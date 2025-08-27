#!/usr/bin/env python
"""
Check en fix geocoding status van patiënten
"""
import os
import django
from datetime import datetime
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, Location
import requests
import time

def check_geocoding_status():
    print("🗺️ Geocoding Status Check")
    print("=" * 40)
    
    # Haal patiënten op van vandaag
    today = datetime.now().date()
    patients = Patient.objects.filter(ophaal_tijd__date=today)
    
    print(f"📅 Datum: {today}")
    print(f"👥 Totaal patiënten: {patients.count()}")
    print()
    
    # Check coördinaten status
    with_coords = patients.filter(latitude__isnull=False, longitude__isnull=False)
    without_coords = patients.filter(latitude__isnull=True) | patients.filter(longitude__isnull=True)
    
    print(f"✅ Met coördinaten: {with_coords.count()}")
    print(f"❌ Zonder coördinaten: {without_coords.count()}")
    print()
    
    if without_coords.count() > 0:
        print("📋 Patiënten zonder coördinaten:")
        for patient in without_coords:
            address = f"{patient.straat or 'Geen straat'}, {patient.postcode or 'Geen postcode'}, {patient.plaats or 'Geen plaats'}"
            print(f"   - {patient.naam}: {address}")
        print()
        
        # Vraag om geocoding uit te voeren
        response = input("🔧 Wil je geocoding uitvoeren voor deze patiënten? (j/n): ")
        if response.lower() in ['j', 'ja', 'y', 'yes']:
            perform_geocoding(without_coords)
    else:
        print("✅ Alle patiënten hebben coördinaten!")

def perform_geocoding(patients):
    print("\n🗺️ Geocoding uitvoeren...")
    print("=" * 30)
    
    success_count = 0
    fail_count = 0
    
    for patient in patients:
        print(f"📍 Geocoding: {patient.naam}")
        
        # Bouw adres samen
        address_parts = []
        if patient.straat:
            address_parts.append(patient.straat)
        if patient.postcode:
            address_parts.append(patient.postcode)
        if patient.plaats:
            address_parts.append(patient.plaats)
        
        if not address_parts:
            print(f"   ❌ Geen adres beschikbaar")
            fail_count += 1
            continue
        
        address = ", ".join(address_parts)
        print(f"   📍 Adres: {address}")
        
        try:
            # Geocoding met OpenStreetMap Nominatim
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': address,
                'format': 'json',
                'limit': 1,
                'countrycodes': 'de'  # Alleen Duitsland
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data:
                # Eerste resultaat gebruiken
                result = data[0]
                lat = float(result['lat'])
                lon = float(result['lon'])
                
                # Update patiënt
                patient.latitude = lat
                patient.longitude = lon
                patient.save()
                
                print(f"   ✅ Coördinaten: {lat}, {lon}")
                success_count += 1
                
            else:
                print(f"   ❌ Geen resultaat gevonden")
                fail_count += 1
            
            # Korte pauze om API niet te overbelasten
            time.sleep(1)
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            fail_count += 1
    
    print(f"\n📊 Geocoding resultaat:")
    print(f"   ✅ Succesvol: {success_count}")
    print(f"   ❌ Gefaald: {fail_count}")
    
    if success_count > 0:
        print(f"\n🎉 {success_count} patiënten succesvol gegecodeerd!")
    else:
        print(f"\n⚠️ Geen patiënten gegecodeerd. Controleer de adressen.")

def fix_missing_coordinates():
    """
    Fix patiënten zonder coördinaten met standaard Bonn coördinaten
    """
    print("\n🔧 Fix ontbrekende coördinaten met standaard locaties...")
    
    # Standaard coördinaten voor Bonn gebied
    default_coords = {
        'Bonn': (50.73743, 7.09821),
        'Köln': (50.93753, 6.96028),
        'Düsseldorf': (51.22172, 6.77616),
        'Default': (50.746702862, 7.151631000)  # Reha Center
    }
    
    patients = Patient.objects.filter(latitude__isnull=True) | Patient.objects.filter(longitude__isnull=True)
    
    for patient in patients:
        # Bepaal standaard coördinaten gebaseerd op plaats
        if patient.plaats:
            place_lower = patient.plaats.lower()
            if 'bonn' in place_lower:
                lat, lon = default_coords['Bonn']
            elif 'köln' in place_lower or 'koeln' in place_lower:
                lat, lon = default_coords['Köln']
            elif 'düsseldorf' in place_lower or 'duesseldorf' in place_lower:
                lat, lon = default_coords['Düsseldorf']
            else:
                lat, lon = default_coords['Default']
        else:
            lat, lon = default_coords['Default']
        
        patient.latitude = lat
        patient.longitude = lon
        patient.save()
        
        print(f"   ✅ {patient.naam}: {lat}, {lon}")

if __name__ == "__main__":
    check_geocoding_status()
    
    # Vraag om ontbrekende coördinaten te fixen
    response = input("\n🔧 Wil je ontbrekende coördinaten fixen met standaard locaties? (j/n): ")
    if response.lower() in ['j', 'ja', 'y', 'yes']:
        fix_missing_coordinates()
    
    print("\n✅ Geocoding check voltooid!")
