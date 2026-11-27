from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.http import JsonResponse
from django.test import RequestFactory, SimpleTestCase, override_settings
import jwt
import requests

from core.auth import requiere_token_servicio
from core.express_client import notificar_evento_express
from core.simulador import configurar_estado, evaluar_simulacion, reiniciar_estado


def generar_jwt(
    rol='ORGANIZADOR',
    expirado=False,
    issuer=None,
    audience=None,
):
    delta = timedelta(minutes=-5) if expirado else timedelta(minutes=30)
    payload = {
        'sub': 'usuario-test-1',
        'rol': rol,
        'iss': issuer or settings.JWT_ISSUER,
        'aud': audience or settings.JWT_AUDIENCE,
        'exp': datetime.now(timezone.utc) + delta,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


class CoreEndpointsTest(SimpleTestCase):
    def setUp(self):
        reiniciar_estado()
        self.factory = RequestFactory()

    def tearDown(self):
        reiniciar_estado()

    def test_health_sin_y_con_prefijo_api(self):
        for ruta in ('/health', '/health/', '/api/health', '/api/health/'):
            respuesta = self.client.get(ruta)
            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(
                respuesta.json(),
                {
                    'status': 'ok',
                    'service': 'esports-identity-evidence-provider',
                },
            )

    def test_get_estado_simulador_devuelve_estado_inicial(self):
        respuesta = self.client.get('/api/estado-simulador')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), {'modo': 'normal', 'latenciaMs': 0})

    def test_post_estado_simulador_sin_jwt_retorna_401(self):
        respuesta = self.client.post(
            '/api/estado-simulador',
            data={'modo': 'error_500'},
            content_type='application/json',
        )
        self.assertEqual(respuesta.status_code, 401)

    def test_post_estado_simulador_con_jwt_expirado_retorna_401(self):
        token = generar_jwt(rol='ORGANIZADOR', expirado=True)
        respuesta = self.client.post(
            '/api/estado-simulador',
            data={'modo': 'error_500'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(respuesta.status_code, 401)

    def test_post_estado_simulador_con_audience_invalida_retorna_401(self):
        token = generar_jwt(rol='ORGANIZADOR', audience='otra-audiencia')
        respuesta = self.client.post(
            '/api/estado-simulador',
            data={'modo': 'error_500'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(respuesta.status_code, 401)

    def test_post_estado_simulador_con_rol_no_organizador_retorna_403(self):
        token = generar_jwt(rol='CAPITAN')
        respuesta = self.client.post(
            '/api/estado-simulador',
            data={'modo': 'error_500'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(respuesta.status_code, 403)

    def test_post_estado_simulador_con_jwt_organizador_actualiza_estado(self):
        token = generar_jwt(rol='ORGANIZADOR')
        respuesta = self.client.post(
            '/api/estado-simulador',
            data={'modo': 'timeout', 'latenciaMs': 4000},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), {'modo': 'timeout', 'latenciaMs': 4000})

        consulta = self.client.get('/api/estado-simulador')
        self.assertEqual(consulta.json(), {'modo': 'timeout', 'latenciaMs': 4000})

    def test_post_estado_simulador_modo_invalido_retorna_400(self):
        token = generar_jwt(rol='ORGANIZADOR')
        respuesta = self.client.post(
            '/api/estado-simulador',
            data={'modo': 'desconocido'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(respuesta.status_code, 400)

    def test_decorador_token_servicio_valida_header(self):
        @requiere_token_servicio
        def vista_interna(request):
            return JsonResponse({'ok': True}, status=200)

        req_sin_token = self.factory.post('/identidad/verificar')
        self.assertEqual(vista_interna(req_sin_token).status_code, 401)

        req_invalido = self.factory.post(
            '/identidad/verificar',
            HTTP_X_SERVICE_TOKEN='secreto-incorrecto',
        )
        self.assertEqual(vista_interna(req_invalido).status_code, 401)

        req_valido = self.factory.post(
            '/identidad/verificar',
            HTTP_X_SERVICE_TOKEN=settings.INTERNAL_SERVICE_SECRET,
        )
        self.assertEqual(vista_interna(req_valido).status_code, 200)

    def test_simulador_header_y_estado_global_error(self):
        req_error = self.factory.get('/health', HTTP_X_SIMULATE_ERROR='503')
        resp_header = evaluar_simulacion(req_error)
        self.assertIsNotNone(resp_header)
        self.assertEqual(resp_header.status_code, 503)

        configurar_estado('error_500')
        req_normal = self.factory.get('/health')
        resp_global = evaluar_simulacion(req_normal)
        self.assertIsNotNone(resp_global)
        self.assertEqual(resp_global.status_code, 500)

    @patch('core.express_client.requests.post')
    @override_settings(EXPRESS_SYNC_ENABLED=True, EXPRESS_SERVICE_URL='http://localhost:3000')
    def test_notificar_evento_express_envia_token_servicio(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        resultado = notificar_evento_express('SANCION_ANTICHEAT', {'jugadorId': 'j-1'})

        self.assertEqual(resultado, {'enviado': True, 'status': 200})
        mock_post.assert_called_once_with(
            'http://localhost:3000/api/integracion/eventos',
            json={'tipo': 'SANCION_ANTICHEAT', 'datos': {'jugadorId': 'j-1'}},
            headers={
                'Content-Type': 'application/json',
                'X-Service-Token': settings.INTERNAL_SERVICE_SECRET,
            },
            timeout=float(settings.EXPRESS_TIMEOUT_SECONDS),
        )

    @patch('core.express_client.requests.post', side_effect=requests.Timeout('timeout'))
    @override_settings(EXPRESS_SYNC_ENABLED=True, EXPRESS_SERVICE_URL='http://localhost:3000')
    def test_notificar_evento_express_maneja_caida_sin_romper(self, _mock_post):
        resultado = notificar_evento_express('EVIDENCIA_REVISADA', {'evidenciaId': 'e-1'})
        self.assertEqual(resultado, {'enviado': False, 'motivo': 'express_no_disponible'})

    @override_settings(EXPRESS_SYNC_ENABLED=False)
    def test_notificar_evento_express_deshabilitado(self):
        resultado = notificar_evento_express('SANCION_ANTICHEAT', {'jugadorId': 'j-1'})
        self.assertEqual(
            resultado,
            {'enviado': False, 'motivo': 'sincronizacion_deshabilitada'},
        )
