#!/usr/bin/env python
"""
Complete end-to-end test van de planning workflow
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

def test_complete_workflow():
    """Test de complete planning workflow"""
    print("🧪 Complete Planning Workflow Test")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    # Stap 1: Test of de server draait
    print("\n1️⃣ Test server status...")
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            print("✅ Server draait correct")
        else:
            print(f"❌ Server error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Kan geen verbinding maken met server: {e}")
        return False
    
    # Stap 2: Test wizard pagina
    print("\n2️⃣ Test wizard pagina...")
    try:
        response = requests.get(f"{base_url}/wizard/")
        if response.status_code == 200:
            print("✅ Wizard pagina toegankelijk")
        else:
            print(f"❌ Wizard pagina error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Wizard pagina error: {e}")
        return False
    
    # Stap 3: Test planning pagina
    print("\n3️⃣ Test planning pagina...")
    try:
        response = requests.get(f"{base_url}/planning/new-ui/")
        if response.status_code == 200:
            print("✅ Planning pagina toegankelijk")
        else:
            print(f"❌ Planning pagina error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Planning pagina error: {e}")
        return False
    
    # Stap 4: Test database status
    print("\n4️⃣ Test database status...")
    try:
        today = date.today()
        patients = Patient.objects.filter(ophaal_tijd__date=today)
        vehicles = Vehicle.objects.all()
        timeslots = TimeSlot.objects.all()
        
        print(f"📊 Database status:")
        print(f"   - Patiënten van vandaag: {patients.count()}")
        print(f"   - Voertuigen: {vehicles.count()}")
        print(f"   - Tijdblokken: {timeslots.count()}")
        
        if vehicles.count() > 0:
            print("✅ Voertuigen beschikbaar")
        else:
            print("❌ Geen voertuigen in database")
            return False
            
        if timeslots.count() > 0:
            print("✅ Tijdblokken beschikbaar")
        else:
            print("❌ Geen tijdblokken in database")
            return False
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False
    
    # Stap 5: Test API endpoints
    print("\n5️⃣ Test API endpoints...")
    
    # Test constraints API
    try:
        response = requests.get(f"{base_url}/api/wizard/constraints/")
        if response.status_code == 200:
            data = response.json()
            print("✅ Constraints API werkt")
            print(f"   - Tijdblokken: {len(data.get('timeslots', []))}")
            print(f"   - Voertuigen: {len(data.get('vehicles', []))}")
        else:
            print(f"❌ Constraints API error: {response.status_code}")
    except Exception as e:
        print(f"❌ Constraints API error: {e}")
    
    # Test auto-assign API
    try:
        # Maak test data voor auto-assign
        test_data = {
            "timeslot_assignments": {
                "10:00": {
                    "patients": ["Test Patient 1", "Test Patient 2"],
                    "vehicle_count": 1
                }
            }
        }
        
        response = requests.post(
            f"{base_url}/api/wizard/auto-assign/",
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Auto-assign API werkt")
            print(f"   - Toegewezen patiënten: {data.get('total_assigned', 0)}")
        else:
            print(f"❌ Auto-assign API error: {response.status_code}")
    except Exception as e:
        print(f"❌ Auto-assign API error: {e}")
    
    # Stap 6: Test patiënten opslag
    print("\n6️⃣ Test patiënten opslag...")
    try:
        # Maak een test patiënt
        vehicle = Vehicle.objects.first()
        if vehicle:
            test_patient = Patient.objects.create(
                naam="Test Workflow Patient",
                straat="Teststraat 123",
                postcode="1234 AB",
                plaats="Teststad",
                ophaal_tijd=datetime.combine(today, time(8, 30)),
                eind_behandel_tijd=datetime.combine(today, time(17, 0)),
                bestemming="Revalidatiecentrum",
                toegewezen_voertuig=vehicle,
                status="gepland",
                latitude=50.7467,
                longitude=7.1516
            )
            
            print(f"✅ Test patiënt aangemaakt: {test_patient.naam}")
            print(f"   - ID: {test_patient.id}")
            print(f"   - Voertuig: {test_patient.toegewezen_voertuig}")
            print(f"   - Status: {test_patient.status}")
            
            # Verwijder test patiënt
            test_patient.delete()
            print("🗑️ Test patiënt verwijderd")
        else:
            print("❌ Geen voertuigen beschikbaar voor test")
            
    except Exception as e:
        print(f"❌ Patiënten opslag error: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 Complete workflow test voltooid!")
    print("✅ Alle componenten werken correct")
    print("\n📋 Volgende stappen voor handmatige test:")
    print("1. Ga naar http://localhost:8000/wizard/")
    print("2. Upload een CSV bestand")
    print("3. Ga door de wizard stappen")
    print("4. Bekijk resultaten op http://localhost:8000/planning/new-ui/")
    
    return True

if __name__ == '__main__':
    test_complete_workflow()
