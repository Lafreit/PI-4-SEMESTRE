from django.core.cache import cache
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import CorridaForm
from .models import Corrida, SolicitacaoCarona
from .utils import geocode_endereco, gerar_rota, nearest_point_on_route
from django.views.decorators.http import require_POST, require_GET
from django.http import JsonResponse, HttpResponseBadRequest
import json
import unicodedata
import requests
from django.views.decorators.cache import cache_page
from decimal import Decimal, InvalidOperation
from django.conf import settings
import logging
import math


PHOTON_BASE = "https://photon.komoot.io/api/"
# Tolerâncias padrão (em metros)
TOLERANCIA_CIDADE = 5000
TOLERANCIA_ESTADO = 50000
TOLERANCIA_PAIS = 100000
TOLERANCIA_MIN = 100
TOLERANCIA_MAX = 200000

logger = logging.getLogger(__name__)


def is_motorista(user):
    return (
        user.is_authenticated
        and getattr(user, "tipo_usuario", "") == "motorista"
    )

def is_passageiro(user):
    return (
        user.is_authenticated
        and getattr(user, "tipo_usuario", "") == "passageiro"
    )

def is_admin(user):
    return (
        user.is_authenticated
        and getattr(user, "tipo_usuario", "") == "admin"
    )

def is_motorista_ou_admin(user):
    return user.is_authenticated and user.tipo_usuario in ["motorista", "admin"]


def _haversine_m(lat1, lon1, lat2, lon2):
    # retorna distância em metros entre dois pontos (haversine)
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c
 

def gerar_rota_e_apurar(origem_lat, origem_lon, destino_lat, destino_lon, profile='driving-car', timeout=8):
 
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


# helpers de busca e serialização ------------------------------------------------

def _rota_para_lista(rota):
    """Garante lista [[lat, lon], ...] segura."""
    rota_serializada = []
    try:
        if isinstance(rota, (list, tuple)) and rota:
            for pair in rota:
                if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                    rota_serializada.append([float(pair[0]), float(pair[1])])
    except Exception:
        rota_serializada = []
    return rota_serializada


def serialize_corrida(corrida, distancia_m=None):
    """Retorna dict serializável para template / API."""
    rota_serializada = _rota_para_lista(corrida.rota)

    origem_lat = corrida.origem_lat if corrida.origem_lat is not None else (rota_serializada[0][0] if rota_serializada else 0.0)
    origem_lon = corrida.origem_lon if corrida.origem_lon is not None else (rota_serializada[0][1] if rota_serializada else 0.0)
    destino_lat = corrida.destino_lat if corrida.destino_lat is not None else (rota_serializada[-1][0] if rota_serializada else 0.0)
    destino_lon = corrida.destino_lon if corrida.destino_lon is not None else (rota_serializada[-1][1] if rota_serializada else 0.0)

    horario_saida_str = corrida.horario_saida.strftime("%H:%M") if getattr(corrida, "horario_saida", None) else None
    horario_chegada_str = corrida.horario_chegada.strftime("%H:%M") if getattr(corrida, "horario_chegada", None) else None

    return {
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
        "distancia_m": float(distancia_m) if distancia_m is not None else float(getattr(corrida, "distancia_ao_passageiro", 0.0)),
    }


def find_corridas_near(lat, lon, tolerancia_metros):
    """
    Versão robusta:
    - expande bbox com margem derivada da tolerância
    - tenta nearest_point_on_route quando rota presente
    - fallback para distância origem/destino quando rota ausente
    - ordena por distância e sempre retorna lista (possivelmente vazia)
    """
    resultados = []
    try:
        if lat is None or lon is None:
            return resultados

        # margem em graus (~1 grau ≈ 111 km) — aproximação suficiente aqui
        margem_deg = max(0.002, (tolerancia_metros / 111000.0))  # mínimo ~0.002° (~200m)
        lat_min = lat - margem_deg
        lat_max = lat + margem_deg
        lon_min = lon - margem_deg
        lon_max = lon + margem_deg

        # primeiro: corridas cujo bbox (expandido) contenha o ponto (mais eficiente)
        qs_bbox = Corrida.objects.filter(
            bbox_min_lat__lte=lat_max,
            bbox_max_lat__gte=lat_min,
            bbox_min_lon__lte=lon_max,
            bbox_max_lon__gte=lon_min,
            status='ativa'
        )

        ids_considerados = set(qs_bbox.values_list('id', flat=True))

        # também considere as corridas ativas restantes (caso bbox não esteja populado corretamente)
        qs_restantes = Corrida.objects.filter(status='ativa').exclude(id__in=ids_considerados)

        # cria um iterador que primeiro itera pelo bbox e depois pelos restantes
        candidatos = list(qs_bbox) + list(qs_restantes)

        for corrida in candidatos:
            # tenta usar rota primeiro
            distancia = None

            rota = getattr(corrida, 'rota', None)
            if rota:
                try:
                    distancia = nearest_point_on_route((lat, lon), rota)
                except Exception as e:
                    # log para debug, mas não explode
                    logger.debug("nearest_point_on_route falhou para corrida %s: %s", corrida.id, e)
                    distancia = None

            # se distancia não obtida via rota, tenta usar origem/destino como fallback
            if distancia is None:
                # tenta origens/destinos explícitos, se existirem
                try:
                    o_lat = getattr(corrida, 'origem_lat', None)
                    o_lon = getattr(corrida, 'origem_lon', None)
                    d_lat = getattr(corrida, 'destino_lat', None)
                    d_lon = getattr(corrida, 'destino_lon', None)
                    candidatos_dist = []
                    if o_lat is not None and o_lon is not None:
                        candidatos_dist.append(_haversine_m(lat, lon, float(o_lat), float(o_lon)))
                    if d_lat is not None and d_lon is not None:
                        candidatos_dist.append(_haversine_m(lat, lon, float(d_lat), float(d_lon)))
                    if candidatos_dist:
                        distancia = min(candidatos_dist)
                except Exception:
                    distancia = None

            # se ainda sem distancia, ignora
            if distancia is None:
                continue

            if distancia <= tolerancia_metros:
                resultados.append((corrida, round(distancia, 1)))

        # ordenar por distância crescente
        resultados.sort(key=lambda t: t[1])
        return resultados

    except Exception as e:
        logger.exception("Erro em find_corridas_near: %s", e)
        return []


@login_required(login_url='usuarios:login')
@user_passes_test(is_motorista_ou_admin, login_url='pagina_inicial')
def cadastrar_corrida(request):
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
                    corrida.rota = rota
                    corrida.distancia_m = distancia_m
                    corrida.pontos_count = pontos_count

                    # atualiza bbox com base na rota
                    try:
                        corrida.set_bbox_from_rota()
                    except Exception:
                        # não deixa quebrar por erro no cálculo do bbox
                        pass

                    corrida.save()
                    messages.success(request, "Corrida cadastrada com sucesso.")
                    return redirect('corrida:lista')

                except requests.RequestException:
                    form.add_error(None, "Não foi possível gerar a rota agora (erro de comunicação). Tente novamente mais tarde.")
                except ValueError as e:
                    form.add_error(None, f"Erro ao gerar rota: {str(e)}")
                except Exception:
                    form.add_error(None, "Erro inesperado ao gerar rota. Contate o administrador.")
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = CorridaForm()

    return render(request, 'corrida/cadastrar_corrida.html', {'form': form})



@login_required
@user_passes_test(is_motorista_ou_admin)
def dashboard_motorista(request):
    # Lógica para o dashboard do motorista
    return render(request, 'corrida/dashboard_motorista.html')  

@login_required
@user_passes_test(is_motorista_ou_admin)
def lista_corridas(request):
    # Lógica para listar corridas
    corridas = Corrida.objects.filter(motorista=request.user).order_by('-data','horario_saida')

    context = {
        'corridas': corridas
    }

    return render(request, 'corrida/lista_corridas.html', context)

@login_required
@user_passes_test(is_motorista_ou_admin)
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
def historico_corridas(request):
    # Lógica para mostrar o histórico de corridas
    return render(request, 'corrida/historico_corridas.html')

@login_required
def detalhes_corrida(request, corrida_id):
    # Lógica para mostrar detalhes de uma corrida específica
    return render(request, 'corrida/detalhes_corrida.html')

@login_required
@user_passes_test(is_motorista_ou_admin)
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

#------------------------------------------------------------------------------------#
#                               normalizando para a busca                            #
#------------------------------------------------------------------------------------#

def remover_acentos(txt):
    if not txt:
        return ""
    return ''.join(
        c for c in unicodedata.normalize('NFKD', txt)
        if not unicodedata.combining(c)
    )

def normalizar_texto(txt):
    return remover_acentos(txt).strip().lower()


#------------------------------------------------------------------------------------#
@login_required
def buscar_corridas(request):
    endereco_passageiro = request.GET.get("endereco", "").strip()
    tolerancia_param = request.GET.get("tolerancia")
    try:
        tolerancia_metros = int(float(tolerancia_param)) if tolerancia_param else None
    except (ValueError, TypeError):
        tolerancia_metros = None

    coords = {"lat": 0.0, "lon": 0.0}
    corridas_serializadas = []

    if not endereco_passageiro:
        # nada a buscar
        return render(request, "corrida/resultados_busca.html", {
            "corridas": corridas_serializadas,
            "coords": coords,
            "endereco": endereco_passageiro,
            "tolerancia_metros": tolerancia_metros,
        })

    termo_busca = normalizar_texto(endereco_passageiro)
    cache_key = f"geo:{termo_busca}"

    # tenta obter lat/lon do cache ou geocoding, com tratamento de erro
    lat = lon = None
    try:
        latlon_cache = cache.get(cache_key)
        if latlon_cache:
            lat, lon = latlon_cache
        else:
            lat, lon = geocode_endereco(endereco_passageiro)
            # só cacheia se vierem valores válidos
            if lat is not None and lon is not None:
                cache.set(cache_key, (lat, lon), timeout=60 * 60)
    except Exception as e:
        # loga a exceção completa — evita 500 retornando fallback textual
        logger.exception("Erro durante geocoding para '%s': %s", endereco_passageiro, e)
        lat = lon = None

    if lat is not None and lon is not None:
        try:
            coords["lat"], coords["lon"] = float(lat), float(lon)
        except Exception:
            coords["lat"], coords["lon"] = 0.0, 0.0

        # tolerância dinâmica quando não informada
        if tolerancia_metros is None:
            if "sp" in termo_busca or "sao paulo" in termo_busca or "são paulo" in termo_busca:
                tolerancia_metros = TOLERANCIA_CIDADE
            elif any(uf in termo_busca for uf in ["rj", "mg", "rs", "pr", "sc"]):
                tolerancia_metros = TOLERANCIA_ESTADO
            else:
                tolerancia_metros = TOLERANCIA_PAIS

        tolerancia_metros = max(TOLERANCIA_MIN, min(tolerancia_metros, TOLERANCIA_MAX))

        corridas_encontradas = []
        # find_corridas_near já faz bbox + nearest_point; deixamos try/except extra por segurança
        try:
            for corrida, distancia in find_corridas_near(lat, lon, tolerancia_metros):
                corrida.distancia_ao_passageiro = distancia
                corridas_encontradas.append(corrida)
        except Exception as e:
            logger.exception("Erro ao filtrar corridas por distância: %s", e)
            corridas_encontradas = []

        # serializa em segurança
        try:
            corridas_serializadas = [
                serialize_corrida(c, distancia_m=getattr(c, "distancia_ao_passageiro", None))
                for c in corridas_encontradas
            ]
        except Exception as e:
            logger.exception("Erro ao serializar corridas: %s", e)
            corridas_serializadas = []

    else:
        # fallback: geocode falhou -> busca aproximada por texto (origem/destino),
        # sem filtro de distância (mostra candidatos por correspondência textual)
        try:
            palavras = termo_busca.split()
            candidatos = []
            for corrida in Corrida.objects.filter(status="ativa"):
                origem_n = normalizar_texto(str(corrida.origem))
                destino_n = normalizar_texto(str(corrida.destino))
                if any(p in origem_n or p in destino_n for p in palavras):
                    candidatos.append(corrida)
            corridas_serializadas = [serialize_corrida(c) for c in candidatos]
        except Exception as e:
            logger.exception("Erro em fallback textual na busca: %s", e)
            corridas_serializadas = []

    return render(request, "corrida/resultados_busca.html", {
        "corridas": corridas_serializadas,
        "coords": coords,
        "endereco": endereco_passageiro,
        "tolerancia_metros": tolerancia_metros,
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
    origem_text = request.GET.get('origem', '').strip()
    tol_param = request.GET.get('tol', None)

    if not origem_text:
        return JsonResponse({'ok': False, 'erro': 'Parâmetro "origem" obrigatório.'}, status=400)

    try:
        tolerancia = int(tol_param) if tol_param is not None else TOLERANCIA_CIDADE
    except (ValueError, TypeError):
        tolerancia = TOLERANCIA_CIDADE

    lat, lon = geocode_endereco(origem_text)
    if lat is None or lon is None:
        return JsonResponse({'ok': False, 'erro': 'Não foi possível geocodificar o endereço de origem.'}, status=404)

    corridas_encontradas = []
    resultados = find_corridas_near(lat, lon, tolerancia) or []
    for corrida, distancia in resultados:

        corrida_dict = serialize_corrida(corrida, distancia_m=distancia)
        corridas_encontradas.append(corrida_dict)

    return JsonResponse({'ok': True, 'coords': {'lat': float(lat), 'lon': float(lon)}, 'corridas': corridas_encontradas}, json_dumps_params={'ensure_ascii': False})



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