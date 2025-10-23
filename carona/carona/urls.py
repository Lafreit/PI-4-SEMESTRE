
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render

def home_view(request):
    return render (request, 'home.html')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_view, name='home'),
    path('usuarios/', include('usuarios.urls', namespace='usuarios')),
    path('corrida/', include ('corrida.urls')),
    # path('veiculos/', include('veiculos.urls')),
]
