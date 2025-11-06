from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import CorridaForm
from .models import Corrida
from .utils import geocode_endereco, gerar_rota, nearest_point_on_route
from django.http import JsonResponse
from django.db.models import Q
import json


TOLERANCIA_METROS = 60000  # 50 km

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
    endereco_passageiro = request.GET.get("endereco", "").strip()
    # ler parâmetro de tolerância enviado pelo usuário (query param "tolerancia")
    tolerancia_param = request.GET.get("tolerancia", None)
    try:
        # tentativa de interpretar como inteiro (metros)
        tolerancia_metros = int(float(tolerancia_param)) if tolerancia_param is not None else TOLERANCIA_METROS
    except (ValueError, TypeError):
        tolerancia_metros = TOLERANCIA_METROS

    # sanitizar / limitar tolerância para evitar valores absurdos
    if tolerancia_metros < 100:
        tolerancia_metros = 100
    if tolerancia_metros > 200000:  # 200 km como teto razoável
        tolerancia_metros = 200000

    corridas_encontradas = []
    coords = {'lat': 0.0, 'lon': 0.0}

    if endereco_passageiro:
        lat, lon = geocode_endereco(endereco_passageiro)
        if lat is not None and lon is not None:
            coords['lat'] = float(lat)
            coords['lon'] = float(lon)

            # temporariamente busca todas ativas e depois filtra pela distância real
            corridas_candidato = Corrida.objects.filter(status='ativa')

            for corrida in corridas_candidato:
                try:
                    distancia = nearest_point_on_route((lat, lon), corrida.rota)
                except Exception:
                    distancia = None

                if distancia is not None and distancia <= tolerancia_metros:
                    corrida.distancia_ao_passageiro = round(distancia, 1)
                    corridas_encontradas.append(corrida)

    # Serializa corridas para JSON-friendly (mesmo formato que você já tinha)
    corridas_serializadas = []
    for corrida in corridas_encontradas:
        rota_serializada = []
        try:
            if isinstance(corrida.rota, (list, tuple)) and corrida.rota:
                for pair in corrida.rota:
                    if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                        lat_p = float(pair[0])
                        lon_p = float(pair[1])
                        rota_serializada.append([lat_p, lon_p])
        except Exception:
            rota_serializada = []

        origem_lat = corrida.origem_lat if corrida.origem_lat is not None else (rota_serializada[0][0] if rota_serializada else 0.0)
        origem_lon = corrida.origem_lon if corrida.origem_lon is not None else (rota_serializada[0][1] if rota_serializada else 0.0)
        destino_lat = corrida.destino_lat if corrida.destino_lat is not None else (rota_serializada[-1][0] if rota_serializada else 0.0)
        destino_lon = corrida.destino_lon if corrida.destino_lon is not None else (rota_serializada[-1][1] if rota_serializada else 0.0)

        horario_saida_str = corrida.horario_saida.strftime("%H:%M") if getattr(corrida, "horario_saida", None) else None
        horario_chegada_str = corrida.horario_chegada.strftime("%H:%M") if getattr(corrida, "horario_chegada", None) else None

        corrida_dict = {
            "id": corrida.id,
            "origem": str(corrida.origem),
            "destino": str(corrida.destino),
            "origem_lat": float(origem_lat),
            "origem_lon": float(origem_lon),
            "destino_lat": float(destino_lat),
            "destino_lon": float(destino_lon),
            "rota": rota_serializada,
            "horario_saida": horario_saida_str,
            "horario_chegada": horario_chegada_str,
            "valor": float(corrida.valor) if corrida.valor is not None else 0.0,
            "vagas_disponiveis": int(corrida.vagas_disponiveis or 0),
            "distancia_m": float(getattr(corrida, "distancia_ao_passageiro", 0.0)),
        }
        corridas_serializadas.append(corrida_dict)

    corridas_json = json.dumps(corridas_serializadas, ensure_ascii=False)
    coords_json = json.dumps(coords, ensure_ascii=False)

    # Passa também a tolerância atual para exibir no template/controle
    return render(request, "corrida/resultados_busca.html", {
        "corridas": corridas_serializadas,
        "coords": coords,
        "corridas_json": corridas_json,
        "coords_json": coords_json,
        "endereco": endereco_passageiro,
        "tolerancia_metros": tolerancia_metros,  # valor usado (m)
    })


def rota_ajax(request):
    try:
        lat1 = float(request.GET.get("lat_origem"))
        lon1 = float(request.GET.get("lon_origem"))
        lat2 = float(request.GET.get("lat_destino"))
        lon2 = float(request.GET.get("lon_destino"))

        rota, _, _ = gerar_rota(lat1, lon1, lat2, lon2)
        # garante floats e formato [lat, lon]
        rota_serializada = [[float(lat), float(lon)] for lat, lon in rota]

        return JsonResponse({"rota": rota_serializada})
    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=400)