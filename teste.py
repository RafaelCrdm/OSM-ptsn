import requests
import math


def fazer_map_matching(coordenadas, api_key, profile="driving-car"):
    """Faz o map matching dos pontos GPS usando a API do OpenRouteService."""
    url = f"https://api.openrouteservice.org/v2/matching/{profile}/geojson"

    # Formata as coordenadas para o formato esperado pela API
    coordenadas_formatadas = [[lon, lat] for lat, lon in coordenadas]

    # Corpo da requisição
    body = {
        "coordinates": coordenadas_formatadas,
        "geometry_simplify": "false",  # Mantém a geometria detalhada
    }

    # Cabeçalhos da requisição
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }

    # Faz a requisição POST
    response = requests.post(url, json=body, headers=headers)

    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Erro na requisição de map matching: {response.status_code}")
        print(response.text)
        return None


def obter_rota_openrouteservice(coordenadas, api_key, profile="driving-car"):
    """Obtém a rota e os nomes das ruas usando a API do OpenRouteService."""
    url = f"https://api.openrouteservice.org/v2/directions/{profile}/geojson"

    # Formata as coordenadas para o formato esperado pela API
    coordenadas_formatadas = [[lon, lat] for lat, lon in coordenadas]

    # Corpo da requisição
    body = {
        "coordinates": coordenadas_formatadas,
        "instructions": "true",  # Retorna instruções detalhadas
        "language": "pt"  # Define o idioma para português
    }

    # Cabeçalhos da requisição
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }

    # Faz a requisição POST
    response = requests.post(url, json=body, headers=headers)

    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Erro na requisição de rota: {response.status_code}")
        print(response.text)
        return None


def calcular_direcao(ponto1, ponto2):
    """Calcula a direção (ângulo) entre dois pontos."""
    lat1, lon1 = ponto1
    lat2, lon2 = ponto2
    d_lon = lon2 - lon1
    x = math.cos(math.radians(lat2)) * math.sin(math.radians(d_lon))
    y = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - math.sin(math.radians(lat1)) * math.cos(
        math.radians(lat2)) * math.cos(math.radians(d_lon))
    return math.degrees(math.atan2(x, y))


def extrair_nomes_das_ruas(data, coordenadas):
    """Extrai os nomes das ruas a partir dos dados da rota, com verificações adicionais."""
    nomes_ruas = []
    rua_anterior = None

    # Percorre as instruções da rota
    for segment in data["features"][0]["properties"]["segments"]:
        for step in segment["steps"]:
            nome_rua = step.get("name", "Sem nome")
            if nome_rua != "Sem nome":
                # Verifica se a rua é a mesma da anterior ou está alinhada com a direção do trajeto
                if rua_anterior is None or nome_rua == rua_anterior:
                    nomes_ruas.append(nome_rua)
                    rua_anterior = nome_rua
                else:
                    # Verifica a direção entre os pontos consecutivos
                    way_points = step.get("way_points", [])
                    if len(way_points) >= 2:  # Garante que há pontos suficientes
                        idx = way_points[0]  # Índice do ponto inicial do passo
                        if idx > 0 and idx + 1 < len(coordenadas):  # Verifica limites da lista
                            direcao = calcular_direcao(coordenadas[idx - 1], coordenadas[idx])
                            # Se a direção for consistente, adiciona a rua
                            if abs(direcao - calcular_direcao(coordenadas[idx],
                                                              coordenadas[idx + 1])) < 45:  # Tolerância de 45 graus
                                nomes_ruas.append(nome_rua)
                                rua_anterior = nome_rua

    return nomes_ruas


# Substitua pela sua chave de API do OpenRouteService
api_key = "5b3ce3597851110001cf6248a9f2f8c56df343e68716c3927fdc4a26"

# Lista de pontos (latitude, longitude)
coordenadas = [
    (-22.873791597461516, -43.331529749183595),
    (-22.873168376717455, -43.335290451426395),
    (-22.90182, -43.18158),
    (-22.90096, -43.18214),
    (-22.90089, -43.18213),
    (-22.90069, -43.18204),
    (-22.90003, -43.18177),
    (-22.900029, -43.18177),
    (-22.898303, -43.181057)
]

# Faz o map matching dos pontos GPS
dados_map_matching = fazer_map_matching(coordenadas, api_key, profile="driving-car")

if dados_map_matching:
    # Extrai as coordenadas corrigidas após o map matching
    coordenadas_corrigidas = [
        (coord[1], coord[0]) for coord in dados_map_matching["features"][0]["geometry"]["coordinates"]
    ]

    # Obtém a rota para carro usando as coordenadas corrigidas
    rota = obter_rota_openrouteservice(coordenadas_corrigidas, api_key, profile="walking")

    if rota:
        # Extrai os nomes das ruas
        nomes_ruas = extrair_nomes_das_ruas(rota, coordenadas_corrigidas)

        # Exibe o resultado
        print("Ruas pelas quais o trajeto passa (carro):")
        for rua in nomes_ruas:
            print(rua)
    else:
        print("Não foi possível obter a rota.")
else:
    print("Não foi possível fazer o map matching.")