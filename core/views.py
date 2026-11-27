from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.auth import error_json, requiere_jwt
from core.simulador import configurar_estado, obtener_estado


@api_view(['GET'])
def health(request):
    return Response(
        {
            'status': 'ok',
            'service': 'esports-identity-evidence-provider',
        },
        status=200,
    )


@requiere_jwt(roles_permitidos=('ORGANIZADOR',))
def _actualizar_estado_simulador(request):
    payload = request.data if isinstance(request.data, dict) else {}
    modo = payload.get('modo')
    latencia_ms = payload.get('latenciaMs')

    if not modo:
        return error_json(
            400,
            'Solicitud invalida',
            'El campo modo es obligatorio.',
        )

    try:
        estado = configurar_estado(modo, latencia_ms)
    except ValueError as exc:
        return error_json(400, 'Solicitud invalida', str(exc))

    return Response(estado, status=200)


@api_view(['GET', 'POST'])
def estado_simulador(request):
    if request.method == 'GET':
        return Response(obtener_estado(), status=200)
    return _actualizar_estado_simulador(request)
