import requests
from shapely.geometry import Point, LineString
from time import sleep

# Open Street Maps Geocoding API endpoint
GEOCODING_API_URL = "https://nominatim.openstreetmap.org/reverse"


def geocode_reverse(lat, lon, cache={}):
    """
    Consulta geocodificação reversa da API OpenStreetMap, com cache.
    """
    sleep(1)  # Pausa para respeitar a política de uso da API
    if (lat, lon) in cache:
        return cache[(lat, lon)]

    headers = {
        'User-Agent': 'BusRouteApp/1.0 (meuemail@example.com)'
    }
    url = f'{GEOCODING_API_URL}?lat={lat}&lon={lon}&format=json'
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        try:
            data = response.json()
            address = data.get('address', {})
            road = address.get('road')
            if road:
                cache[(lat, lon)] = address
                return address
        except ValueError:
            pass
    return None


def is_valid_street(address):
    """
    Verifica se o endereço é válido e elimina somente cruzamentos explícitos.
    """
    if not address:
        return None

    road_name = address.get('road', '')

    # Ignorar cruzamentos explícitos com " e " ou "&"
    if ' e ' in road_name.lower() or '&' in road_name:
        return None

    # Retorna o nome da rua se for válido
    return road_name


def get_street_itinerary(points):
    """
    Obtém o nome das ruas que fazem parte do itinerário do ônibus.
    :param points: Lista de pontos (longitude, latitude)
    :return: Lista com nomes das ruas únicas no itinerário
    """
    previous_street = None
    street_names = []

    for lon, lat in points:
        # Obtém o endereço via geocodificação reversa
        address = geocode_reverse(lat, lon)

        # Depuração: log para entender o que a API retorna
        if address:
            print(f"Endereço retornado para ({lat}, {lon}): {address}")
        else:
            print(f"Nenhum endereço retornado para ({lat}, {lon})")

        # Validar se é uma rua válida e relevante
        road_name = is_valid_street(address)

        if road_name:
            print(f"Rua válida identificada: {road_name}")
        else:
            print(f"Rua ignorada para o ponto ({lat}, {lon})")

        # Adiciona rua ao itinerário apenas se for diferente da anterior
        if road_name and road_name != previous_street:
            street_names.append(road_name)
            previous_street = road_name

    return street_names


# Exemplo de Itinerário com Coordenadas (longitude, latitude)
route_coordinates = [
    (-43.181245, -22.901718),  # Avenida Presidente Vargas
    (-43.18125, -22.90172),  # Avenida Presidente Vargas (repetido próximo)
    (-43.18158, -22.90182),  # Cruzamento (ignorar Marechal Floriano)
    (-43.18213, -22.90089),  # Rua Uruguaiana
    (-43.18177, -22.90003),  # Rua Acre
    (-43.18177, -22.900029),  # Rua Acre (repetida)
]

# Processa os nomes das ruas do itinerário
street_names = get_street_itinerary(route_coordinates)
print("Ruas percorridas no itinerário:", " | ".join(street_names))
