from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import CorridaForm
from .models import Corrida, SolicitacaoCarona
from .utils import geocode_endereco, gerar_rota, nearest_point_on_route
from django.views.decorators.http import require_POST, require_GET
from django.http import JsonResponse, HttpResponseBadRequest
from django.db.models import Q
import json
import requests
from django.views.decorators.cache import cache_page
from decimal import Decimal, InvalidOperation
from django.conf import settings


PHOTON_BASE = "https://photon.komoot.io/api/"
TOLERANCIA_METROS = 60000  # 50 km

def is_motorista(user):
    return bool(user and user.is_authenticated and (user.is_superuser or getattr(user, "tipo_usuario", "") == "motorista"))

def is_passageiro(user):
    return bool(user and user.is_authenticated and (user.is_superuser or getattr(user, "tipo_usuario", "") == "passageiro"))


def gerar_rota_e_apurar(origem_lat, origem_lon, destino_lat, destino_lon, profile='driving-car', timeout=8):
    """
    Retorna (rota, distancia_m, pontos_count)
    - rota: lista de [lat, lon]
    - distancia_m: float (metros)
    - pontos_count: int (número de pontos na rota)
    Tenta OpenRouteService se ORS_API_KEY existe em settings, senão usa OSRM público.
    Lança requests.RequestException em erro de comunicação ou ValueError em resposta inválida.
    """
    # valida entradas
    if None in (origem_lat, origem_lon, destino_lat, destino_lon):
        raise ValueError("Coordenadas ausentes para gerar rota")

    # Tenta OpenRouteService (se chave disponível)
    ors_key = getattr(settings, 'ORS_API_KEY', None)
    if ors_key:
        url = f'https://api.openrouteservice.org/v2/directions/{profile}/geojson'
        body = {
            "coordinates": [[float(origem_lon), float(origem_lat)], [float(destino_lon), float(destino_lat)]],
            "instructions": False
        }
        headers = {
            'Authorization': ors_key,
            'Content-Type': 'application/json'
        }
        r = requests.post(url, json=body, headers=headers, timeout=timeout)
        r.raise_for_status()
        js = r.json()
        features = js.get('features') or []
        if not features:
            raise ValueError("ORS: resposta sem features")
        geom = features[0].get('geometry') or {}
        coords = geom.get('coordinates')  # lista de [lon, lat]
        if not coords:
            raise ValueError("ORS: geometry vazia")
        # converter para [[lat, lon], ...]
        rota = [[c[1], c[0]] for c in coords]
        props = features[0].get('properties') or {}
        summary = props.get('summary') or {}
        distancia_m = summary.get('distance') or (props.get('segments', [{}])[0].get('distance') if props else None)
        distancia_m = float(distancia_m) if distancia_m is not None else None
        pontos_count = len(rota)
        return rota, distancia_m, pontos_count

    # Fallback: OSRM público
    osrm_url = (
        f'https://router.project-osrm.org/route/v1/driving/'
        f'{float(origem_lon)},{float(origem_lat)};{float(destino_lon)},{float(destino_lat)}'
        f'?overview=full&geometries=geojson&annotations=distance'
    )
    r = requests.get(osrm_url, timeout=timeout)
    r.raise_for_status()
    js = r.json()
    routes = js.get('routes') or []
    if not routes:
        raise ValueError("OSRM: resposta sem routes")
    route0 = routes[0]
    geom = route0.get('geometry') or {}
    coords = geom.get('coordinates')  # lista de [lon, lat]
    if not coords:
        raise ValueError("OSRM: geometry vazia")
    rota = [[c[1], c[0]] for c in coords]
    distancia_m = float(route0.get('distance')) if route0.get('distance') is not None else None
    pontos_count = len(rota)
    return rota, distancia_m, pontos_count

@login_required(login_url='usuarios:login')
@user_passes_test(is_motorista, login_url='usuarios:login')
def cadastrar_corrida(request):
    """
    View para cadastrar uma corrida.
    - exige que o usuário selecione sugestões com coordenadas (origem_lat/origem_lon e destino_lat/destino_lon)
    - gera rota via ORS (se chave em settings) ou OSRM público
    - preenche corrida.rota, corrida.distancia_m, corrida.pontos_count e bbox via set_bbox_from_rota()
    - se falhar a geração da rota, adiciona erro ao form e não salva (garante que DB terá os campos preenchidos)
    """
    if request.method == 'POST':
        form = CorridaForm(request.POST)
        if form.is_valid():
            corrida = form.save(commit=False)
            corrida.motorista = request.user

            # conversor seguro Decimal/str -> float
            def to_float(value):
                if value in (None, '', False):
                    return None
                try:
                    return float(value)
                except (ValueError, TypeError, InvalidOperation):
                    return None

            corrida.origem_lat = to_float(form.cleaned_data.get('origem_lat'))
            corrida.origem_lon = to_float(form.cleaned_data.get('origem_lon'))
            corrida.destino_lat = to_float(form.cleaned_data.get('destino_lat'))
            corrida.destino_lon = to_float(form.cleaned_data.get('destino_lon'))

            # exige coordenadas
            if not all([corrida.origem_lat, corrida.origem_lon, corrida.destino_lat, corrida.destino_lon]):
                form.add_error(None, "Origem e destino precisam ter coordenadas (selecione uma sugestão).")
            else:
                try:
                    rota, distancia_m, pontos_count = gerar_rota_e_apurar(
                        corrida.origem_lat, corrida.origem_lon,
                        corrida.destino_lat, corrida.destino_lon
                    )
                    # preencher campos do modelo
                    corrida.rota = rota
                    corrida.distancia_m = distancia_m
                    corrida.pontos_count = pontos_count

                    # atualiza bbox com base na rota
                    try:
                        corrida.set_bbox_from_rota()
                    except Exception:
                        # não deixa quebrar a requisição por erro no cálculo do bbox
                        pass

                    # salvar definitivo no DB
                    corrida.save()
                    messages.success(request, "Corrida cadastrada com sucesso.")
                    return redirect('corrida:lista')  # ajuste para sua url de listagem

                except requests.RequestException:
                    form.add_error(None, "Não foi possível gerar a rota agora (erro de comunicação). Tente novamente mais tarde.")
                except ValueError as e:
                    form.add_error(None, f"Erro ao gerar rota: {str(e)}")
                except Exception:
                    form.add_error(None, "Erro inesperado ao gerar rota. Contate o administrador.")
        else:
            messages.error(request, "Por favor corrija os erros no formulário.")
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


@login_required
@require_POST
def solicitar_carona(request, corrida_id):
    """
    Endpoint AJAX (POST) para o passageiro solicitar uma vaga na corrida.
    Retorna JSON: { ok: True, id: <id>, status: <status> } ou { erro: <mensagem> }.
    """
    user = request.user
    # busca corrida ativa
    corrida = get_object_or_404(Corrida, id=corrida_id, status='ativa')

    # não permitir que o motorista solicite a própria corrida
    if corrida.motorista_id == user.id:
        return JsonResponse({'erro': 'Você não pode solicitar sua própria carona.'}, status=400)

    # evitar solicitações duplicadas (pendente/aceita/recusada exceto cancelada)
    existente = SolicitacaoCarona.objects.filter(
        corrida=corrida,
        passageiro=user
    ).exclude(status='CANCELADA').exists()

    if existente:
        return JsonResponse({'erro': 'Você já solicitou esta carona.'}, status=400)

    # criar solicitação
    solicit = SolicitacaoCarona.objects.create(corrida=corrida, passageiro=user)
    return JsonResponse({
        'ok': True,
        'id': solicit.id,
        'status': solicit.status,
        'data_solicitacao': solicit.data_solicitacao.isoformat()
    })


@login_required
def solicitar_corrida(request, corrida_id):
    """
    Cria uma solicitação de carona para a corrida informada.
    """
    if request.method == "POST":
        corrida = get_object_or_404(Corrida, id=corrida_id)
        passageiro = request.user

        # Verifica se já existe solicitação pendente
        if SolicitacaoCarona.objects.filter(corrida=corrida, passageiro=passageiro).exists():
            return JsonResponse({"status": "erro", "message": "Você já solicitou esta corrida."}, status=400)

        SolicitacaoCarona.objects.create(
            corrida=corrida,
            passageiro=passageiro,
            status="Pendente"
        )

        return JsonResponse({"status": "ok", "message": "Solicitação enviada com sucesso!"})

    return JsonResponse({"status": "erro", "message": "Método não permitido."}, status=405)


@require_GET
def buscar_corridas_api(request):
    """
    API GET que recebe:
      ?origem=<texto>&destino=<texto>&tol=<metros opcional>
    e retorna JSON:
      { "ok": True, "corridas": [ { corrida_dict }, ... ], "coords": {lat, lon} }
    """
    origem_text = request.GET.get('origem', '').strip()
    destino_text = request.GET.get('destino', '').strip()
    tol_param = request.GET.get('tol', None)

    # validação básica
    if not origem_text or not destino_text:
        return JsonResponse({'ok': False, 'erro': 'Parâmetros "origem" e "destino" são obrigatórios.'}, status=400)

    # tolerância: se foi informada no request, usa; caso contrário usa padrão
    try:
        tolerancia = int(tol_param) if tol_param is not None else TOLERANCIA_METROS
    except (ValueError, TypeError):
        tolerancia = TOLERANCIA_METROS

    # geocodifica origem (passageiro) — usamos só para centralizar no mapa e para filtro inicial
    lat, lon = geocode_endereco(origem_text)
    if lat is None or lon is None:
        return JsonResponse({'ok': False, 'erro': 'Não foi possível geocodificar o endereço de origem.'}, status=404)

    coords = {'lat': float(lat), 'lon': float(lon)}

    # filtro inicial por bounding box (corridas marcadas como 'ativa')
    corridas_bbox = Corrida.objects.filter(
        bbox_min_lat__lte=lat,
        bbox_max_lat__gte=lat,
        bbox_min_lon__lte=lon,
        bbox_max_lon__gte=lon,
        status='ativa'
    )

    corridas_encontradas = []
    for corrida in corridas_bbox:
        try:
            distancia = nearest_point_on_route((lat, lon), corrida.rota)
        except Exception:
            distancia = None

        if distancia is not None and distancia <= tolerancia:
            # serializa rota como [[lat, lon], ...]
            rota_serializada = []
            try:
                if isinstance(corrida.rota, (list, tuple)) and corrida.rota:
                    for pair in corrida.rota:
                        if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                            rota_serializada.append([float(pair[0]), float(pair[1])])
            except Exception:
                rota_serializada = []

            origem_lat = corrida.origem_lat if corrida.origem_lat is not None else (rota_serializada[0][0] if rota_serializada else 0.0)
            origem_lon = corrida.origem_lon if corrida.origem_lon is not None else (rota_serializada[0][1] if rota_serializada else 0.0)
            destino_lat = corrida.destino_lat if corrida.destino_lat is not None else (rota_serializada[-1][0] if rota_serializada else 0.0)
            destino_lon = corrida.destino_lon if corrida.destino_lon is not None else (rota_serializada[-1][1] if rota_serializada else 0.0)

            corrida_dict = {
                "id": corrida.id,
                "origem": str(corrida.origem),
                "destino": str(corrida.destino),
                "origem_lat": float(origem_lat),
                "origem_lon": float(origem_lon),
                "destino_lat": float(destino_lat),
                "destino_lon": float(destino_lon),
                "rota": rota_serializada,
                "horario_saida": corrida.horario_saida.strftime("%H:%M") if getattr(corrida, "horario_saida", None) else None,
                "horario_chegada": corrida.horario_chegada.strftime("%H:%M") if getattr(corrida, "horario_chegada", None) else None,
                "valor": float(corrida.valor) if corrida.valor is not None else 0.0,
                "vagas_disponiveis": int(corrida.vagas_disponiveis or 0),
                "distancia_m": float(getattr(corrida, "distancia_ao_passageiro", 0.0)),
            }
            corridas_encontradas.append(corrida_dict)

    return JsonResponse({
        'ok': True,
        'coords': coords,
        'corridas': corridas_encontradas
    }, json_dumps_params={'ensure_ascii': False})



@require_GET
@cache_page(30)  # cache simples: 30s (ajuste conforme necessidade)
def geocode_photon(request):
    q = request.GET.get('q', '').strip()
    if not q:
        return HttpResponseBadRequest("missing q")

    params = {
        'q': q,
        'limit': int(request.GET.get('limit', 6)),
    }
    # opcional: bias por lat/lon para priorizar resultados próximos ao usuário
    lat = request.GET.get('lat')
    lon = request.GET.get('lon')
    if lat and lon:
        params['lat'] = lat
        params['lon'] = lon

    # opcional: forçar idioma (ex: 'pt' ou 'en')
    lang = request.GET.get('lang')
    if lang:
        params['lang'] = lang

    try:
        headers = {'User-Agent': 'MeuAppCarona/1.0 (contato@seudominio.com)'}
        resp = requests.get(PHOTON_BASE, params=params, timeout=5, headers=headers)
        resp.raise_for_status()
        js = resp.json()
        features = []
        for f in js.get('features', []):
            coords = f.get('geometry', {}).get('coordinates', [None, None])
            props = f.get('properties', {})
            display = props.get('name') or props.get('street') or props.get('city') or props.get('country')
            # fallback para display_name do Photon (se tiver)
            display = display or props.get('osm_value') or props.get('display_name') or props.get('label')
            features.append({
                'display_name': props.get('name') or props.get('label') or f.get('properties'),
                'lat': coords[1],
                'lon': coords[0],
                'properties': props,
            })
        return JsonResponse(features, safe=False)
    except Exception:
        # degrade graciosamente: retornar lista vazia (ou logar o erro)
        return JsonResponse([], safe=False, status=200)