from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from .forms import RegistroForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import PerfilPassageiroForm

@login_required
def pagina_inicial(request):
    return render(request, 'paginainicial.html')

def cadastra_usuario(request):
    return render(request, 'cadastraUsuario.html')

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
            return redirect('usuarios:pagina_inicial')
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
            #messages.success(request, 'Login realizado com sucesso!')
            return redirect('usuarios:pagina_inicial')
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
    #messages.success(request, 'Logout realizado com sucesso!')
    return redirect('home')


# VIEW DE PERFIL PASSAGEIRO OU MOTORISTA
# -----------------------------
@login_required
def meu_perfil(request):
    
    user_tipo = 'passageiro'  # tipo de usuario

    try:
        # Acessa o tipo através da relação 'profile' (request.user.profile.tipo)
        user_tipo = request.user.profile.tipo
    except AttributeError:
        # Se houver um erro (o objeto 'profile' ainda não existe), mantém o padrão 'passageiro'
        pass

    if user_tipo == 'motorista':
        template_name = 'usuarios/perfil_motorista.html' 
    else:
        # Se for passageiro ou se houver falha ao ler o perfil
        template_name = 'usuarios/perfil_passageiro.html'
        
    # O objeto 'user' é passado para o template, incluindo o 'profile' associado
    return render(request, template_name, {'user': request.user})

@login_required
def editar_perfil(request):
    usuario_logado = request.user
    
    if request.method == 'POST':
        form = PerfilPassageiroForm(request.POST, instance=usuario_logado)
        
        if form.is_valid():
            # O form.save() customizado em PerfilPassageiroForm lida com a senha
            form.save()
            messages.success(request, 'Seu perfil e/ou senha foram atualizados com sucesso!')
            return redirect('usuarios:meu_perfil') 
    else:
        form = PerfilPassageiroForm(instance=usuario_logado)

    context = {
        'form': form,
        'usuario': usuario_logado
    }
    
    return render(request, 'editar_perfil.html', context)
