from django.core.cache import cache
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import CorridaForm
from .models import Corrida, SolicitacaoCarona
from .utils import geocode_endereco, gerar_rota, nearest_point_on_route
from django.views.decorators.http import require_POST, require_GET
from django.http import JsonResponse, HttpResponseBadRequest
import json, unicodedata, requests, logging, math
from datetime import datetime, timedelta, date, time
from django.urls import reverse
from django.views.decorators.cache import cache_page
from decimal import Decimal, InvalidOperation
from django.conf import settings
from django.db import IntegrityError, transaction, models as dj_models
from django.db.models import Prefetch
from notificacao.models import Notificacao



PHOTON_BASE = "https://photon.komoot.io/api/"
# Tolerâncias padrão (em metros)
TOLERANCIA_CIDADE = 5000
TOLERANCIA_ESTADO = 50000
TOLERANCIA_PAIS = 100000
TOLERANCIA_MIN = 100
TOLERANCIA_MAX = 200000

VELOCIDADE_MEDIA_KMH = 50

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


def geocode(request):
    query = request.GET.get("q", "")
    if not query:
        return JsonResponse({"error": "Parâmetro 'q' obrigatório"}, status=400)

    url = "https://api.openrouteservice.org/geocode/search"

    params = {
        "api_key": settings.ORS_API_KEY,
        "text": query,
        "boundary.country": "BR"
    }

    try:
        r = requests.get(url, params=params, timeout=5)
        data = r.json()

        # Extrair features de forma segura
        features = data.get("features", [])
        resultados = []

        for f in features:
            props = f.get("properties", {})
            geometry = f.get("geometry", {})

            # Pular se não tiver coords
            if "coordinates" not in geometry:
                continue

            lon, lat = geometry["coordinates"]

            resultados.append({
                "label": props.get("label", ""),
                "lat": lat,
                "lon": lon,
                "city": props.get("locality") or props.get("city"),
                "state": props.get("region"),
                "postcode": props.get("postalcode"),
            })

        return JsonResponse({"results": resultados})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

# 🛣 Geração de rota via ORS
def api_rota(request):
    # 1️⃣ Obter e validar coordenadas
    try:
        lat1 = float(request.GET.get("lat1"))
        lon1 = float(request.GET.get("lon1"))
        lat2 = float(request.GET.get("lat2"))
        lon2 = float(request.GET.get("lon2"))
    except (TypeError, ValueError) as e:
        logger.error(f"Coordenadas inválidas: {e}, GET params: {request.GET}")
        return JsonResponse({"error": "Coordenadas inválidas"}, status=400)

    # 2️⃣ Montar payload para ORS
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    body = {
        "coordinates": [
            [lon1, lat1],
            [lon2, lat2]
        ]
    }

    headers = {
        "Authorization": getattr(settings, "ORS_API_KEY", ""),
        "Content-Type": "application/json"
    }

    if not headers["Authorization"]:
        logger.error("Chave ORS_API_KEY não configurada no settings")
        return JsonResponse({"error": "Chave ORS não configurada"}, status=500)

    # 3️⃣ Chamada à API externa
    try:
        r = requests.post(url, json=body, headers=headers, timeout=10)
        r.raise_for_status()  # dispara HTTPError para status >= 400
    except requests.exceptions.Timeout:
        logger.error("Timeout ao chamar ORS API")
        return JsonResponse({"error": "Timeout ao chamar API externa"}, status=504)
    except requests.exceptions.HTTPError as e:
        logger.error(f"Erro HTTP na ORS API: {e}, resposta: {r.text}")
        return JsonResponse({"error": f"Erro HTTP na ORS API: {r.status_code}"}, status=r.status_code)
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro de requisição na ORS API: {e}")
        return JsonResponse({"error": "Erro na API externa"}, status=500)

    # 4️⃣ Validar resposta JSON
    try:
        data = r.json()
        if "features" not in data or not data["features"]:
            logger.error(f"Resposta ORS sem features: {data}")
            return JsonResponse({"error": "Não foi possível gerar rota"}, status=500)
    except ValueError as e:
        logger.error(f"JSON inválido da ORS API: {e}, resposta: {r.text}")
        return JsonResponse({"error": "Resposta inválida da API externa"}, status=500)

    # 5️⃣ Retornar rota para o frontend
    return JsonResponse(data, safe=False)



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

                    # ---------- CALCULAR HORÁRIO DE CHEGADA ----------
                    # Só faz sentido se o motorista informou horario_saida
                    if corrida.horario_saida:
                        try:
                            # distancia_m em metros -> km:
                            distancia_km = (distancia_m or 0) / 1000.0
                            # tempo em horas = distancia_km / velocidade_kmh
                            horas = distancia_km / VELOCIDADE_MEDIA_KMH if VELOCIDADE_MEDIA_KMH > 0 else 0
                            duracao = timedelta(seconds=int(round(horas * 3600)))

                            # precisamos somar TimeField + duracao -> use datetime temporário
                            # usamos a data informada ou hoje se não houver data
                            data_base = corrida.data if corrida.data else date.today()
                            dt_saida = datetime.combine(data_base, corrida.horario_saida)
                            dt_chegada = dt_saida + duracao
                            # salva apenas o time na TimeField
                            corrida.horario_chegada = dt_chegada.time()
                        except Exception:
                            # não falha todo o processo por cálculo de tempo; apenas não define horario_chegada
                            pass

                    corrida.save()
                    messages.success(request, "Corrida cadastrada com sucesso.")
                    return redirect('usuarios:pagina_inicial')

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
def deletar_corrida(request, corrida_id):
    corrida = get_object_or_404(Corrida, id=corrida_id)

    # verificação: dono (motorista) ou staff
    usuario_e_dono = getattr(corrida, "motorista", None) == request.user
    if not (usuario_e_dono or request.user.is_staff):
        # se for AJAX, retorna 403 JSON
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"error": "Sem permissão"}, status=403)
        messages.error(request, "Você não tem permissão para deletar esta corrida.")
        return redirect(reverse("corrida:lista_corridas"))

    if request.method == "POST":
        corrida.delete()
        # se requisição AJAX: responde JSON (frontend removerá a linha)
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": True})
        # caso normal: redireciona para lista (PRG)
        messages.success(request, "Corrida removida com sucesso.")
        return redirect(reverse("corrida:lista_corridas"))

    # Se chegar por GET (não esperado), redireciona para lista
    return redirect(reverse("corrida:lista_corridas"))


@login_required
@user_passes_test(is_motorista_ou_admin)
def dashboard_motorista(request):
    # Lógica para o dashboard do motorista
    return render(request, 'corrida/dashboard_motorista.html')  


@login_required
@user_passes_test(is_motorista_ou_admin)
def lista_corridas(request):
    print(">>> view lista_corridas chamada <<<")
    logger.error("view lista_corridas chamada")

    qs = Corrida.objects.filter(
        motorista=request.user
    ).order_by('-data', 'horario_saida').select_related('motorista')

    # Integração minha_solicitacao (apenas para saber se existe solicitação do usuário logado)
    if request.user.is_authenticated:
        solicit_qs = SolicitacaoCarona.objects.filter(passageiro=request.user)
        qs = qs.prefetch_related(
            Prefetch('solicitacoes', queryset=solicit_qs, to_attr='minha_solicitacoes')
        )

    corridas = list(qs)

    # Marca corrida.minha_solicitacao
    if request.user.is_authenticated:
        for corrida in corridas:
            lista = getattr(corrida, 'minha_solicitacoes', None)
            corrida.minha_solicitacao = lista[0] if lista else None
    else:
        for corrida in corridas:
            corrida.minha_solicitacao = None

    return render(request, 'corrida/lista_corridas.html', {
        'corridas': corridas
    })


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

def detalhe_corrida(request, pk):
    corrida = get_object_or_404(Corrida, id=pk)
    return render(request, 'corrida/detalhe_corrida.html', {'corrida': corrida})

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


@require_GET
@cache_page(30)  # opcional: remova/ajuste para debug
def geocode_ajax(request):
    endereco = request.GET.get("endereco", "").strip()
    if not endereco:
        return JsonResponse({"error": "endereco vazio"}, status=400)

    url = f"https://photon.komoot.io/api/?q={endereco}&lang=pt"
    resp = requests.get(url)

    if resp.status_code != 200:
        return JsonResponse({"error": "erro na API externa"}, status=500)

    data = resp.json()
    features = data.get("features", [])

    if not features:
        return JsonResponse({"error": "nenhum resultado"}, status=404)

    f = features[0]  # PEGAR APENAS O PRIMEIRO RESULTADO

    props = f.get("properties", {})
    geometry = f.get("geometry", {}).get("coordinates", [])

    if len(geometry) != 2:
        return JsonResponse({"error": "sem coordenadas"}, status=500)

    lon, lat = geometry  # atenção: Photon = [lon, lat]

    return JsonResponse({
        "lat": lat,
        "lon": lon,
        "bairro": props.get("district") or props.get("suburb"),
        "cidade": props.get("city"),
        "estado": props.get("state"),
        "cep": props.get("postcode"),
        "display_name": props.get("name")
    })

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

    # Se não informou endereço → página vazia
    if not endereco_passageiro:
        return render(request, "corrida/resultados_busca.html", {
            "corridas": corridas_serializadas,
            "coords": coords,
            "endereco": endereco_passageiro,
            "tolerancia_metros": tolerancia_metros,
        })

    termo_busca = normalizar_texto(endereco_passageiro)
    cache_key = f"geo:{termo_busca}"

    lat = lon = None

    # Tenta pegar do cache / geocode
    try:
        latlon_cache = cache.get(cache_key)
        if latlon_cache:
            lat, lon = latlon_cache
        else:
            lat, lon = geocode_endereco(endereco_passageiro)
            if lat is not None and lon is not None:
                cache.set(cache_key, (lat, lon), timeout=60 * 60)
    except Exception as e:
        logger.exception("Erro durante geocoding para '%s': %s", endereco_passageiro, e)
        lat = lon = None

    # ================================================================
    # 1) GEOCODE OK → BUSCA POR DISTÂNCIA
    # ================================================================
    if lat is not None and lon is not None:
        try:
            coords["lat"], coords["lon"] = float(lat), float(lon)
        except Exception:
            coords["lat"], coords["lon"] = 0.0, 0.0

        # tolerância dinâmica
        if tolerancia_metros is None:
            if "sp" in termo_busca or "sao paulo" in termo_busca or "são paulo" in termo_busca:
                tolerancia_metros = TOLERANCIA_CIDADE
            elif any(uf in termo_busca for uf in ["rj", "mg", "rs", "pr", "sc"]):
                tolerancia_metros = TOLERANCIA_ESTADO
            else:
                tolerancia_metros = TOLERANCIA_PAIS

        tolerancia_metros = max(TOLERANCIA_MIN, min(tolerancia_metros, TOLERANCIA_MAX))

        # → Busca corridas pelo algoritmo de proximidade
        corridas_encontradas = []
        try:
            for corrida, distancia in find_corridas_near(lat, lon, tolerancia_metros):
                corrida.distancia_ao_passageiro = distancia
                corridas_encontradas.append(corrida)
        except Exception as e:
            logger.exception("Erro ao filtrar corridas por distância: %s", e)

        # Buscar solicitações do usuário (uma única query)
        solicitacoes_map = {}
        try:
            corrida_ids = [c.id for c in corridas_encontradas]
            qs_solic = SolicitacaoCarona.objects.filter(
                corrida_id__in=corrida_ids,
                passageiro=request.user
            )
            for s in qs_solic:
                solicitacoes_map[s.corrida_id] = s
        except Exception as e:
            logger.exception("Erro ao buscar solicitações: %s", e)

        # Serialização final
        corridas_serializadas = []
        for c in corridas_encontradas:
            ser = serialize_corrida(c, distancia_m=c.distancia_ao_passageiro)

            solic = solicitacoes_map.get(c.id)
            ser["minha_solicitacao"] = {
                "id": solic.id,
                "status": solic.status,
            } if solic else None

            corridas_serializadas.append(ser)

    # ================================================================
    # 2) GEOCODE FALHOU → FALLBACK DE BUSCA POR TEXTO
    # ================================================================
    else:
        try:
            palavras = termo_busca.split()
            candidatos = []
            for corrida in Corrida.objects.filter(status="ativa"):
                origem_n = normalizar_texto(str(corrida.origem))
                destino_n = normalizar_texto(str(corrida.destino))
                if any(p in origem_n or p in destino_n for p in palavras):
                    candidatos.append(corrida)

            solicitacoes_map = {}
            corrida_ids = [c.id for c in candidatos]
            qs_solic = SolicitacaoCarona.objects.filter(
                corrida_id__in=corrida_ids,
                passageiro=request.user
            )
            for s in qs_solic:
                solicitacoes_map[s.corrida_id] = s

            corridas_serializadas = []
            for c in candidatos:
                ser = serialize_corrida(c)

                solic = solicitacoes_map.get(c.id)
                ser["minha_solicitacao"] = {
                    "id": solic.id,
                    "status": solic.status,
                } if solic else None

                corridas_serializadas.append(ser)

        except Exception as e:
            logger.exception("Erro em fallback textual: %s", e)
            corridas_serializadas = []

    # ================================================================
    # RENDER FINAL
    # ================================================================
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
def minhas_solicitacoes_api(request):
    """
    Retorna um mapeamento {corrida_id: solicitacao_id} para as corridas cujos ids
    foram passados via querystring ?ids=1,2,3.
    Só retorna solicitações pendentes do usuário (ou adapte o filtro).
    """
    ids_raw = request.GET.get('ids', '')
    if not ids_raw:
        return JsonResponse({'solicitacoes': {}})

    # limpar e converter para inteiros
    try:
        ids_list = [int(x) for x in ids_raw.split(',') if x.strip().isdigit()]
    except ValueError:
        return JsonResponse({'solicitacoes': {}}, status=400)

    qs = SolicitacaoCarona.objects.filter(
        passageiro=request.user,
        corrida_id__in=ids_list,
        status=SolicitacaoCarona.STATUS_PENDENTE
    ).only('id', 'corrida_id')

    mapping = {s.corrida_id: s.id for s in qs}
    return JsonResponse({'solicitacoes': mapping})


@login_required
@require_POST
def solicitar_carona(request, corrida_id):
    user = request.user
    corrida = get_object_or_404(Corrida, id=corrida_id, status='ativa')

    # Não permitir solicitar a própria corrida
    if corrida.motorista_id == user.id:
        return JsonResponse({'erro': 'Você não pode solicitar sua própria carona.'}, status=400)

    try:
        with transaction.atomic():
            solicit, created = SolicitacaoCarona.objects.get_or_create(
                corrida=corrida,
                passageiro=user,
                defaults={'status': SolicitacaoCarona.STATUS_PENDENTE}
            )

            if not created:
                if solicit.status == SolicitacaoCarona.STATUS_CANCELADA:
                    solicit.status = SolicitacaoCarona.STATUS_PENDENTE
                    solicit.save(update_fields=['status'])
                    created = True
                else:
                    return JsonResponse({'erro': 'Você já solicitou esta carona.'}, status=400)

            # 🔔 Criar notificação para o motorista (usando o campo `dados` para metadados)
            Notificacao.objects.create(
                usuario=corrida.motorista,
                titulo="Nova solicitação de vaga",
                mensagem=f"{user.nome} solicitou uma vaga na sua corrida de {corrida.origem} → {corrida.destino}.",
                tipo=Notificacao.TIPO_SOLICITACAO_RECEBIDA,
                dados={
                    "link": f"/corrida/detalhes/{corrida.id}/",
                    "corrida_id": corrida.id,
                    "solicitacao_id": solicit.id,
                },
            )

    except IntegrityError:
        logger.exception("IntegrityError ao criar solicitação de carona")
        return JsonResponse({'erro': 'Erro ao criar solicitação. Tente novamente.'}, status=500)
    except Exception:
        logger.exception("Erro inesperado em solicitar_carona")
        return JsonResponse({'erro': 'Erro interno. Tente novamente.'}, status=500)

    return JsonResponse({
        'ok': True,
        'id': solicit.id,
        'status': solicit.status,
        'data_solicitacao': solicit.data_solicitacao.isoformat()
    }, status=201 if created else 200)



@login_required
@require_POST
def cancelar_solicitacao(request, solicitacao_id):
    solicit = get_object_or_404(
        SolicitacaoCarona,
        id=solicitacao_id,
        passageiro=request.user
    )

    if solicit.status != SolicitacaoCarona.STATUS_PENDENTE:
        return JsonResponse({'erro': 'Não é possível cancelar esta solicitação.'}, status=400)

    solicit.status = SolicitacaoCarona.STATUS_CANCELADA
    solicit.save(update_fields=['status'])

    # 🔔 Criar notificação correta
    Notificacao.objects.create(
        usuario=solicit.corrida.motorista,
        titulo="Solicitação cancelada",
        mensagem=f"{request.user.nome} cancelou a solicitação da corrida {solicit.corrida.origem} → {solicit.corrida.destino}.",
        tipo=Notificacao.TIPO_SOLICITACAO_RESPONDIDA,
        dados={
            "corrida_id": solicit.corrida.id,
            "solicitacao_id": solicit.id
        }
    )

    return JsonResponse({'ok': True})



@login_required
@require_POST
def responder_solicitacao(request, solicitacao_id):
    action = request.POST.get('action')
    if action not in ('aceitar', 'rejeitar'):
        return JsonResponse({'erro': 'Ação inválida.'}, status=400)

    solicit = get_object_or_404(SolicitacaoCarona, id=solicitacao_id)
    corrida = solicit.corrida

    # Apenas o motorista pode responder
    if corrida.motorista_id != request.user.id:
        return JsonResponse({'erro': 'Sem permissão.'}, status=403)

    try:
        with transaction.atomic():
            corrida_locked = Corrida.objects.select_for_update().get(id=corrida.id)

            from notificacao.models import Notificacao

            if action == 'aceitar':

                # Sem vagas → não pode aceitar
                if corrida_locked.vagas_disponiveis <= 0:
                    return JsonResponse({'erro': 'Não há vagas disponíveis.'}, status=400)

                solicit.status = SolicitacaoCarona.STATUS_ACEITA
                solicit.save(update_fields=['status'])

                # decrementa vagas
                Corrida.objects.filter(id=corrida.id).update(
                    vagas_disponiveis=dj_models.F('vagas_disponiveis') - 1
                )

                # 🔔 Notifica passageiro
                Notificacao.objects.create(
                    usuario=solicit.passageiro,
                    mensagem=f"Sua solicitação para a corrida {corrida.origem} → {corrida.destino} foi ACEITA!",
                    link=f"/corrida/detalhes/{corrida.id}/",
                )

            else:  # rejeitar
                solicit.status = SolicitacaoCarona.STATUS_RECUSADA
                solicit.save(update_fields=['status'])

                # 🔔 Notifica o passageiro
                Notificacao.objects.create(
                    usuario=solicit.passageiro,
                    mensagem=f"Sua solicitação para a corrida {corrida.origem} → {corrida.destino} foi RECUSADA.",
                    link=f"/corrida/detalhes/{corrida.id}/",
                )

    except Exception:
        return JsonResponse({'erro': 'Erro interno ao processar a solicitação.'}, status=500)

    return JsonResponse({'ok': True, 'status': solicit.status})




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
@cache_page(30)
def geocode_photon(request):
    # aceita q (seu código) ou endereco (frontend antigo)
    q = request.GET.get('q') or request.GET.get('endereco') or ''
    q = q.strip()
    if not q:
        return HttpResponseBadRequest("missing q")

    params = {
        'q': q,
        'limit': int(request.GET.get('limit', 6)),
    }
    lat = request.GET.get('lat')
    lon = request.GET.get('lon')
    if lat and lon:
        params['lat'] = lat
        params['lon'] = lon

    lang = request.GET.get('lang')
    if lang:
        params['lang'] = lang

    try:
        headers = {'User-Agent': 'MeuAppCarona/1.0 (contato@seudominio.com)'}
        resp = requests.get(PHOTON_BASE, params=params, timeout=6, headers=headers)
        resp.raise_for_status()
        js = resp.json()
        features = []
        for f in js.get('features', []):
            coords = f.get('geometry', {}).get('coordinates', [None, None])
            props = f.get('properties', {}) or {}

            # monta display_name com mais cuidado
            parts = [
                props.get('name'),
                props.get('street'),
                props.get('suburb'),
                props.get('neighbourhood'),
                props.get('city') or props.get('town') or props.get('village'),
                props.get('state'),
                props.get('postcode'),
                props.get('country')
            ]
            display_name = ', '.join([p for p in parts if p])

            features.append({
                'display_name': display_name or props.get('label') or props.get('osm_value') or '',
                'lat': coords[1],
                'lon': coords[0],
                'address': {
                    'suburb': props.get('suburb'),
                    'neighbourhood': props.get('neighbourhood'),
                    'city': props.get('city') or props.get('town') or props.get('village'),
                    'state': props.get('state'),
                    'postcode': props.get('postcode'),
                },
                'properties': props,
            })
        return JsonResponse(features, safe=False)
    except Exception as e:
        logger.exception("geocode_photon error")
        # retorna lista vazia (cliente continua funcional), mas logamos o erro
        return JsonResponse([], safe=False, status=200)


@login_required
@require_GET
def minha_solicitacao_api(request, corrida_id):
    
    solicit = SolicitacaoCarona.objects.filter(corrida_id=corrida_id, passageiro=request.user).first()
    if not solicit:
        return JsonResponse({'ok': True, 'solicitacao': None})
    return JsonResponse({
        'ok': True,
        'solicitacao': {
            'id': solicit.id,
            'status': solicit.status,
            'data_solicitacao': solicit.data_solicitacao.isoformat() if solicit.data_solicitacao else None,
        }
    })



@login_required
@require_POST
def api_aceitar_solicitacao(request):
    try:
        corrida_id = int(request.POST.get('corrida_id'))
        solicitacao_id = int(request.POST.get('solicitacao_id'))
    except Exception:
        return HttpResponseBadRequest("IDs inválidos")

    solicitacao = SolicitacaoCarona.objects.filter(
        id=solicitacao_id,
        corrida_id=corrida_id,
        corrida__motorista=request.user
    ).first()

    if not solicitacao:
        return JsonResponse({"ok": False, "error": "Solicitação não encontrada"}, status=404)

    if solicitacao.status == SolicitacaoCarona.STATUS_ACEITA:
        return JsonResponse({"ok": False, "error": "Solicitação já aceita"}, status=400)

    solicitacao.status = SolicitacaoCarona.STATUS_ACEITA
    solicitacao.save(update_fields=['status'])

    # opcional: marcar notificação do passageiro como lida ou criar notificação
    Notificacao.objects.create(
        usuario=solicitacao.passageiro,
        titulo="Solicitação Aceita",
        mensagem=f"Sua solicitação para a corrida de {solicitacao.corrida.origem} → {solicitacao.corrida.destino} foi aceita!",
        tipo=Notificacao.TIPO_SOLICITACAO_RESPONDIDA,
        dados={"corrida_id": solicitacao.corrida.id, "solicitacao_id": solicitacao.id}
    )

    return JsonResponse({"ok": True, "status": solicitacao.status})