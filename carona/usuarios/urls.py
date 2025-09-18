from django.urls import path
from . import views  # Isso importa do APP usuario, não do projeto

app_name = 'usuarios'

urlpatterns = [
    path('cadastro/', views.cadastra_usuario, name='cadastra_usuario'),
    path('pagina/', views.pagina_inicial, name='pagina_inicial'),
]