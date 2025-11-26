# notificacao/urls.py
from django.urls import path
from . import views

app_name = "notificacao"

urlpatterns = [
    path("", views.lista_notificacoes, name="lista"),
    path("api/marcar_lida/", views.api_marcar_lida, name="api_marcar_lida"),
    path("api/contagem/", views.api_contagem_nao_lidas, name="api_contagem"),
    
]
