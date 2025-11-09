# corrida/scripts/popular_corridas_preciso.py
import random
import traceback
from time import sleep
from datetime import timedelta

from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model

from corrida.models import Corrida
from corrida.utils import gerar_rota  # tenta gerar rota via sua implementação

# helper: distância haversine (metros)
import math
def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2.0)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2.0)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# ---- Dados base (coordenadas aproximadas) ----
# bairros de São Paulo (amostra; coordenadas aproximadas centrais de cada bairro)
SP_BAIRROS = [
    ("Pinheiros", -23.561414, -46.691013),
    ("Vila Madalena", -23.558101, -46.688442),
    ("Moema", -23.607978, -46.662204),
    ("Itaim Bibi", -23.586035, -46.674316),
    ("Brooklin", -23.611616, -46.682766),
    ("Liberdade", -23.565849, -46.633965),
    ("Sé", -23.550520, -46.633308),
    ("Brás", -23.538444, -46.608056),
    ("Tatuapé", -23.532204, -46.568369),
    ("Vila Prudente", -23.587600, -46.569100),
]

# bairros da cidade de Araras (aproximações)
ARARAS_BAIRROS = [
    ("Centro", -22.3550, -47.3870),
    ("Jardim Primavera", -22.3590, -47.3920),
    ("Vila Operária", -22.3570, -47.3830),
    ("Vila Monteiro", -22.3580, -47.3890),
    ("Vila Santa Maria", -22.3565, -47.3950),
    ("Residencial Pinheiro", -22.3610, -47.3895),
    ("Cecap", -22.3605, -47.3840),
    ("Jardim Sampaio", -22.3620, -47.3925),
    ("Vila Cristina", -22.3540, -47.3900),
    ("Jardim Europa", -22.3585, -47.3865),
]

# pares de cidades próximas (cidade origem, lat, lon, cidade destino, lat, lon)
# mantive pares claramente dentro do estado de SP e relativamente próximos
CITY_PAIRS = [
    ("São Paulo", -23.550520, -46.633308, "Osasco", -23.532300, -46.791600),
    ("São Paulo", -23.550520, -46.633308, "Guarulhos", -23.462800, -46.533600),
    ("Campinas", -22.905560, -47.060830, "Sumaré", -22.820800, -47.266400),
    ("Jundiaí", -23.185700, -46.897800, "Itatiba", -23.000600, -46.866300),
    ("Santos", -23.960800, -46.333600, "São Vicente", -23.960000, -46.388000),
    ("Ribeirão Preto", -21.177500, -47.810300, "Sertãozinho", -21.128600, -47.975200),
    ("Bauru", -22.314500, -49.060600, "Marília", -22.217000, -49.945800),
    ("São José dos Campos", -23.223700, -45.900900, "Taubaté", -23.020500, -45.559700),
    ("Piracicaba", -22.733800, -47.647600, "Limeira", -22.564500, -47.401700),
    ("Americana", -22.737700, -47.333100, "Limeira", -22.564500, -47.401700),
]

def make_datetime_offset(hours=0):
    base = timezone.now()
    return (base + timedelta(hours=hours)).date(), (base + timedelta(hours=hours)).time()

def try_generate_rota(orig_lat, orig_lon, dest_lat, dest_lon):
    """
    Tenta usar gerar_rota; se falhar, retorna rota fallback (2 pontos), distancia (haversine) e pontos_count.
    """
    try:
        rota, distancia, n_pontos = gerar_rota(orig_lat, orig_lon, dest_lat, dest_lon)
        # normaliza rota
        rota_serializada = []
        if isinstance(rota, (list, tuple)):
            for p in rota:
                if isinstance(p, (list, tuple)) and len(p) >= 2:
                    rota_serializada.append([float(p[0]), float(p[1])])
        if not rota_serializada:
            # fallback if gerar_rota returns no points
            raise RuntimeError("rota vazia do gerar_rota, usando fallback")
        return rota_serializada, float(distancia) if distancia is not None else haversine_m(orig_lat, orig_lon, dest_lat, dest_lon), int(n_pontos) if n_pontos else len(rota_serializada)
    except Exception:
        # fallback simples
        dist = haversine_m(orig_lat, orig_lon, dest_lat, dest_lon)
        rota_fallback = [[float(orig_lat), float(orig_lon)], [float(dest_lat), float(dest_lon)]]
        return rota_fallback, float(dist), 2

def _create_corrida_entry(motorista, origem_text, destino_text,
                          origem_lat, origem_lon, destino_lat, destino_lon,
                          bairro_origem="", bairro_destino="",
                          cidade_origem="", cidade_destino="", estado="São Paulo", cep_origem="", cep_destino="",
                          data=None, horario_saida=None, horario_chegada=None,
                          vagas=3, valor=30.0, observacoes=""):
    """
    Cria um dicionário pronto para usar em Corrida.objects.create(...)
    (não salva - apenas retorna dicionário)
    """
    # prepare default data/time if None
    if data is None or horario_saida is None:
        d, t = make_datetime_offset(hours=random.randint(1, 72))
        data = data or d
        horario_saida = horario_saida or t
        # horario_chegada: +1h
        horario_chegada = horario_chegada or ( (timezone.now() + timedelta(hours=random.randint(2, 5))).time() )

    rota, distancia, pontos = try_generate_rota(origem_lat, origem_lon, destino_lat, destino_lon)

    corrida_data = {
        "motorista": motorista,
        "origem": origem_text,
        "bairro_origem": bairro_origem,
        "cidade_origem": cidade_origem or "São Paulo",
        "estado_origem": estado,
        "cep_origem": cep_origem,
        "destino": destino_text,
        "bairro_destino": bairro_destino,
        "cidade_destino": cidade_destino or "São Paulo",
        "estado_destino": estado,
        "cep_destino": cep_destino,
        "data": data,
        "horario_saida": horario_saida,
        "horario_chegada": horario_chegada,
        "vagas_disponiveis": vagas,
        "valor": valor,
        "observacoes": observacoes,
        "status": "ativa",
        "origem_lat": float(origem_lat),
        "origem_lon": float(origem_lon),
        "destino_lat": float(destino_lat),
        "destino_lon": float(destino_lon),
        "rota": rota,
        "distancia_m": float(distancia),
        "pontos_count": int(pontos),
    }
    return corrida_data

def run(dry_run=False, pause_between=0.2, max_items=None):
    """
    Popula o banco com 30 corridas conforme solicitado.
    - dry_run=True: mostra o que faria, não salva.
    - pause_between: segundos entre geração de rotas (ajuste se necessário).
    """
    User = get_user_model()

    # pega um motorista existente ou cria um
    motorista = User.objects.filter(tipo_usuario='motorista').first()
    if not motorista:
        # cria motorista de teste (ajuste email/nome se desejar)
        motorista = User.objects.create_user(email="motorista@example.com", nome="Motorista Teste", password="change_me_123")
        # se houver campo tipo_usuario, marca como motorista
        try:
            motorista.tipo_usuario = 'motorista'
            motorista.save()
        except Exception:
            pass
        print("Usuário motorista criado:", motorista)

    created = 0
    failed = 0

    items = []

    # 10 corridas SP bairro->bairro
    for i in range(10):
        b1 = SP_BAIRROS[i % len(SP_BAIRROS)]
        b2 = SP_BAIRROS[(i+3) % len(SP_BAIRROS)]  # garante bairro diferente
        origem_name = f"{b1[0]}, São Paulo"
        destino_name = f"{b2[0]}, São Paulo"
        data = None
        horario_saida = None

        cd = _create_corrida_entry(
            motorista=motorista,
            origem_text=origem_name,
            destino_text=destino_name,
            origem_lat=b1[1], origem_lon=b1[2],
            destino_lat=b2[1], destino_lon=b2[2],
            bairro_origem=b1[0],
            bairro_destino=b2[0],
            cidade_origem="São Paulo",
            cidade_destino="São Paulo",
            estado="São Paulo",
            cep_origem="01000-000",
            cep_destino="01000-001",
            data=data,
            horario_saida=horario_saida,
            horario_chegada=None,
            vagas=random.randint(1,4),
            valor=round(random.uniform(10, 80),2),
            observacoes="Corrida gerada automaticamente (SP bairro-bairro)."
        )
        items.append(cd)

    # 10 corridas Araras bairro->bairro
    for i in range(10):
        b1 = ARARAS_BAIRROS[i % len(ARARAS_BAIRROS)]
        b2 = ARARAS_BAIRROS[(i+4) % len(ARARAS_BAIRROS)]
        origem_name = f"{b1[0]}, Araras, SP"
        destino_name = f"{b2[0]}, Araras, SP"
        cd = _create_corrida_entry(
            motorista=motorista,
            origem_text=origem_name,
            destino_text=destino_name,
            origem_lat=b1[1], origem_lon=b1[2],
            destino_lat=b2[1], destino_lon=b2[2],
            bairro_origem=b1[0],
            bairro_destino=b2[0],
            cidade_origem="Araras",
            cidade_destino="Araras",
            estado="São Paulo",
            cep_origem="13600-000",
            cep_destino="13600-001",
            data=None,
            horario_saida=None,
            horario_chegada=None,
            vagas=random.randint(1,4),
            valor=round(random.uniform(8, 60),2),
            observacoes="Corrida gerada automaticamente (Araras bairro-bairro)."
        )
        items.append(cd)

    # 10 corridas cidade->cidade (pares próximos)
    for i, pair in enumerate(CITY_PAIRS):
        origem_city, o_lat, o_lon, destino_city, d_lat, d_lon = pair
        origem_name = f"{origem_city}"
        destino_name = f"{destino_city}"
        cd = _create_corrida_entry(
            motorista=motorista,
            origem_text=origem_name,
            destino_text=destino_name,
            origem_lat=o_lat, origem_lon=o_lon,
            destino_lat=d_lat, destino_lon=d_lon,
            bairro_origem="Centro",
            bairro_destino="Centro",
            cidade_origem=origem_city,
            cidade_destino=destino_city,
            estado="São Paulo",
            cep_origem="00000-000",
            cep_destino="00000-001",
            data=None,
            horario_saida=None,
            horario_chegada=None,
            vagas=random.randint(1,4),
            valor=round(random.uniform(25, 180),2),
            observacoes="Corrida gerada automaticamente (cidade-cidade próxima)."
        )
        items.append(cd)

    # opcional: limita quantidade processada
    if max_items:
        items = items[:max_items]

    print(f"Preparado para criar {len(items)} corridas (dry_run={dry_run}).")

    for idx, corrida_kwargs in enumerate(items, start=1):
        try:
            print(f"\n[{idx}/{len(items)}] Criando: {corrida_kwargs['origem']} -> {corrida_kwargs['destino']}")
            # set bbox from rota will be called after object creation
            if not dry_run:
                with transaction.atomic():
                    c = Corrida.objects.create(**corrida_kwargs)
                    # set bbox (usa método do model)
                    try:
                        c.set_bbox_from_rota()
                        c.save()
                    except Exception as e:
                        print("  aviso: falha ao set_bbox_from_rota():", e)
                created += 1
                print("  salvo id", c.id)
            else:
                print("  dry_run -> não salvo. exemplo rota length:", len(corrida_kwargs.get("rota") or []))
                # mostra amostra da rota
                print("  rota sample:", (corrida_kwargs.get("rota") or [])[:2])
            # pausa leve para evitar rate limits
            if pause_between:
                sleep(pause_between)
        except Exception as e:
            failed += 1
            print("  ERRO criando corrida:", e)
            traceback.print_exc()

    print("\nResumo: created =", created, "failed =", failed)
