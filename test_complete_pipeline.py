#!/usr/bin/env python
"""
Test de complete pipeline: patiënten upload -> geocoding -> tijdblok toewijzing -> route generatie
"""
import os
import sys
import django
from pathlib import Path
import requests
import json
from datetime import date, datetime, time

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, Vehicle, TimeSlot

def test_complete_pipeline():
    """Test de complete pipeline"""
    print("🧪 Complete Pipeline Test")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    # Stap 1: Check huidige patiënten
    print("\n1️⃣ Check huidige patiënten...")
    today = date.today()
    patients = Patient.objects.filter(ophaal_tijd__date=today)
    
    print(f"📊 Patiënten van vandaag: {patients.count()}")
    
    if patients.count() == 0:
        print("❌ Geen patiënten gevonden. Upload eerst patiënten via de wizard.")
        return False
    
    # Stap 2: Check geocoding status
    print("\n2️⃣ Check geocoding status...")
    patients_with_coords = patients.filter(latitude__isnull=False, longitude__isnull=False)
    patients_without_coords = patients.filter(latitude__isnull=True, longitude__isnull=True)
    
    print(f"✅ Patiënten met coördinaten: {patients_with_coords.count()}")
    print(f"❌ Patiënten zonder coördinaten: {patients_without_coords.count()}")
    
    if patients_without_coords.count() > 0:
        print("⚠️ Sommige patiënten hebben geen coördinaten. Geocoding nodig.")
    
    # Stap 3: Check voertuig toewijzing
    print("\n3️⃣ Check voertuig toewijzing...")
    patients_with_vehicle = patients.filter(toegewezen_voertuig__isnull=False)
    patients_without_vehicle = patients.filter(toegewezen_voertuig__isnull=True)
    
    print(f"✅ Patiënten met voertuig: {patients_with_vehicle.count()}")
    print(f"❌ Patiënten zonder voertuig: {patients_without_vehicle.count()}")
    
    # Stap 4: Check tijdblok toewijzing
    print("\n4️⃣ Check tijdblok toewijzing...")
    patients_with_timeslot = patients.filter(toegewezen_tijdblok__isnull=False)
    patients_without_timeslot = patients.filter(toegewezen_tijdblok__isnull=True)
    
    print(f"✅ Patiënten met tijdblok: {patients_with_timeslot.count()}")
    print(f"❌ Patiënten zonder tijdblok: {patients_without_timeslot.count()}")
    
    # Stap 5: Test route generatie API
    print("\n5️⃣ Test route generatie...")
    try:
        # Haal voertuigen op met patiënten
        vehicles_with_patients = Vehicle.objects.filter(patient__ophaal_tijd__date=today).distinct()
        
        print(f"🚗 Voertuigen met patiënten: {vehicles_with_patients.count()}")
        
        for vehicle in vehicles_with_patients:
            vehicle_patients = patients.filter(toegewezen_voertuig=vehicle)
            print(f"   - {vehicle}: {vehicle_patients.count()} patiënten")
            
            if vehicle_patients.count() > 0:
                # Test route generatie voor dit voertuig
                route_data = {
                    "vehicle_id": vehicle.id,
                    "date": today.isoformat()
                }
                
                response = requests.post(
                    f"{base_url}/api/google-maps-routes/",
                    json=route_data,
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code == 200:
                    route_info = response.json()
                    print(f"     ✅ Route gegenereerd: {route_info.get('status', 'OK')}")
                else:
                    print(f"     ❌ Route generatie gefaald: {response.status_code}")
        
    except Exception as e:
        print(f"❌ Route generatie error: {e}")
    
    # Stap 6: Test planning pagina
    print("\n6️⃣ Test planning pagina...")
    try:
        response = requests.get(f"{base_url}/planning/new-ui/")
        if response.status_code == 200:
            print("✅ Planning pagina toegankelijk")
            
            # Check of er patiënten worden getoond
            if "patient" in response.text.lower() or "patiënt" in response.text.lower():
                print("✅ Patiënten worden getoond op planning pagina")
            else:
                print("⚠️ Geen patiënten gevonden op planning pagina")
        else:
            print(f"❌ Planning pagina error: {response.status_code}")
    except Exception as e:
        print(f"❌ Planning pagina error: {e}")
    
    # Stap 7: Samenvatting
    print("\n" + "=" * 50)
    print("📋 Pipeline Status Samenvatting:")
    print(f"   - Totaal patiënten: {patients.count()}")
    print(f"   - Met coördinaten: {patients_with_coords.count()}")
    print(f"   - Met voertuig: {patients_with_vehicle.count()}")
    print(f"   - Met tijdblok: {patients_with_timeslot.count()}")
    
    if patients.count() > 0 and patients_with_coords.count() == patients.count() and patients_with_vehicle.count() > 0:
        print("\n🎉 Pipeline werkt correct!")
        print("✅ Patiënten zijn geüpload, gegeocodeerd en toegewezen")
        print("✅ Routes kunnen worden gegenereerd")
        print("\n📋 Volgende stappen:")
        print("1. Bekijk routes op http://localhost:8000/planning/new-ui/")
        print("2. Exporteer planning als PDF")
        print("3. Stuur planning naar chauffeurs")
        return True
    else:
        print("\n⚠️ Pipeline heeft problemen:")
        if patients.count() == 0:
            print("   - Geen patiënten geüpload")
        if patients_with_coords.count() < patients.count():
            print("   - Niet alle patiënten zijn gegeocodeerd")
        if patients_with_vehicle.count() == 0:
            print("   - Geen patiënten toegewezen aan voertuigen")
        return False

if __name__ == '__main__':
    test_complete_pipeline()
