"""
Calculateur de distance et prix pour les taxis
"""
import logging
import math
import requests
import os
from typing import Tuple


logger = logging.getLogger(__name__)

class DistanceCalculator:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.openrouteservice.org/v2/directions/driving-car"
        self.headers = {
            'Authorization': api_key,
            'Content-Type': 'application/json'
        }
        
        # Coordonnées GPS des stations principales de Dakar
        self.station_coordinates = {
            'parcelles assainies': (14.7677, -17.3980),
            'golf nord': (14.7589, -17.3944),
            'le plateau': (14.6770, -17.4370),
            'grande mosquee': (14.6828, -17.4472),
            'liberte 5': (14.7214, -17.4639),
            'liberte 6': (14.7261, -17.4700),
            'grand medine': (14.6986, -17.4689),
            'prefecture guediawaye': (14.7833, -17.4000),
            'dalal jam': (14.7750, -17.4050),
            'croisement 22': (14.7400, -17.4500),
            'papa gueye fall (petersen)': (14.7150, -17.4550),
            'place de la nation': (14.7050, -17.4580),
            'grand dakar': (14.7100, -17.4450),
            'dakar': (14.6928, -17.4467),
            'hann': (14.7200, -17.4200),
            'colobane': (14.6900, -17.4600),
            'hann maristes': (14.7150, -17.4250),
            'bountou pikine': (14.7500, -17.3900),
            'thiaroye': (14.7600, -17.3700),
            'yeumbeul': (14.7700, -17.3500),
            'rufisque': (14.7150, -17.2800),
            'bargny': (14.7000, -17.2300),
            'diamniadio': (14.7000, -17.2000),
            'yoff': (14.7500, -17.4800),
            'ouakam': (14.7300, -17.4900),
            'mermoz': (14.7000, -17.4700),
            'fann': (14.6800, -17.4700),
            'point e': (14.6900, -17.4650),
            'sacré coeur': (14.7100, -17.4750),
            'medina': (14.6750, -17.4400),
            'gare routière': (14.6800, -17.4350),
            'terminus libert 5': (14.7214, -17.4639),
            'terminus gudiawaye': (14.7833, -17.4000),
            'terminus keur massar': (14.7700, -17.3300),
            'scat urbam': (14.6700, -17.4400),
            'dieuppeul': (14.6850, -17.4550),
            'centre-ville': (14.6770, -17.4370)
        }
    
    def get_station_coordinates(self, station_name):
        """Trouve les coordonnées GPS d'une station"""
        station_lower = station_name.lower()
        
        # Recherche exacte
        for station, coords in self.station_coordinates.items():
            if station in station_lower or station_lower in station:
                return coords
        
        # Recherche partielle
        for station, coords in self.station_coordinates.items():
            if any(word in station_lower for word in station.split()):
                return coords
        
        # Fallback pour Dakar centre
        return (14.6928, -17.4467)
    
    def calculate_real_distance(self, depart, arrivee):
        """Calcule la distance réelle via l'API OpenRouteService"""
        try:
            # Obtenir les coordonnées
            dep_coords = self.get_station_coordinates(depart)
            arr_coords = self.get_station_coordinates(arrivee)
            
            # Préparer la requête API
            body = {
                "coordinates": [
                    [dep_coords[1], dep_coords[0]],  # [longitude, latitude]
                    [arr_coords[1], arr_coords[0]]
                ],
                "instructions": False,
                "preference": "recommended"
            }
            
            # Faire l'appel API
            response = requests.post(
                self.base_url,
                json=body,
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                distance_km = data['routes'][0]['summary']['distance'] / 1000  # Convertir en km
                duration_min = data['routes'][0]['summary']['duration'] / 60   # Convertir en minutes
                
                return round(distance_km, 1), round(duration_min, 1)
            else:
                logger.warning("API distance temporairement indisponible")
                return self.estimate_distance_fallback(depart, arrivee)
                
        except Exception as e:
            logger.warning("Calcul de distance approximatif utilisé")
            return self.estimate_distance_fallback(depart, arrivee)
    
    def estimate_distance_fallback(self, depart, arrivee):
        """Estimation de distance fallback si l'API échoue"""
        # Logique d'estimation basée sur la localisation
        peripherique_stations = ['parcelles', 'guediawaye', 'keur massar', 'pikine', 'rufisque', 'diamniadio', 'yoff']
        central_stations = ['plateau', 'dakar', 'medina', 'fann', 'point e', 'mermoz', 'sacré coeur', 'grand dakar']
        
        dep_lower = depart.lower()
        arr_lower = arrivee.lower()
        
        is_depart_peripherique = any(station in dep_lower for station in peripherique_stations)
        is_arrivee_peripherique = any(station in arr_lower for station in peripherique_stations)
        is_depart_central = any(station in dep_lower for station in central_stations)
        is_arrivee_central = any(station in arr_lower for station in central_stations)
        
        if is_depart_peripherique and is_arrivee_peripherique:
            return 18.0, 35  # Long trajet
        elif (is_depart_peripherique and is_arrivee_central) or (is_depart_central and is_arrivee_peripherique):
            return 12.0, 25  # Trajet moyen
        else:
            return 6.0, 15   # Trajet court

class TaxiPriceCalculator:
    def __init__(self, api_key):
        self.distance_calculator = DistanceCalculator(api_key)
        
        # Tarifs taxi Dakar (réalistes)
        self.base_price = 1000    # Prix de prise en charge
        self.price_per_km = 450   # Prix par km
        self.night_surcharge = 1.2  # Majoration nuit (20%)
        self.min_price = 1200     # Prix minimum
        
    def calculate_taxi_price(self, depart, arrivee):
        """Calcule le prix du taxi basé sur la distance réelle"""
        distance_km, duration_min = self.distance_calculator.calculate_real_distance(depart, arrivee)
        
        # Prix de base + prix par km
        base_calculation = self.base_price + (distance_km * self.price_per_km)
        
        # Arrondir à la centaine supérieure
        price = math.ceil(base_calculation / 100) * 100
        
        # Appliquer le prix minimum
        final_price = max(self.min_price, price)
        
        return final_price, distance_km, duration_min