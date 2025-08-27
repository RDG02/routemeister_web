#!/usr/bin/env python
"""
Check patiënt tijden en tijdblok toewijzing
"""
import os
import django
from datetime import datetime
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, TimeSlot
from django.db import models

def check_patient_times():
    print("🔍 Check Patiënt Tijden en Tijdblok Toewijzing")
    print("=" * 50)
    
    today = datetime.now().date()
    patients = Patient.objects.filter(ophaal_tijd__date=today)
    
    print(f"👥 Patiënten vandaag: {patients.count()}")
    print()
    
    # Check elke patiënt
    for i, patient in enumerate(patients, 1):
        print(f"📋 Patiënt {i}: {patient.naam}")
        print(f"   📅 Ophaal tijd: {patient.ophaal_tijd}")
        print(f"   📅 Eind tijd: {patient.eind_behandel_tijd}")
        print(f"   🚗 Halen tijdblok: {patient.halen_tijdblok.naam if patient.halen_tijdblok else 'Geen'}")
        print(f"   🏠 Brengen tijdblok: {patient.bringen_tijdblok.naam if patient.bringen_tijdblok else 'Geen'}")
        print()
    
    # Check beschikbare tijdblokken
    print("⏰ Beschikbare Tijdblokken:")
    print("-" * 30)
    
    timeslots = TimeSlot.objects.filter(actief=True).order_by('heen_start_tijd')
    for ts in timeslots:
        print(f"   {ts.naam}: {ts.heen_start_tijd}-{ts.heen_eind_tijd} / {ts.terug_start_tijd}-{ts.terug_eind_tijd}")
    
    print()
    
    # Test tijdblok toewijzing logica
    print("🔍 Test Tijdblok Toewijzing Logica:")
    print("-" * 30)
    
    for patient in patients[:3]:  # Test eerste 3 patiënten
        print(f"\n📍 {patient.naam}:")
        
        if patient.ophaal_tijd:
            pickup_time = patient.ophaal_tijd.time()
            print(f"   🚗 Ophaal tijd: {pickup_time}")
            
            # Zoek halen tijdblok
            halen_found = False
            for ts in timeslots:
                if ts.heen_start_tijd <= pickup_time <= ts.heen_eind_tijd:
                    print(f"   ✅ Halen tijdblok gevonden: {ts.naam}")
                    halen_found = True
                    break
            
            if not halen_found:
                print(f"   ❌ Geen halen tijdblok gevonden voor {pickup_time}")
        
        if patient.eind_behandel_tijd:
            end_time = patient.eind_behandel_tijd.time()
            print(f"   🏠 Eind tijd: {end_time}")
            
            # Zoek brengen tijdblok
            brengen_found = False
            for ts in timeslots:
                if end_time <= ts.terug_start_tijd:
                    print(f"   ✅ Brengen tijdblok gevonden: {ts.naam}")
                    brengen_found = True
                    break
            
            if not brengen_found:
                print(f"   ❌ Geen brengen tijdblok gevonden voor {end_time}")

def fix_timeslot_assignments():
    """
    Fix tijdblok toewijzingen
    """
    print(f"\n🔧 Fix Tijdblok Toewijzingen")
    print("-" * 30)
    
    today = datetime.now().date()
    patients = Patient.objects.filter(ophaal_tijd__date=today)
    timeslots = TimeSlot.objects.filter(actief=True).order_by('heen_start_tijd')
    
    fixed_count = 0
    
    for patient in patients:
        print(f"📍 {patient.naam}")
        
        # Skip als al correct toegewezen
        if patient.halen_tijdblok and patient.bringen_tijdblok:
            print(f"   ✅ Al correct toegewezen")
            continue
        
        # Zoek halen tijdblok
        halen_timeslot = None
        if patient.ophaal_tijd:
            pickup_time = patient.ophaal_tijd.time()
            
            for ts in timeslots:
                if ts.heen_start_tijd <= pickup_time <= ts.heen_eind_tijd:
                    halen_timeslot = ts
                    break
        
        # Zoek brengen tijdblok
        brengen_timeslot = None
        if patient.eind_behandel_tijd:
            end_time = patient.eind_behandel_tijd.time()
            
            for ts in timeslots:
                if end_time <= ts.terug_start_tijd:
                    brengen_timeslot = ts
                    break
        
        # Update patiënt
        if halen_timeslot:
            patient.halen_tijdblok = halen_timeslot
            print(f"   🚗 Halen: {halen_timeslot.naam}")
        
        if brengen_timeslot:
            patient.bringen_tijdblok = brengen_timeslot
            print(f"   🏠 Brengen: {brengen_timeslot.naam}")
        
        if halen_timeslot or brengen_timeslot:
            patient.save()
            fixed_count += 1
            print(f"   ✅ Toegewezen")
        else:
            print(f"   ❌ Geen tijdblok gevonden")
        
        print()
    
    print(f"📊 {fixed_count} patiënten gefixed")

if __name__ == "__main__":
    check_patient_times()
    
    response = input("\n🔧 Wil je tijdblok toewijzingen fixen? (j/n): ")
    if response.lower() in ['j', 'ja', 'y', 'yes']:
        fix_timeslot_assignments()
    
    print(f"\n✅ Check voltooid!")
