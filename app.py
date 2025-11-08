from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
import math
import requests

# ----------------------------
# Définition des modèles
# ----------------------------

ORS_API_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjQ4YzZhZDMzMTcwOTRmOGFiZmQ3MzI5ZjgxYzcxOGIyIiwiaCI6Im11cm11cjY0In0="

# Pydantic model pour les requêtes
class RouteRequest(BaseModel):
    depart: str
    arrivee: str
    preference: str = "équilibré"

# ----------------------------
# Classes internes
# ----------------------------

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

class DistanceCalculator:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.openrouteservice.org/v2/directions/driving-car"
        self.headers = {'Authorization': api_key, 'Content-Type': 'application/json'}
        self.station_coordinates = {
            'parcelles assainies': (14.7677, -17.3980),
            'le plateau': (14.6770, -17.4370),
            'dakar': (14.6928, -17.4467),
            # ... ajoute toutes les stations ici ...
        }

    def get_station_coordinates(self, station_name):
        station_lower = station_name.lower()
        for station, coords in self.station_coordinates.items():
            if station in station_lower or station_lower in station:
                return coords
        return (14.6928, -17.4467)  # fallback

    def calculate_real_distance(self, depart, arrivee):
        try:
            dep_coords = self.get_station_coordinates(depart)
            arr_coords = self.get_station_coordinates(arrivee)
            body = {"coordinates": [[dep_coords[1], dep_coords[0]], [arr_coords[1], arr_coords[0]]],
                    "instructions": False, "preference": "recommended"}
            response = requests.post(self.base_url, json=body, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                distance_km = data['routes'][0]['summary']['distance'] / 1000
                duration_min = data['routes'][0]['summary']['duration'] / 60
                return round(distance_km,1), round(duration_min,1)
            else:
                return self.estimate_distance_fallback(depart, arrivee)
        except:
            return self.estimate_distance_fallback(depart, arrivee)

    def estimate_distance_fallback(self, depart, arrivee):
        return 10.0, 20  # fallback simple

class TaxiPriceCalculator:
    def __init__(self, api_key):
        self.distance_calculator = DistanceCalculator(api_key)
        self.base_price = 1000
        self.price_per_km = 450
        self.min_price = 1200

    def calculate_taxi_price(self, depart, arrivee):
        distance_km, duration_min = self.distance_calculator.calculate_real_distance(depart, arrivee)
        price = max(self.min_price, math.ceil((self.base_price + distance_km*self.price_per_km)/100)*100)
        return price, distance_km, duration_min

class ScoringModel:
    def __init__(self, df, api_key):
        self.df = df
        self.avg_prix = df['prix'].mean()
        self.avg_rapidite = df['rapidite'].mean()
        self.avg_confort = df['confort'].mean()
        self.taxi_calculator = TaxiPriceCalculator(api_key)

    def calculate_score(self, option, preference='équilibré'):
        if preference == 'économique':
            weights = {'prix': 0.5, 'rapidite':0.3, 'confort':0.2}
        elif preference == 'rapide':
            weights = {'prix':0.3, 'rapidite':0.5, 'confort':0.2}
        elif preference == 'confortable':
            weights = {'prix':0.3, 'rapidite':0.2, 'confort':0.5}
        else:
            weights = {'prix':0.4, 'rapidite':0.4, 'confort':0.2}
        prix_norm = max(0, 1 - (option['prix']/(self.avg_prix*3)))
        rapidite_norm = option['rapidite']/10
        confort_norm = option['confort']/10
        base_score = prix_norm*weights['prix'] + rapidite_norm*weights['rapidite'] + confort_norm*weights['confort']
        transport_bonus = {'BRT':1.1,'TAXI':1.0,'TER':0.9,'DEM-DIKK':1.2}
        for key, bonus in transport_bonus.items():
            if key in option['type transport']:
                base_score *= bonus
                break
        return min(10, round(base_score*10,2))

class SearchEngine:
    def __init__(self, df, scoring_model):
        self.df = df
        self.scoring_model = scoring_model
        self.all_stations = list(set(df['depart'].unique()) | set(df['arrivee'].unique()))

    def find_similar_station(self, station_input):
        if not station_input: return None
        station_input = station_input.lower().strip()
        for s in self.all_stations:
            if s.lower() == station_input:
                return s
        for s in self.all_stations:
            if station_input in s.lower():
                return s
        return None

    def find_routes(self, depart_input, arrivee_input, preference='équilibré'):
        depart_corrected = self.find_similar_station(depart_input)
        arrivee_corrected = self.find_similar_station(arrivee_input)
        if not depart_corrected or not arrivee_corrected:
            return None
        mask = (self.df['depart'].str.lower()==depart_corrected.lower()) & (self.df['arrivee'].str.lower()==arrivee_corrected.lower())
        options = self.df[mask].copy()
        if not options.empty:
            options['score'] = options.apply(lambda x: self.scoring_model.calculate_score(x, preference), axis=1)
            return options.nlargest(3,'score').to_dict(orient='records')
        else:
            taxi_price, distance_km, duration_min = self.scoring_model.taxi_calculator.calculate_taxi_price(depart_corrected, arrivee_corrected)
            taxi_option = {
                'type transport':'TAXI 🚕',
                'depart': depart_corrected,
                'arrivee': arrivee_corrected,
                'prix': taxi_price,
                'rapidite':7.5,
                'confort':9.0,
                'distance_km':distance_km,
                'duree_min':duration_min,
                'score': self.scoring_model.calculate_score({'type transport':'TAXI','prix':taxi_price,'rapidite':7.5,'confort':9.0}, preference)
            }
            return [taxi_option]

# ----------------------------
# Chargement CSV et modèles
# ----------------------------

try:
    df = pd.read_csv("sunuguide_clean_standard.csv")
except Exception as e:
    print(f"Erreur CSV: {e}")
    df = pd.DataFrame()

preprocessor = DataPreprocessor(df)
df_clean = preprocessor.clean_data().create_features().get_data()

scoring_model = ScoringModel(df_clean, ORS_API_KEY)
search_engine = SearchEngine(df_clean, scoring_model)

# ----------------------------
# FastAPI app
# ----------------------------

app = FastAPI(title="SunuGuide API", description="API pour assistant transport Dakar", version="1.0")

@app.get("/")
def root():
    return {"message": "API SunuGuide en ligne"}

@app.post("/search_routes")
def search_routes(request: RouteRequest):
    results = search_engine.find_routes(request.depart, request.arrivee, request.preference.lower())
    if not results:
        raise HTTPException(status_code=404, detail="Aucun trajet trouvé")
    return {"results": results}
