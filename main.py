import requests
from time import sleep

# Open Street Maps Geocoding API endpoint
GEOCODING_API_URL = "https://nominatim.openstreetmap.org/reverse"


def geocode_reverse(lat, lon, cache={}):
    """
    Consulta geocodificação reversa da API OpenStreetMap, com cache para evitar múltiplas chamadas.
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
            road = data.get('address', {}).get('road')
            cache[(lat, lon)] = road
            return road
        except ValueError:
            pass
    return None


def get_correct_route(points):
    """
    Obtém as ruas do trajeto real do veículo, ignorando nomes de ruas inadequados ou cruzamentos.

    :param points: Lista de coordenadas (longitude, latitude)
    :return: Lista de nomes das ruas pelas quais o veículo realmente passou.
    """
    previous_street = None
    street_names = []
    for i, (lon, lat) in enumerate(points):
        road_name = geocode_reverse(lat, lon)  # Consulta a rua utilizando geocodificação reversa

        # Verifica se o ponto está consistente com as ruas anteriores/subsequentes
        if road_name:
            # Checar cruzamentos com base na sequência (descarta ruas não consistentes)
            if i > 0 and i < len(points) - 1:  # Ponto intermediário
                previous_point_street = street_names[-1] if len(street_names) > 0 else None
                next_point_road = geocode_reverse(points[i + 1][1], points[i + 1][0])

                # Se a rua atual diverge de ambas (anterior e posterior), ignora
                if road_name != previous_point_street and road_name != next_point_road:
                    print(f"Ignorando rua {road_name} em ({lat}, {lon}): possível cruzamento inconsistente.")
                    continue

            # Adiciona a rua ao itinerário
            if road_name != previous_street:  # Nome da rua mudou
                street_names.append(road_name)
                previous_street = road_name

    return street_names


# Coordenadas do itinerário
route_coordinates = [
    (-43.181245, -22.901718),  # Avenida Presidente Vargas
    (-43.18125, -22.90172),  # Avenida Presidente Vargas
    (-43.18158, -22.90182),  # Cruzamento: ignorar Marechal Floriano
    (-43.18214, -22.90096),  # Cruzamento: retornar Rua Uruguaiana
    (-43.18213, -22.90089),  # Rua Uruguaiana
    (-43.18204, -22.90069),  # Rua Uruguaiana
    (-43.18177, -22.90003),  # Rua Acre
    (-43.18177, -22.900029),  # Rua Acre (repetido)
    (-43.181057, -22.898303),  # Rua Acre
]

# Processa os nomes das ruas do itinerário
street_names = get_correct_route(route_coordinates)
print("Ruas percorridas no itinerário:", " | ".join(street_names))
