from django.shortcuts import render

def pagina_inicial(request):
    return render(request, 'paginainicial.html')

def cadastra_usuario(request):
    return render(request, 'cadastraUsuario.html')
