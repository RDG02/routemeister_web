#!/usr/bin/env python
"""
Test of patiënten correct worden opgeslagen na route optimalisatie
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, Vehicle, TimeSlot
from datetime import date, datetime, time

def test_patient_save():
    """Test of patiënten correct worden opgeslagen"""
    print("🧪 Test patiënt opslag...")
    
    today = date.today()
    print(f"📅 Vandaag: {today}")
    
    # Check patiënten van vandaag
    today_patients = Patient.objects.filter(ophaal_tijd__date=today)
    print(f"📊 Patiënten van vandaag: {today_patients.count()}")
    
    if today_patients.exists():
        print("\n📋 Patiënten van vandaag:")
        for patient in today_patients:
            vehicle_info = f" -> {patient.toegewezen_voertuig}" if patient.toegewezen_voertuig else " (geen voertuig)"
            print(f"   - {patient.naam} (ID: {patient.id}){vehicle_info}")
            print(f"     Ophaal: {patient.ophaal_tijd}")
            print(f"     Eind: {patient.eind_behandel_tijd}")
            print(f"     Status: {patient.status}")
            print(f"     Coördinaten: {patient.latitude}, {patient.longitude}")
            print()
    else:
        print("   ❌ Geen patiënten van vandaag gevonden")
        
        # Maak een test patiënt aan
        print("🔧 Maak test patiënt aan...")
        
        # Zoek een voertuig
        vehicle = Vehicle.objects.first()
        if vehicle:
            print(f"   Gebruik voertuig: {vehicle}")
            
            # Maak test patiënt
            test_patient = Patient.objects.create(
                naam="Test Patient",
                straat="Teststraat 1",
                postcode="1234 AB",
                plaats="Teststad",
                ophaal_tijd=datetime.combine(today, time(8, 30)),
                eind_behandel_tijd=datetime.combine(today, time(15, 30)),
                bestemming="Test Bestemming",
                toegewezen_voertuig=vehicle,
                status="gepland",
                latitude=50.7467,
                longitude=7.1516
            )
            
            print(f"   ✅ Test patiënt aangemaakt: {test_patient.naam}")
            
            # Check opnieuw
            today_patients = Patient.objects.filter(ophaal_tijd__date=today)
            print(f"📊 Patiënten van vandaag na test: {today_patients.count()}")
        else:
            print("   ❌ Geen voertuigen gevonden")
    
    # Check voertuigen met patiënten
    vehicles_with_patients = Vehicle.objects.filter(patient__ophaal_tijd__date=today).distinct()
    print(f"🚗 Voertuigen met patiënten: {vehicles_with_patients.count()}")
    
    if vehicles_with_patients.exists():
        print("\n🚗 Voertuigen met patiënten:")
        for vehicle in vehicles_with_patients:
            assigned_patients = Patient.objects.filter(toegewezen_voertuig=vehicle, ophaal_tijd__date=today)
            print(f"   - {vehicle} ({vehicle.referentie or vehicle.kenteken})")
            print(f"     Toegewezen patiënten: {assigned_patients.count()}")
            for patient in assigned_patients:
                print(f"       * {patient.naam}")
            print()
    
    return True

if __name__ == '__main__':
    test_patient_save()
