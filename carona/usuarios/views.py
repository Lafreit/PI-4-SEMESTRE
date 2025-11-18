from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from .forms import RegistroForm, PerfilPassageiroForm, PerfilMotoristaForm 
from .models import Usuario, Profile 

# -----------------------------
# VIEWS BÁSICAS
# -----------------------------

@login_required
def pagina_inicial(request):
    return render(request, 'paginainicial.html')

def cadastra_usuario(request):
    return render(request, 'cadastraUsuario.html')

def register_view(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Cadastro realizado com sucesso!')
            return redirect('usuarios:pagina_inicial')
        else:
            messages.error(request, 'Erro no cadastro. Verifique os dados.')
    else:
        form = RegistroForm()
    return render(request, 'usuarios/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('usuarios:pagina_inicial')
        else:
            messages.error(request, 'Email ou senha inválidos.')
    else:
        form = AuthenticationForm()
    return render(request, 'usuarios/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')


# ----------------------------------------------------------------------
# VIEW DE VISUALIZAÇÃO DE PERFIL (meu_perfil)
# ----------------------------------------------------------------------
@login_required
def meu_perfil(request):
    """
    Renderiza o template de visualização de perfil correto baseado em request.user.tipo_usuario.
    """
    usuario_logado = request.user
    
    # Acessa o tipo de usuário diretamente do campo no modelo Usuario
    user_tipo = usuario_logado.tipo_usuario 
    
    if user_tipo == Usuario.MOTORISTA: # Usa a constante definida no models.py
        template_name = 'usuarios/perfil_motorista.html'
    else:
        template_name = 'usuarios/perfil_passageiro.html'
        
    # O objeto 'user' é passado para o template.
    return render(request, template_name, {'user': usuario_logado})


# ----------------------------------------------------------------------
# VIEW DE EDIÇÃO DE PERFIL (editar_perfil)
# Lida com a edição dos dados base (Usuario) e Motorista (Profile).
# ----------------------------------------------------------------------

@login_required
def editar_perfil(request):
    usuario_logado = request.user
    
    # 1. Inicializa Formulários (Mantido como estava)
    usuario_form = PerfilPassageiroForm(instance=usuario_logado)
    profile_form = None
    profile_instance = None

    if usuario_logado.tipo_usuario == Usuario.MOTORISTA:
        profile_instance, created = Profile.objects.get_or_create(user=usuario_logado)
        profile_form = PerfilMotoristaForm(instance=profile_instance)
    
    # 2. Lógica POST (Salvar dados)
    if request.method == 'POST':
        usuario_form = PerfilPassageiroForm(request.POST, instance=usuario_logado)
        
        # Instancia o profile_form com POST se for motorista
        if usuario_logado.tipo_usuario == Usuario.MOTORISTA and profile_instance:
            profile_form = PerfilMotoristaForm(request.POST, instance=profile_instance)

        salvo_com_sucesso = False
        
        if usuario_form.is_valid():
            usuario_form.save()
            salvo_com_sucesso = True # Sucesso nos dados base
            
            # Lógica para Motorista
            if usuario_logado.tipo_usuario == Usuario.MOTORISTA and profile_form:
                
                if profile_form.is_valid():
                    profile_form.save()
                    # MENSAGEM DE SUCESSO DO MOTORISTA
                    messages.success(request, 'Perfil e dados do veículo atualizados com sucesso! 🚗')
                    # Não colocamos return/redirect aqui.
                else:
                    messages.error(request, 'Erro ao salvar dados do veículo. Verifique o formulário.')
                    salvo_com_sucesso = False # Falha nos dados do veículo
            
            # Lógica de Mensagem e Redirecionamento Final
            if salvo_com_sucesso:
                # Mensagem de sucesso APENAS para Passageiros
                # A mensagem de Motorista já foi definida acima.
                if usuario_logado.tipo_usuario == Usuario.PASSAGEIRO:
                    messages.success(request, 'Perfil atualizado com sucesso! 🎉')
                
                # REDIRECIONAMENTO FINAL APÓS SUCESSO COMPLETO
                return redirect('usuarios:meu_perfil') 
        
        # Se o usuario_form for inválido:
        else:
            messages.error(request, 'Houve um erro ao salvar os dados principais do perfil. Verifique os campos.')
            # Não redireciona, cai para renderizar o formulário com erros.

    # 3. Contexto (Mantido como estava)
    context = {
        'usuario_form': usuario_form, 
        'profile_form': profile_form,
        'usuario': usuario_logado
    }
    
    # Renderiza o template de edição
    return render(request, 'editar_perfil.html', context)
