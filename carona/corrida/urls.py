from django.urls import path, include
from . import views     

app_name = 'corrida'

urlpatterns = [
    path("cadastrar/", views.cadastrar_corrida, name="cadastrar_corrida"),
    path("geocode_ajax/", views.geocode_ajax, name="geocode_ajax"),
    path("rota_ajax/", views.rota_ajax, name="rota_ajax"),
    path('dashboard/', views.dashboard_motorista, name='dashboard_motorista'),
    path("buscar/", views.buscar_corridas, name="buscar_corridas"),
    path('lista/', views.lista_corridas, name='lista_corridas'),    
    path('solicitar/', views.solicitar_corrida, name='solicitar_corrida'),
    path('historico/', views.historico_corridas, name='historico_corridas'),
    path('detalhes/<int:corrida_id>/', views.detalhes_corrida, name='detalhes_corrida'),
    path('cancelar/<int:corrida_id>/', views.cancelar_corrida, name='cancelar_corrida'),
    path('editar/<int:corrida_id>/', views.editar_corrida, name='editar_corrida'),
    path('corrida/<int:corrida_id>/solicitar/', views.solicitar_carona, name='solicitar_carona'),
    path('solicitar_corrida/<int:corrida_id>/', views.solicitar_corrida, name='solicitar_corrida'),
    path('api/buscar_corridas/', views.buscar_corridas_api, name='buscar_corridas_api'),
]