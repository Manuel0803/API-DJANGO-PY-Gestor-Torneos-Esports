from functools import wraps
import hmac

from django.conf import settings
from django.http import JsonResponse
import jwt


def error_json(status, title, detail):
    return JsonResponse({'error': title, 'detail': detail}, status=status)


def validar_token_servicio(request):
    token_recibido = request.headers.get('X-Service-Token', '')
    secreto_esperado = getattr(settings, 'INTERNAL_SERVICE_SECRET', '')
    if not token_recibido or not secreto_esperado:
        return False
    return hmac.compare_digest(token_recibido, secreto_esperado)


def requiere_token_servicio(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not validar_token_servicio(request):
            return error_json(
                401,
                'No autorizado',
                'Token de servicio invalido o ausente.',
            )
        return view_func(request, *args, **kwargs)

    return wrapped


def extraer_bearer_token(request):
    auth_header = request.headers.get('Authorization', '').strip()
    if not auth_header:
        return None
    partes = auth_header.split(' ', 1)
    if len(partes) != 2 or partes[0].lower() != 'bearer':
        return None
    token = partes[1].strip()
    return token or None


def decodificar_jwt(token):
    return jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[getattr(settings, 'JWT_ALGORITHM', 'HS256')],
    )


def requiere_jwt(roles_permitidos=None):
    roles_normalizados = (
        {rol.upper() for rol in roles_permitidos}
        if roles_permitidos is not None
        else None
    )

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            token = extraer_bearer_token(request)
            if not token:
                return error_json(
                    401,
                    'No autorizado',
                    'Credenciales de autenticacion ausentes o mal formadas.',
                )
            try:
                payload = decodificar_jwt(token)
            except jwt.ExpiredSignatureError:
                return error_json(
                    401,
                    'No autorizado',
                    'El token de autenticacion ha expirado.',
                )
            except jwt.InvalidTokenError:
                return error_json(
                    401,
                    'No autorizado',
                    'Token de autenticacion invalido.',
                )

            if roles_normalizados is not None:
                rol_usuario = str(
                    payload.get('rol') or payload.get('role') or ''
                ).upper()
                if rol_usuario not in roles_normalizados:
                    return error_json(
                        403,
                        'Prohibido',
                        'Permisos insuficientes para esta operacion.',
                    )

            request.jwt_payload = payload
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator
