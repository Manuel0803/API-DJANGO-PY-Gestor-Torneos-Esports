from django.urls import re_path

from core import views as core_views

urlpatterns = [
    re_path(r'^health/?$', core_views.health, name='health'),
    re_path(r'^api/health/?$', core_views.health, name='api-health'),
    re_path(
        r'^api/estado-simulador/?$',
        core_views.estado_simulador,
        name='estado-simulador',
    ),
]
