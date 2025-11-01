#!/bin/bash

echo "🚀 Starting SunuGuide Python Model Service..."

# Se positionner dans le bon dossier
cd "$(dirname "$0")"

# Installer les dépendances si nécessaire
pip install -r requirements.txt

# Démarrer l'API FastAPI
echo "📡 Starting FastAPI on port 5000..."
python api/fastapi_app.py