import sys
import os
sys.path.insert(0, os.getcwd())

print("🧪 Test de déploiement...")

try:
    from models.transport_model import transport_model
    print("✅ Import réussi")
    
    # Test chemin CSV
    print(f"📁 Chemin CSV: {transport_model.data_path}")
    print(f"📄 CSV existe: {os.path.exists(transport_model.data_path)}")
    
    # Test recherche
    result = transport_model.find_routes('Parcelles Assainies', 'Le Plateau')
    print(f"🔍 Recherche: {result['success']}")
    
    print("🎉 Prêt pour le déploiement!")
    
except Exception as e:
    print(f"❌ Erreur: {e}")                                 