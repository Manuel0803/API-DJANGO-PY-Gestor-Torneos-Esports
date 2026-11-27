from threading import Lock
import time

from django.http import JsonResponse

MODOS_VALIDOS = {'normal', 'timeout', 'error_500'}
LATENCIA_TIMEOUT_POR_DEFECTO_MS = 3500

_lock = Lock()
_estado = {
    'modo': 'normal',
    'latencia_ms': 0,
}


def obtener_estado():
    with _lock:
        return {
            'modo': _estado['modo'],
            'latenciaMs': _estado['latencia_ms'],
        }


def configurar_estado(modo, latencia_ms=None):
    if modo not in MODOS_VALIDOS:
        raise ValueError('Modo de simulador invalido.')

    if latencia_ms is None:
        latencia_calculada = LATENCIA_TIMEOUT_POR_DEFECTO_MS if modo == 'timeout' else 0
    else:
        if isinstance(latencia_ms, bool) or not isinstance(latencia_ms, int) or latencia_ms < 0:
            raise ValueError('La latencia debe ser un entero mayor o igual a cero.')
        latencia_calculada = latencia_ms

    with _lock:
        _estado['modo'] = modo
        _estado['latencia_ms'] = latencia_calculada
        return {
            'modo': _estado['modo'],
            'latenciaMs': _estado['latencia_ms'],
        }


def reiniciar_estado():
    return configurar_estado('normal', 0)


def _respuesta_error_simulado(status_code):
    return JsonResponse(
        {
            'error': 'Falla simulada',
            'detail': 'El servicio externo no se encuentra disponible temporalmente.',
        },
        status=status_code,
    )


def evaluar_simulacion(request):
    simular_timeout_header = request.headers.get('X-Simulate-Timeout', '').strip().lower()
    if simular_timeout_header in ('1', 'true', 'yes'):
        time.sleep(LATENCIA_TIMEOUT_POR_DEFECTO_MS / 1000.0)

    simular_error_header = request.headers.get('X-Simulate-Error', '').strip()
    if simular_error_header:
        try:
            codigo = int(simular_error_header)
        except ValueError:
            codigo = 500
        if codigo not in (500, 502, 503, 504):
            codigo = 500
        return _respuesta_error_simulado(codigo)

    with _lock:
        modo_actual = _estado['modo']
        latencia_actual = _estado['latencia_ms']

    if modo_actual == 'timeout':
        espera_ms = latencia_actual if latencia_actual > 0 else LATENCIA_TIMEOUT_POR_DEFECTO_MS
        time.sleep(espera_ms / 1000.0)
        return None

    if modo_actual == 'error_500':
        return _respuesta_error_simulado(500)

    return None
