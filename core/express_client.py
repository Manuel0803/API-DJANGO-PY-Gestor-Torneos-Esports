import logging

from django.conf import settings
import requests

logger = logging.getLogger(__name__)


def notificar_evento_express(tipo, datos):
    if not getattr(settings, 'EXPRESS_SYNC_ENABLED', True):
        return {'enviado': False, 'motivo': 'sincronizacion_deshabilitada'}

    base_url = getattr(settings, 'EXPRESS_SERVICE_URL', '').rstrip('/')
    if not base_url:
        return {'enviado': False, 'motivo': 'url_express_no_configurada'}

    url = f'{base_url}/api/integracion/eventos'
    headers = {
        'Content-Type': 'application/json',
        'X-Service-Token': getattr(settings, 'INTERNAL_SERVICE_SECRET', ''),
    }
    timeout = float(getattr(settings, 'EXPRESS_TIMEOUT_SECONDS', 3))

    try:
        respuesta = requests.post(
            url,
            json={'tipo': tipo, 'datos': datos},
            headers=headers,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        logger.warning('No se pudo notificar evento %s a Express: %s', tipo, exc)
        return {'enviado': False, 'motivo': 'express_no_disponible'}

    if 200 <= respuesta.status_code < 300:
        return {'enviado': True, 'status': respuesta.status_code}

    logger.warning(
        'Express rechazo el evento %s con estado %s',
        tipo,
        respuesta.status_code,
    )
    return {'enviado': False, 'status': respuesta.status_code}
