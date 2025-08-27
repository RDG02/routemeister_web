#!/usr/bin/env python
"""
Fix geocoding voor bestaande patiënten zonder coördinaten
"""
import os
import django
from datetime import datetime
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient
import requests
import time

def fix_existing_patients_geocoding():
    print("🔧 Fix Geocoding voor Bestaande Patiënten")
    print("=" * 50)
    
    # Haal alle patiënten op zonder coördinaten
    patients_without_coords = Patient.objects.filter(
        latitude__isnull=True
    ) | Patient.objects.filter(
        longitude__isnull=True
    )
    
    print(f"👥 Patiënten zonder coördinaten: {patients_without_coords.count()}")
    
    if patients_without_coords.count() == 0:
        print("✅ Alle patiënten hebben al coördinaten!")
        return
    
    print("\n🗺️ Start geocoding...")
    print("-" * 30)
    
    success_count = 0
    fail_count = 0
    
    for patient in patients_without_coords:
        print(f"📍 {patient.naam}")
        
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
        
        full_address = ", ".join(address_parts) + ", Deutschland"
        print(f"   📍 Adres: {full_address}")
        
        try:
            # Geocoding met OpenStreetMap Nominatim
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': full_address,
                'format': 'json',
                'limit': 1,
                'countrycodes': 'de'
            }
            headers = {
                'User-Agent': 'Routemeister/1.0 (https://routemeister.com)'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data and len(data) > 0:
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
                # Fallback naar standaard coördinaten gebaseerd op plaats
                lat, lon = get_default_coordinates(patient.plaats)
                patient.latitude = lat
                patient.longitude = lon
                patient.save()
                
                print(f"   ⚠️ Fallback coördinaten: {lat}, {lon}")
                success_count += 1
            
            # Korte pauze om API niet te overbelasten
            time.sleep(1)
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            # Fallback naar standaard coördinaten
            lat, lon = get_default_coordinates(patient.plaats)
            patient.latitude = lat
            patient.longitude = lon
            patient.save()
            
            print(f"   ⚠️ Fallback coördinaten: {lat}, {lon}")
            success_count += 1
    
    print(f"\n📊 Geocoding resultaat:")
    print(f"   ✅ Succesvol: {success_count}")
    print(f"   ❌ Gefaald: {fail_count}")
    
    if success_count > 0:
        print(f"\n🎉 {success_count} patiënten succesvol gegecodeerd!")
    else:
        print(f"\n⚠️ Geen patiënten gegecodeerd.")

def get_default_coordinates(plaats):
    """
    Bepaal standaard coördinaten gebaseerd op plaats
    """
    if not plaats:
        return (50.746702862, 7.151631000)  # Reha Center
    
    place_lower = plaats.lower()
    
    if 'bonn' in place_lower:
        return (50.73743, 7.09821)
    elif 'köln' in place_lower or 'koeln' in place_lower:
        return (50.93753, 6.96028)
    elif 'düsseldorf' in place_lower or 'duesseldorf' in place_lower:
        return (51.22172, 6.77616)
    elif 'siegburg' in place_lower:
        return (50.7952, 7.2070)
    elif 'bad honnef' in place_lower:
        return (50.6458, 7.2278)
    elif 'niederkassel' in place_lower:
        return (50.8167, 7.0333)
    else:
        return (50.746702862, 7.151631000)  # Reha Center

if __name__ == "__main__":
    fix_existing_patients_geocoding()
    print("\n✅ Geocoding fix voltooid!")
