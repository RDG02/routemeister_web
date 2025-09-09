#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import GoogleMapsConfig

def check_google_maps_config():
    print("🔍 Google Maps Configuratie Check")
    print("=" * 50)
    
    # Check if any config exists
    configs = GoogleMapsConfig.objects.all()
    print(f"📊 Aantal configuraties: {configs.count()}")
    
    if configs.count() == 0:
        print("❌ Geen Google Maps configuratie gevonden!")
        print("💡 Ga naar Django admin om een configuratie aan te maken.")
        return
    
    # Check each config
    for i, config in enumerate(configs):
        print(f"\n📋 Configuratie {i+1}:")
        print(f"   ID: {config.id}")
        print(f"   Enabled: {config.enabled}")
        print(f"   API Key: {'✅ Aanwezig' if config.api_key else '❌ Ontbreekt'}")
        if config.api_key:
            print(f"   API Key (eerste 10 chars): {config.api_key[:10]}...")
        print(f"   Created: {config.created_at}")
        print(f"   Updated: {config.updated_at}")
    
    # Check active config
    try:
        active_config = GoogleMapsConfig.get_active_config()
        if active_config:
            print(f"\n✅ Actieve configuratie: ID {active_config.id}")
            print(f"   Enabled: {active_config.enabled}")
            print(f"   API Key: {'✅ Aanwezig' if active_config.api_key else '❌ Ontbreekt'}")
        else:
            print("\n⚠️ Geen actieve configuratie gevonden")
    except Exception as e:
        print(f"\n❌ Fout bij ophalen actieve configuratie: {e}")
    
    print("\n" + "=" * 50)
    print("💡 Oplossingen:")
    print("1. Ga naar Django admin (/admin/)")
    print("2. Ga naar 'Planning' → 'Google Maps Configuraties'")
    print("3. Maak een nieuwe configuratie aan of bewerk bestaande")
    print("4. Zet 'Enabled' op True")
    print("5. Voeg een geldige Google Maps API key toe")

if __name__ == "__main__":
    check_google_maps_config()
