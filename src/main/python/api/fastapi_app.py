"""
API FastAPI pour l'intégration avec Spring Boot
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

from ..models.transport_model import transport_model

app = FastAPI(
    title="SunuGuide Python API",
    description="API Python pour les modèles de transport",
    version="1.0.0"
)

# CORS pour permettre les appels depuis Spring Boot
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/python/health")
async def health_check():
    return {"status": "healthy", "service": "python-models"}

@app.get("/python/stations")
async def get_stations():
    """Retourne les stations disponibles"""
    try:
        stations = transport_model.get_available_stations()
        return {"stations": stations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/python/search/{depart}/{arrivee}")
async def search_routes(depart: str, arrivee: str, preference: str = "balanced"):
    """Recherche d'itinéraires"""
    try:
        result = transport_model.find_routes(depart, arrivee, preference)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/python/model-info")
async def get_model_info():
    """Informations sur le modèle"""
    try:
        return transport_model.get_model_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)