#!/usr/bin/env python
"""
Assign time slots to patients based on their pickup times
Updated to prioritize standard time slots from old web app
"""

import os
import django
from datetime import time

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, TimeSlot

def assign_timeslots():
    print("🔧 Assigning Time Slots to Patients")
    print("=" * 40)
    
    # Get all active time slots
    timeslots = TimeSlot.objects.filter(actief=True)
    print(f"📊 Actieve tijdblokken: {timeslots.count()}")
    
    # Get CSV patients
    patients = Patient.objects.filter(status='nieuw')
    print(f"📊 CSV patiënten: {patients.count()}")
    
    assigned_count = 0
    
    for patient in patients:
        print(f"\n🔍 Processing: {patient.naam}")
        print(f"   Ophaal tijd: {patient.ophaal_tijd}")
        
        if not patient.ophaal_tijd:
            print("   ❌ Geen ophaal tijd!")
            continue
        
        # Extract time from datetime
        pickup_time = patient.ophaal_tijd.time()
        print(f"   Pickup time: {pickup_time}")
        
        # Find matching halen time slot (nieuwe logica)
        halen_timeslot = None
        
        # First try to find a standard "Holen" time slot
        for ts in timeslots.filter(naam__startswith='Holen'):
            if ts.heen_start_tijd and pickup_time >= ts.heen_start_tijd:
                # Vind het juiste tijdblok (meest recente die past)
                if not halen_timeslot or ts.heen_start_tijd > halen_timeslot.heen_start_tijd:
                    halen_timeslot = ts
        
        # If no standard match, try other time slots
        if not halen_timeslot:
            for ts in timeslots:
                if ts.heen_start_tijd and pickup_time >= ts.heen_start_tijd:
                    # Vind het juiste tijdblok (meest recente die past)
                    if not halen_timeslot or ts.heen_start_tijd > halen_timeslot.heen_start_tijd:
                        halen_timeslot = ts
        
        if not halen_timeslot:
            print("   ❌ Geen halen tijdblok gevonden!")
            continue
        else:
            print(f"   ✅ Halen tijdblok: {halen_timeslot.naam} (start: {halen_timeslot.heen_start_tijd})")
        
        # Find matching brengen time slot (prioritize standard time slots)
        brengen_timeslot = None
        if patient.eind_behandel_tijd:
            end_time = patient.eind_behandel_tijd.time()
            print(f"   End time: {end_time}")
            
            # First try to find a standard "Bringen" time slot (nieuwe logica)
            for ts in timeslots.filter(naam__startswith='Bringen'):
                if ts.terug_start_tijd and end_time <= ts.terug_start_tijd:
                    # Vind het eerste beschikbare tijdblok na eind tijd
                    if not brengen_timeslot or ts.terug_start_tijd < brengen_timeslot.terug_start_tijd:
                        brengen_timeslot = ts
            
            # If no standard match, try other time slots
            if not brengen_timeslot:
                for ts in timeslots:
                    if ts.terug_start_tijd and end_time <= ts.terug_start_tijd:
                        # Vind het eerste beschikbare tijdblok na eind tijd
                        if not brengen_timeslot or ts.terug_start_tijd < brengen_timeslot.terug_start_tijd:
                            brengen_timeslot = ts
            
            if not brengen_timeslot:
                print("   ⚠️  Geen brengen tijdblok gevonden!")
            else:
                print(f"   ✅ Brengen tijdblok: {brengen_timeslot.naam} (start: {brengen_timeslot.terug_start_tijd})")
        else:
            brengen_timeslot = None
            print("   ⚠️  Geen eind behandeling tijd!")
        
        # Assign time slots
        patient.halen_tijdblok = halen_timeslot
        patient.bringen_tijdblok = brengen_timeslot
        patient.save()
        
        assigned_count += 1
        print(f"   ✅ Time slots assigned!")
    
    print(f"\n🎯 Result: {assigned_count}/{patients.count()} patiënten hebben tijdblokken toegewezen gekregen")
    
    # Verify assignments
    print("\n🔍 Verification:")
    patients_with_timeslots = Patient.objects.filter(status='nieuw', halen_tijdblok__isnull=False)
    print(f"   Patiënten met halen tijdblok: {patients_with_timeslots.count()}")
    
    for patient in patients_with_timeslots:
        print(f"   - {patient.naam}: {patient.halen_tijdblok.naam} -> {patient.bringen_tijdblok.naam if patient.bringen_tijdblok else 'None'}")

if __name__ == "__main__":
    assign_timeslots()
