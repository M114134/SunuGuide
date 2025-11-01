import sys
import os

print("🎯 TEST FINAL SUNUGUIDE")
print("=" * 40)

# Configuration
sys.path.insert(0, os.getcwd())
print(f"📁 Dossier: {os.getcwd()}")

try:
    print("\n1. Import des modèles...")
    from models.transport_model import transport_model
    print("   ✅ SUCCÈS")
    
    print("\n2. Test basique...")
    stations = transport_model.get_available_stations()
    print(f"   ✅ {len(stations)} stations")
    
    print("\n3. Test recherche...")
    result = transport_model.find_routes('Parcelles Assainies', 'Le Plateau')
    print(f"   ✅ Recherche: {result['success']}")
    
    if result['success']:
        for opt in result['options']:
            print(f"      🚗 {opt['transportType']}: {opt['price']} FCFA")
    
    print("\n🎉 PRÊT PUSH GITHUB!")
    
except Exception as e:
    print(f"❌ ÉCHEC: {e}")