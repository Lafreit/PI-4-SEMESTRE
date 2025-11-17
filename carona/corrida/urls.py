from django.urls import path
from . import views

app_name = 'corrida'

urlpatterns = [
    path("cadastrar/", views.cadastrar_corrida, name="cadastrar_corrida"),
    path("api/geocode/", views.geocode, name="api_geocode"),
    path("api/rota/", views.api_rota, name="rota"),
    path("geocode_ajax/", views.geocode_ajax, name="geocode_ajax"),
    path("rota_ajax/", views.rota_ajax, name="rota_ajax"),
    path('dashboard/', views.dashboard_motorista, name='dashboard_motorista'),
    path("buscar/", views.buscar_corridas, name="buscar_corridas"),
    path('lista/', views.lista_corridas, name='lista_corridas'),
    path('historico/', views.historico_corridas, name='historico_corridas'),
    path('detalhes/<int:corrida_id>/', views.detalhes_corrida, name='detalhes_corrida'),
    path('cancelar/<int:corrida_id>/', views.cancelar_corrida, name='cancelar_corrida'),
    path('editar/<int:corrida_id>/', views.editar_corrida, name='editar_corrida'),
    path('deletar/<int:corrida_id>/', views.deletar_corrida, name='deletar_corrida'),

    path('api/buscar_corridas/', views.buscar_corridas_api, name='buscar_corridas_api'),
    path('api/minhas_solicitacoes/', views.minhas_solicitacoes_api, name='minhas_solicitacoes_api'),

    # Rotas de solicitação (mantidas dentro do app "corrida")
    path('solicitacao/<int:solicitacao_id>/cancelar/', views.cancelar_solicitacao, name='cancelar_solicitacao'),
    path('solicitacao/<int:solicitacao_id>/responder/', views.responder_solicitacao, name='responder_solicitacao'),

    # Endpoints relacionados a uma corrida específica
    path('corrida/<int:corrida_id>/minha_solicitacao/', views.minha_solicitacao_api, name='minha_solicitacao_api'),
    path('<int:corrida_id>/solicitar/', views.solicitar_carona, name='solicitar_carona'),
]
