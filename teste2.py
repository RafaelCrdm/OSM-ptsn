import json
import math
import requests
import time
from typing import List, Dict, Tuple, Optional
import sqlite3


class BusRouteNavigator:
    # Tipos de via inadequados para ônibus (conforme documentação OSM)
    UNSUITABLE_WAYS = {
        'cycleway', 'footway', 'path', 'pedestrian', 'steps', 'track',
        'bridleway', 'raceway', 'bus_guideway', 'escape', 'service'
    }

    def __init__(self, geojson_path: str, cache_db: str = 'bus_street_names_cache.db'):
        self.geojson_path = geojson_path
        self.cache_db = cache_db

        with open(geojson_path) as f:
            self.geojson = json.load(f)

        self._init_cache()
        self.segments = self._process_segments()

    def _init_cache(self):
        """Inicializa o banco de dados SQLite para cache"""
        self.conn = sqlite3.connect(self.cache_db)
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS street_names (
                lat REAL,
                lon REAL,
                street_name TEXT,
                highway_type TEXT,
                timestamp INTEGER,
                PRIMARY KEY (lat, lon)
            )
        ''')
        self.conn.commit()

    def _process_segments(self) -> List[Dict]:
        """Processa os segmentos do GeoJSON"""
        segments = []
        for feature in self.geojson['features']:
            coords = feature['geometry']['coordinates']
            segment = {
                'id': feature['properties']['id_segmento_int'],
                'coordinates': coords,
                'start': coords[0],
                'end': coords[-1],
                'length': self._calculate_segment_length(coords)
            }
            segments.append(segment)
        return segments

    def _calculate_segment_length(self, coords: List[List[float]]) -> float:
        """Calcula o comprimento de um segmento em metros"""
        length = 0
        for i in range(len(coords) - 1):
            length += self._haversine_distance(coords[i], coords[i + 1])
        return length

    def _haversine_distance(self, coord1: List[float], coord2: List[float]) -> float:
        """Calcula a distância entre duas coordenadas em metros"""
        lat1, lon1 = coord1[1], coord1[0]
        lat2, lon2 = coord2[1], coord2[0]

        R = 6371000  # Raio da Terra em metros
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (math.sin(delta_phi / 2) ** 2 +
             math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def _get_street_info_from_cache(self, lat: float, lon: float) -> Optional[tuple]:
        """Obtém informações da rua do cache"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT street_name, highway_type FROM street_names WHERE lat = ? AND lon = ?', (lat, lon))
        result = cursor.fetchone()
        return result if result else None

    def _save_street_info_to_cache(self, lat: float, lon: float, street_name: str, highway_type: str):
        """Salva informações da rua no cache"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO street_names 
            (lat, lon, street_name, highway_type, timestamp) 
            VALUES (?, ?, ?, ?, ?)
        ''', (lat, lon, street_name, highway_type, int(time.time())))
        self.conn.commit()

    def get_street_info(self, coord: List[float]) -> Dict:
        """
        Obtém informações da rua para uma coordenada, filtrando por tipos adequados para ônibus.

        :param coord: Lista [longitude, latitude]
        :return: Dicionário com nome da rua e tipo, ou None se for via inadequada
        """
        lon, lat = coord[0], coord[1]

        # Tenta obter do cache primeiro
        cached_info = self._get_street_info_from_cache(lat, lon)
        if cached_info:
            street_name, highway_type = cached_info
            if highway_type in self.UNSUITABLE_WAYS:
                return None
            return {'name': street_name, 'type': highway_type}

        # Consulta a API do Nominatim
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"

        try:
            time.sleep(1)  # Respeita o limite da API
            headers = {'User-Agent': 'BusNavigator/1.0 (seu-email@exemplo.com)'}
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()

            # Obtém tipo da via (highway tag do OSM)
            highway_type = data.get('extratags', {}).get('highway') or \
                           data.get('address', {}).get('road_type')

            # Se for via inadequada, retorna None
            if highway_type in self.UNSUITABLE_WAYS:
                self._save_street_info_to_cache(lat, lon, 'VIA INADEQUADA', highway_type)
                return None

            street_name = data.get('address', {}).get('road', 'Rua Desconhecida')

            # Salva no cache
            self._save_street_info_to_cache(lat, lon, street_name, highway_type or 'unknown')

            return {'name': street_name, 'type': highway_type}

        except Exception as e:
            print(f"Erro ao obter informações da rua: {e}")
            return None

    def get_bus_route_streets(self) -> List[Dict]:
        """
        Retorna as ruas adequadas para ônibus na ordem do percurso.
        """
        route_streets = []
        current_street = None

        for segment in self.segments:
            # Obtém informações no ponto médio do segmento
            mid_point = segment['coordinates'][len(segment['coordinates']) // 2]
            street_info = self.get_street_info(mid_point)

            if not street_info:
                continue  # Ignora vias inadequadas

            street_name = street_info['name']

            if current_street is None:
                current_street = {
                    'name': street_name,
                    'type': street_info['type'],
                    'length': segment['length'],
                    'segments': [segment['id']],
                    'start': segment['start'],
                    'end': segment['end']
                }
            elif street_name == current_street['name']:
                current_street['length'] += segment['length']
                current_street['segments'].append(segment['id'])
                current_street['end'] = segment['end']
            else:
                route_streets.append(current_street)
                current_street = {
                    'name': street_name,
                    'type': street_info['type'],
                    'length': segment['length'],
                    'segments': [segment['id']],
                    'start': segment['start'],
                    'end': segment['end']
                }

        if current_street:
            route_streets.append(current_street)

        return route_streets

    def generate_bus_route_report(self, output_file: str = 'rotas_onibus.txt'):
        """
        Gera um relatório completo das ruas adequadas para ônibus.
        """
        bus_streets = self.get_bus_route_streets()

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("RELATÓRIO DE ROTAS PARA ÔNIBUS\n")
            f.write("===============================\n\n")
            f.write(f"Arquivo GeoJSON processado: {self.geojson_path}\n")
            f.write(f"Total de ruas adequadas: {len(bus_streets)}\n\n")

            f.write("DETALHES DO TRAJETO:\n")
            f.write("--------------------\n")

            for i, street in enumerate(bus_streets, 1):
                f.write(f"\n{i}. {street['name']}\n")
                f.write(f"   Tipo de via: {street['type'] or 'Não especificado'}\n")
                f.write(f"   Extensão: {street['length']:.0f} metros\n")
                f.write(f"   Segmentos: {', '.join(street['segments'])}\n")
                f.write(f"   Início: {street['start'][1]}, {street['start'][0]}\n")
                f.write(f"   Fim: {street['end'][1]}, {street['end'][0]}\n")

            f.write("\nOBS: Foram filtradas ciclovias, vias pedestres e outros tipos inadequados.\n")

        print(f"Relatório gerado em '{output_file}'")


# Exemplo de uso
if __name__ == "__main__":
    navigator = BusRouteNavigator('teste.geojson')

    try:
        print("Processando rotas para ônibus...")
        bus_streets = navigator.get_bus_route_streets()

        print("\n--- Ruas adequadas para ônibus ---")
        for i, street in enumerate(bus_streets, 1):
            print(f"{i}. {street['name']} ({street['type']}) - {street['length']:.0f}m")

        # Gera relatório completo
        navigator.generate_bus_route_report()

    finally:
        navigator.close()
    print("Processo concluído!")