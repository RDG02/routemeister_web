#!/usr/bin/env python
"""
Script om tijdblokken toe te wijzen aan bestaande patiënten
"""
import os
import sys
import django
from pathlib import Path
from datetime import date, datetime, time

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, Vehicle, TimeSlot

def assign_timeslots_to_patients():
    """Wijs tijdblokken toe aan patiënten die nog geen tijdblok hebben"""
    print("⏰ Tijdblok toewijzing aan patiënten")
    print("=" * 40)
    
    today = date.today()
    
    # Haal patiënten op zonder tijdblok
    patients_without_timeslot = Patient.objects.filter(
        ophaal_tijd__date=today,
        toegewezen_tijdblok__isnull=True
    )
    
    print(f"📊 Patiënten zonder tijdblok: {patients_without_timeslot.count()}")
    
    if patients_without_timeslot.count() == 0:
        print("✅ Alle patiënten hebben al een tijdblok")
        return True
    
    # Haal beschikbare tijdblokken op
    timeslots = TimeSlot.objects.all().order_by('aankomst_tijd')
    print(f"⏰ Beschikbare tijdblokken: {timeslots.count()}")
    
    if timeslots.count() == 0:
        print("❌ Geen tijdblokken beschikbaar")
        return False
    
    # Groepeer patiënten per voertuig
    vehicles_with_patients = {}
    for patient in patients_without_timeslot:
        if patient.toegewezen_voertuig:
            vehicle = patient.toegewezen_voertuig
            if vehicle not in vehicles_with_patients:
                vehicles_with_patients[vehicle] = []
            vehicles_with_patients[vehicle].append(patient)
    
    print(f"🚗 Voertuigen met patiënten: {len(vehicles_with_patients)}")
    
    # Wijs tijdblokken toe per voertuig
    assigned_count = 0
    
    for vehicle, vehicle_patients in vehicles_with_patients.items():
        print(f"\n🚗 {vehicle}: {len(vehicle_patients)} patiënten")
        
        # Sorteer patiënten op ophaal tijd
        vehicle_patients.sort(key=lambda p: p.ophaal_tijd)
        
        # Wijs tijdblokken toe
        for i, patient in enumerate(vehicle_patients):
            # Kies een tijdblok gebaseerd op ophaal tijd
            patient_time = patient.ophaal_tijd.time()
            
            # Zoek het beste tijdblok (gebruik aankomst_tijd)
            best_timeslot = None
            for timeslot in timeslots:
                # Voor halen: patiënt tijd moet rond aankomst_tijd zijn
                if timeslot.tijdblok_type == 'halen':
                    # Bepaal een redelijke tijd range (30 minuten voor en na)
                    from datetime import timedelta
                    start_range = (datetime.combine(date.today(), timeslot.aankomst_tijd) - timedelta(minutes=30)).time()
                    end_range = (datetime.combine(date.today(), timeslot.aankomst_tijd) + timedelta(minutes=30)).time()
                    
                    if start_range <= patient_time <= end_range:
                        best_timeslot = timeslot
                        break
            
            # Als geen exacte match, neem het eerste beschikbare tijdblok
            if not best_timeslot:
                best_timeslot = timeslots[i % timeslots.count()]
            
            # Wijs tijdblok toe
            patient.toegewezen_tijdblok = best_timeslot
            patient.save()
            
            print(f"   ✅ {patient.naam} -> {best_timeslot} ({patient_time})")
            assigned_count += 1
    
    print(f"\n🎉 {assigned_count} patiënten hebben nu een tijdblok")
    
    # Check resultaat
    patients_with_timeslot = Patient.objects.filter(
        ophaal_tijd__date=today,
        toegewezen_tijdblok__isnull=False
    )
    
    print(f"📊 Patiënten met tijdblok: {patients_with_timeslot.count()}")
    
    return True

if __name__ == '__main__':
    assign_timeslots_to_patients()
