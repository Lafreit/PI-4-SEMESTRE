from django.urls import path
from . import views 

app_name = 'usuarios'

urlpatterns = [
    path ('register/', views.register_view, name='register'),
    path ('login/', views.login_view, name='login'),
    path ('logout/', views.logout_view, name='logout'),
    path('cadastro/', views.cadastra_usuario, name='cadastra_usuario'),
    path('pagina/', views.pagina_inicial, name='pagina_inicial'),
]

