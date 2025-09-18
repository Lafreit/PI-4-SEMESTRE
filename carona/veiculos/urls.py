from django.urls import path
from . import views

urlpatterns = [
    # ... outras URLs já existentes na sua aplicação
    path('cadastrar/', views.cadastrar_veiculo, name='cadastrar_veiculo'),
]