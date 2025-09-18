from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from .forms import RegistroForm

# -----------------------------
# VIEW DE REGISTRO
# -----------------------------
def register_view(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()  # salva usuário com senha em hash
            login(request, user)  # loga automaticamente
            messages.success(request, 'Cadastro realizado com sucesso!')
            return redirect('home')
        else:
            messages.error(request, 'Erro no cadastro. Verifique os dados.')
    else:
        form = RegistroForm()  # GET: form vazio

    # Renderiza o template sempre (GET ou POST inválido)
    return render(request, 'usuarios/register.html', {'form': form})


# -----------------------------
# VIEW DE LOGIN
# -----------------------------
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)  # loga o usuário
            messages.success(request, 'Login realizado com sucesso!')
            return redirect('home')
        else:
            messages.error(request, 'Email ou senha inválidos.')
    else:
        form = AuthenticationForm()  # GET: form vazio

    # Renderiza o template sempre (GET ou POST inválido)
    return render(request, 'usuarios/login.html', {'form': form})


# -----------------------------
# VIEW DE LOGOUT
# -----------------------------
def logout_view(request):
    logout(request)  # encerra sessão do usuário
    messages.success(request, 'Logout realizado com sucesso!')
    return redirect('login')
