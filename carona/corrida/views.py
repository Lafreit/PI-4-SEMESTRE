from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import CorridaForm
from .models import Corrida

def is_motorista(user):
    return bool(user and user.is_authenticated and getattr(user, "tipo_usuario", "") == "motorista")


@login_required(login_url='usuarios:login')
@user_passes_test(is_motorista, login_url='usuarios:login')
def cadastrar_corrida(request):
    if request.method == 'POST':
        form = CorridaForm(request.POST)
        if form.is_valid():
            corrida = form.save(commit=False)
            corrida.motorista = request.user
            corrida.save()
            messages.success(request, 'Corrida cadastrada com sucesso!')
            return redirect('usuarios:pagina_inicial')
        else:
            # Exibe todos os erros detalhados via mensagens
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Erro em {field}: {error}")
    else:
        form = CorridaForm()

    return render(request, 'corrida/cadastrar_corrida.html', {'form': form})

@login_required
@user_passes_test(is_motorista)
def dashboard_motorista(request):
    # Lógica para o dashboard do motorista
    return render(request, 'corrida/dashboard_motorista.html')  

@login_required
@user_passes_test(is_motorista)
def lista_corridas(request):
    # Lógica para listar corridas
    corridas = Corrida.objects.filter(motorista=request.user).order_by('-data','horario_saida')

    context = {
        'corridas': corridas
    }

    return render(request, 'corrida/lista_corridas.html', context)

@login_required
@user_passes_test(is_motorista)
def editar_corrida(request, corrida_id):
    corrida = get_object_or_404(Corrida, id=corrida_id, motorista=request.user)

    if request.method == 'POST':
        form = CorridaForm(request.POST, instance=corrida)
        if form.is_valid():
            form.save()
            messages.success(request, 'Corrida atualizada com sucesso!')
            return redirect('corrida:lista_corridas')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Erro em {field}: {error}")

    else:
        form = CorridaForm(instance=corrida)


    return render(request, 'corrida/editar_corrida.html', {'form': form, 'corrida': corrida})       


@login_required
def solicitar_corrida(request):
    # Lógica para solicitar uma corrida
    return render(request, 'corrida/solicitar_corrida.html')

@login_required
def historico_corridas(request):
    # Lógica para mostrar o histórico de corridas
    return render(request, 'corrida/historico_corridas.html')

@login_required
def detalhes_corrida(request, corrida_id):
    # Lógica para mostrar detalhes de uma corrida específica
    return render(request, 'corrida/detalhes_corrida.html')

@login_required
@user_passes_test(is_motorista)
def cancelar_corrida(request, corrida_id):
    # Lógica para cancelar uma corrida
        corrida = get_object_or_404(Corrida, id=corrida_id, motorista=request.user)

        if request.method == 'POST':
            if corrida.status == 'ativa':
                corrida.status = 'cancelada'
                messages.success(request, 'Corrida cancelada com sucesso.')
            else:
                corrida.status = 'ativa'
                messages.success(request, 'Corrida reativada com sucesso.')
            corrida.save()
            return redirect('corrida:lista_corridas')
        return render(request, 'corrida/cancelar_corrida.html', {'corrida': corrida})