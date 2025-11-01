"""
Modèle principal de recommandation de transport SunuGuide
Adapté pour l'intégration Spring Boot
"""

import pandas as pd
import numpy as np
import math
import requests
import os
from typing import Dict, List, Optional, Tuple
import logging

# ✅ AJOUTEZ CETTE LIGNE :
from .price_calculator import TaxiPriceCalculator, DistanceCalculator

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Clé API intégrée
ORS_API_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjQ4YzZhZDMzMTcwOTRmOGFiZmQ3MzI5ZjgxYzcxOGIyIiwiaCI6Im11cm11cjY0In0="

class DataPreprocessor:
    def __init__(self, df):
        self.df = df.copy()
    
    def clean_data(self):
        self.df['rapidite'] = self.df['rapidite'].fillna(5.0)
        self.df['confort'] = self.df['confort'].fillna(5.0)
        return self
    
    def create_features(self):
        self.df['categorie_prix'] = pd.cut(self.df['prix'], 
                                         bins=[0, 500, 2000, 50000],
                                         labels=['Économique', 'Moyen', 'Cher'])
        self.df['score_basique'] = (self.df['rapidite'] + self.df['confort']) / 2
        return self
    
    def get_data(self):
        return self.df

class ScoringModel:
    def __init__(self, df, api_key):
        self.df = df
        self.avg_prix = df['prix'].mean()
        self.avg_rapidite = df['rapidite'].mean()
        self.avg_confort = df['confort'].mean()
        self.taxi_calculator = TaxiPriceCalculator(api_key)
    
    def calculate_score(self, option, preference='équilibré'):
        """Score simple mais équilibré"""
        
        # Définir les poids ÉQUILIBRÉS
        if preference == 'économique':
            weights = {'prix': 0.5, 'rapidite': 0.3, 'confort': 0.2}
        elif preference == 'rapide':
            weights = {'prix': 0.3, 'rapidite': 0.5, 'confort': 0.2}
        elif preference == 'confortable':
            weights = {'prix': 0.3, 'rapidite': 0.2, 'confort': 0.5}
        else:  # équilibré
            weights = {'prix': 0.4, 'rapidite': 0.4, 'confort': 0.2}
        
        # Normalisation
        prix_norm = max(0, 1 - (option['prix'] / (self.avg_prix * 3)))
        rapidite_norm = option['rapidite'] / 10
        confort_norm = option['confort'] / 10
        
        # Score de base
        base_score = (
            prix_norm * weights['prix'] + 
            rapidite_norm * weights['rapidite'] + 
            confort_norm * weights['confort']
        )
        
        # Facteur d'équilibrage par type de transport
        transport_bonus = {
            'BRT': 1.1,
            'TAXI': 1.0,
            'TER': 0.9,
            'DEM-DIKK': 1.2
        }
        
        # Appliquer le bonus selon le type
        transport_type = option['type transport']
        for key, bonus in transport_bonus.items():
            if key in transport_type:
                base_score *= bonus
                break
        
        return min(10, round(base_score * 10, 2))

class SearchEngine:
    def __init__(self, df, scoring_model):
        self.df = df
        self.scoring_model = scoring_model
        self.all_stations = list(set(df['depart'].unique()) | set(df['arrivee'].unique()))
    
    def find_similar_station(self, station_input):
        """Trouve la station la plus similaire"""
        if not station_input:
            return None
            
        station_input = str(station_input).lower().strip()
        
        # Correspondance exacte
        exact_matches = [s for s in self.all_stations if s.lower() == station_input]
        if exact_matches:
            return exact_matches[0]
        
        # Correspondance partielle
        for station in self.all_stations:
            if station_input in station.lower():
                return station
        
        return None
    
    def find_routes(self, depart_input, arrivee_input, preference='équilibré'):
        """Trouve les routes avec recherche flexible"""
        
        depart_corrected = self.find_similar_station(depart_input)
        arrivee_corrected = self.find_similar_station(arrivee_input)
        
        corrections = {}
        if depart_corrected and depart_corrected.lower() != depart_input.lower():
            corrections['depart'] = depart_corrected
        if arrivee_corrected and arrivee_corrected.lower() != arrivee_input.lower():
            corrections['arrivee'] = arrivee_corrected
        
        if not depart_corrected or not arrivee_corrected:
            return None, corrections
        
        # Recherche directe dans le dataset
        mask = (self.df['depart'].str.lower() == depart_corrected.lower()) & \
               (self.df['arrivee'].str.lower() == arrivee_corrected.lower())
        
        options = self.df[mask].copy()
        
        if not options.empty:
            # Calcul des scores pour les options existantes
            options['score'] = options.apply(
                lambda x: self.scoring_model.calculate_score(x, preference), 
                axis=1
            )
            top_3 = options.nlargest(3, 'score')
            return top_3, corrections
        else:
            # Si pas de trajet direct, suggérer le taxi avec prix réel
            return self._suggest_taxi(depart_corrected, arrivee_corrected, preference, corrections)
    
    def _suggest_taxi(self, depart, arrivee, preference, corrections):
        """Suggère une option taxi avec prix calculé en temps réel"""
        taxi_price, distance_km, duration_min = self.scoring_model.taxi_calculator.calculate_taxi_price(depart, arrivee)
        
        # Créer une option taxi réaliste
        taxi_option = pd.DataFrame([{
            'type transport': 'TAXI',
            'depart': depart,
            'arrivee': arrivee,
            'prix': taxi_price,
            'rapidite': 7.5,  # Taxi généralement rapide
            'confort': 9.0,   # Confort élevé
            'distance_km': distance_km,
            'duree_min': duration_min,
            'is_taxi_suggestion': True
        }])
        
        # Calculer le score
        taxi_option['score'] = taxi_option.apply(
            lambda x: self.scoring_model.calculate_score(x, preference), 
            axis=1
        )
        
        corrections['taxi_suggestion'] = True
        return taxi_option, corrections

    def get_available_stations(self) -> List[str]:
        """Retourne la liste des stations disponibles"""
        return sorted(self.all_stations)
    
    def get_transport_stats(self) -> Dict:
        """Retourne les statistiques du réseau"""
        return {
            'total_routes': len(self.df),
            'transport_types': self.df['type transport'].value_counts().to_dict(),
            'price_range': {
                'min': int(self.df['prix'].min()),
                'max': int(self.df['prix'].max()),
                'avg': int(self.df['prix'].mean())
            }
        }

class SunuGuideTransportModel:
    """Classe principale pour l'intégration Spring Boot"""
    
    def __init__(self, data_path: str = r"C:\Users\USER\Desktop\ESPOIRE\SunuGuide\data\sunuguide_clean_standard.csv"):
        self.data_path = data_path
        self.search_engine = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialise le modèle avec les données"""
        try:
            # Utiliser le chemin relatif pour l'intégration
            df = pd.read_csv(self.data_path)
            preprocessor = DataPreprocessor(df)
            preprocessor.clean_data().create_features()
            processed_df = preprocessor.get_data()
            
            scoring_model = ScoringModel(processed_df, ORS_API_KEY)
            self.search_engine = SearchEngine(processed_df, scoring_model)
            logger.info("✅ SunuGuide Transport Model initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Model initialization failed: {e}")
            raise
    
    def find_routes(self, depart: str, arrivee: str, preference: str = "balanced") -> Dict:
        """
        Recherche des itinéraires - Interface pour Spring Boot
        
        Returns:
            Dict: Résultats formatés pour l'API Java
        """
        try:
            # Adapter les préférences pour le modèle existant
            pref_mapping = {
                "balanced": "équilibré",
                "economic": "économique", 
                "fast": "rapide",
                "comfort": "confortable"
            }
            model_preference = pref_mapping.get(preference, "équilibré")
            
            recommendations, corrections = self.search_engine.find_routes(
                depart, arrivee, model_preference
            )
            
            if recommendations is None or len(recommendations) == 0:
                return {
                    "success": False,
                    "message": "Aucun trajet trouvé",
                    "taxiSuggestion": self._suggest_taxi(depart, arrivee)
                }
            
            # Formater les résultats pour l'API Spring Boot
            options = []
            for _, option in recommendations.iterrows():
                options.append({
                    "transportType": option['type transport'],
                    "departure": option['depart'],
                    "arrival": option['arrivee'],
                    "price": int(option['prix']),
                    "speed": float(option['rapidite']),
                    "comfort": float(option['confort']),
                    "score": float(option['score']),
                    "distanceKm": float(option.get('distance_km', 0)),
                    "durationMin": float(option.get('duree_min', 0)),
                    "isTaxiSuggestion": option.get('is_taxi_suggestion', False)
                })
            
            return {
                "success": True,
                "departure": depart,
                "arrival": arrivee,
                "corrections": corrections,
                "options": options,
                "totalOptions": len(options)
            }
            
        except Exception as e:
            logger.error(f"Route search error: {e}")
            return {
                "success": False,
                "message": f"Erreur de recherche: {str(e)}"
            }
    
    def _suggest_taxi(self, depart: str, arrivee: str) -> Dict:
        """Suggère un taxi quand aucun trajet n'est trouvé"""
        try:
            taxi_price, distance_km, duration_min = self.search_engine.scoring_model.taxi_calculator.calculate_taxi_price(depart, arrivee)
            
            return {
                "transportType": "TAXI",
                "departure": depart,
                "arrival": arrivee,
                "price": taxi_price,
                "distanceKm": distance_km,
                "durationMin": duration_min,
                "speed": 7.5,
                "comfort": 9.0,
                "isTaxiSuggestion": True
            }
        except Exception as e:
            logger.error(f"Taxi suggestion error: {e}")
            return {}
    
    def get_available_stations(self) -> List[str]:
        """Liste des stations disponibles"""
        return self.search_engine.get_available_stations()
    
    def get_model_info(self) -> Dict:
        """Informations sur le modèle"""
        return {
            "name": "SunuGuide Transport Model",
            "version": "1.0.0",
            "author": "Votre Nom",
            "totalRoutes": len(self.search_engine.df),
            "availableStations": len(self.get_available_stations())
        }

# Instance globale pour l'API
transport_model = SunuGuideTransportModel()