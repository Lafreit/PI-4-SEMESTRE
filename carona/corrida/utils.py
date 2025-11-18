import requests
from django.conf import settings
import openrouteservice
from math import radians, cos, sin, asin, sqrt

ORS_BASE_URL = "https://api.openrouteservice.org"
ORS_API_KEY = getattr(settings, "ORS_API_KEY", None)

def geocode_endereco(endereco):
    """
    Converte um endereço em coordenadas (latitude, longitude)
    usando o serviço de geocodificação do ORS.
    """
    if not ORS_API_KEY:
        print("ORS_API_KEY não definida!")
        return None, None

    try:
        url = f"{ORS_BASE_URL}/geocode/search"
        params = {
            "api_key": ORS_API_KEY,
            "text": endereco,
            "size": 1
        }
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        features = data.get("features")
        if not features:
            print("Nenhuma coordenada encontrada para:", endereco)
            return None, None

        coords = features[0]["geometry"]["coordinates"]
        return coords[1], coords[0]  # lat, lon

    except Exception as e:
        print("Erro ao geocodificar endereço:", e)
        return None, None


def gerar_rota(lat_origem, lon_origem, lat_destino, lon_destino):
    """
    Gera uma rota entre dois pontos usando a API Directions do ORS.
    Retorna: lista de pontos (lat, lon), distância em metros e número de pontos.
    """
    if not ORS_API_KEY:
        print("ORS_API_KEY não definida!")
        return [], 0, 0

    try:
        url = f"{ORS_BASE_URL}/v2/directions/driving-car"
        headers = {
            "Authorization": ORS_API_KEY,
            "Accept": "application/json"
        }
        payload = {
            "coordinates": [
                [lon_origem, lat_origem],
                [lon_destino, lat_destino]
            ],
            "format": "geojson"
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        print("ORS status:", resp.status_code)
        data = resp.json()

        if "routes" not in data or not data["routes"]:
            from pprint import pprint
            print("Resposta ORS sem 'routes':")
            pprint(data)
            return [], 0, 0

        route = data["routes"][0]
        distancia = route["summary"]["distance"]

        # Decodifica a geometria da rota (polyline) em coordenadas
        coords = openrouteservice.convert.decode_polyline(route["geometry"])["coordinates"]
        pontos = [(lat, lon) for lon, lat in coords]

        return pontos, distancia, len(pontos)

    except Exception as e:
        print("Erro ao gerar rota (exception):", repr(e))
        return [], 0, 0


def haversine(lat1, lon1, lat2, lon2):
    """
    Calcula a distância entre dois pontos em metros usando a fórmula de Haversine.
    """
    R = 6371000  # raio da Terra em metros
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c

def nearest_point_on_route(ponto, rota):
    """
    Retorna a menor distância entre um ponto (lat, lon) e uma rota (lista de [lat, lon]).
    """
    lat, lon = ponto
    return min(haversine(lat, lon, p[0], p[1]) for p in rota) if rota else float("inf")