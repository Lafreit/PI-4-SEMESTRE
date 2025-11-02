from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import CorridaForm
from .models import Corrida
from .utils import geocode_endereco, gerar_rota, nearest_point_on_route
from django.http import JsonResponse
from django.db.models import Q


TOLERANCIA_METROS = 600  # distância máxima para considerar "próximo"

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
            corrida.status = 'ativa'  # valor padrão

            # Geocodificar origem e destino
            origem_coords = geocode_endereco(corrida.origem)
            destino_coords = geocode_endereco(corrida.destino)

            if origem_coords and destino_coords:
                corrida.origem_lat, corrida.origem_lon = origem_coords
                corrida.destino_lat, corrida.destino_lon = destino_coords

                # Gerar rota
                rota, distancia, n_pontos = gerar_rota(
                    corrida.origem_lat, corrida.origem_lon,
                    corrida.destino_lat, corrida.destino_lon
                )
                corrida.rota = rota
                corrida.distancia_m = distancia
                corrida.pontos_count = n_pontos

                # Bounding box
                corrida.set_bbox_from_rota()
            else:
                messages.warning(request, "Não foi possível geocodificar origem ou destino.")

            corrida.save()
            messages.success(request, 'Corrida cadastrada com sucesso!')
            return redirect('usuarios:pagina_inicial')
        else:
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


def geocode_ajax(request):
    """
    Endpoint AJAX para geocodificar um endereço e retornar lat/lon.
    """
    endereco = request.GET.get("endereco")
    if not endereco:
        return JsonResponse({"erro": "Endereço não fornecido"}, status=400)

    lat, lon = geocode_endereco(endereco)
    if lat is not None and lon is not None:
        return JsonResponse({"lat": lat, "lon": lon})
    else:
        return JsonResponse({"erro": "Não foi possível geocodificar"}, status=404)
    

def buscar_corridas(request):
    endereco_passageiro = request.GET.get("endereco")
    corridas_encontradas = []

    if endereco_passageiro:
        lat, lon = geocode_endereco(endereco_passageiro)
        if lat is not None and lon is not None:
            # Filtro inicial por bounding box
            corridas_bbox = Corrida.objects.filter(
                bbox_min_lat__lte=lat,
                bbox_max_lat__gte=lat,
                bbox_min_lon__lte=lon,
                bbox_max_lon__gte=lon,
                status='ativa'
            )

            # Verificação real de proximidade
            for corrida in corridas_bbox:
                distancia = nearest_point_on_route((lat, lon), corrida.rota)
                if distancia <= TOLERANCIA_METROS:
                    corrida.distancia_ao_passageiro = round(distancia, 1)
                    corridas_encontradas.append(corrida)

    return render(request, "corrida/resultados_busca.html", {
        "corridas": corridas_encontradas,
        "endereco": endereco_passageiro
    })


def rota_ajax(request):
    try:
        lat1 = float(request.GET.get("lat_origem"))
        lon1 = float(request.GET.get("lon_origem"))
        lat2 = float(request.GET.get("lat_destino"))
        lon2 = float(request.GET.get("lon_destino"))

        rota, _, _ = gerar_rota(lat1, lon1, lat2, lon2)
        rota_serializada = [[lat, lon] for lat, lon in rota]  # <- ESSA LINHA É ESSENCIAL

        return JsonResponse({"rota": rota_serializada})
    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=400)