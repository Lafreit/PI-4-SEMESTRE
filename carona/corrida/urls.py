from django.urls import path, include
from . import views     

app_name = 'corrida'

urlpatterns = [
    path('cadastrar/', views.cadastrar_corrida, name='cadastrar_corrida'),
    path('dashboard/', views.dashboard_motorista, name='dashboard_motorista'),
    path('lista/', views.lista_corridas, name='lista_corridas'),    
    path('solicitar/', views.solicitar_corrida, name='solicitar_corrida'),
    path('historico/', views.historico_corridas, name='historico_corridas'),
    path('detalhes/<int:corrida_id>/', views.detalhes_corrida, name='detalhes_corrida'),
    path('cancelar/<int:corrida_id>/', views.cancelar_corrida, name='cancelar_corrida'),
]   