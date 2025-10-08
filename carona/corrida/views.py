from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import CorridaForm

def is_motorista(user):
    return user.is_authenticated and user.tipo_usuario == 'MOTORISTA'

@login_required
@user_passes_test(is_motorista)
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
def lista_corridas(request):
    # Lógica para listar corridas
    return render(request, 'corrida/lista_corridas.html')

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
def cancelar_corrida(request, corrida_id):
    # Lógica para cancelar uma corrida
    return render(request, 'corrida/cancelar_corrida.html') 