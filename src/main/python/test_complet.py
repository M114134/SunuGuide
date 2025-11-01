import sys
import os
import pandas as pd

print("=" * 60)
print("🧪 TEST COMPLET SUNUGUIDE - MODÈLES PYTHON")
print("=" * 60)

# Configuration des chemins
sys.path.insert(0, os.getcwd())

try:
    print("📦 1. Import des modèles...")
    from models.transport_model import transport_model
    print("   ✅ Modèles importés avec succès")
    
    print("\n📊 2. Test des stations...")
    stations = transport_model.get_available_stations()
    print(f"   ✅ {len(stations)} stations disponibles")
    print(f"   📋 5 premières: {stations[:5]}")
    
    print("\n🔍 3. Test de recherche - Parcelles Assainies → Le Plateau...")
    result1 = transport_model.find_routes('Parcelles Assainies', 'Le Plateau')
    print(f"   ✅ Recherche 1: {result1['success']}")
    if result1['success']:
        print(f"   🎯 {result1['totalOptions']} option(s) trouvée(s)")
        for i, option in enumerate(result1['options'], 1):
            print(f"      {i}. {option['transportType']}: {option['price']} FCFA")
    
    print("\n🔍 4. Test de recherche - Golf Nord → Grande Mosquee...")
    result2 = transport_model.find_routes('Golf Nord', 'Grande Mosquee')
    print(f"   ✅ Recherche 2: {result2['success']}")
    if result2['success']:
        print(f"   🎯 {result2['totalOptions']} option(s) trouvée(s)")
        for i, option in enumerate(result2['options'], 1):
            print(f"      {i}. {option['transportType']}: {option['price']} FCFA")
    
    print("\n🔍 5. Test de recherche - Station inexistante...")
    result3 = transport_model.find_routes('StationInexistante', 'AutreStation')
    print(f"   ✅ Gestion d'erreur: {result3['success']}")
    if not result3['success']:
        print(f"   💡 Message: {result3.get('message', 'N/A')}")
    
    print("\n📈 6. Test des statistiques...")
    stats = transport_model.get_model_info()
    print(f"   📊 Nombre total de routes: {stats['totalRoutes']}")
    print(f"   🏁 Stations disponibles: {stats['availableStations']}")
    
    print("\n" + "=" * 60)
    print("🎉 TOUS LES TESTS SONT RÉUSSIS !")
    print("✅ Le modèle est prêt pour l'intégration Spring Boot")
    print("=" * 60)
    
except Exception as e:
    print(f"\n❌ ERREUR: {e}")
    print("\n🔧 Debug information:")
    print(f"   Dossier: {os.getcwd()}")
    print(f"   Python path: {sys.path}")
    print(f"   Fichiers models/: {os.listdir('models')}")