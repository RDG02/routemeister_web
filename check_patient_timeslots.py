#!/usr/bin/env python
"""
Check patient time slot assignments
"""

import os
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, TimeSlot

def check_patient_timeslots():
    print("🔍 Check Patient Time Slots")
    print("=" * 40)
    
    # Get all active time slots
    timeslots = TimeSlot.objects.filter(actief=True)
    print(f"📊 Actieve tijdblokken: {timeslots.count()}")
    for ts in timeslots:
        print(f"   - {ts.naam}: {ts.heen_start_tijd}-{ts.heen_eind_tijd} (heen), {ts.terug_start_tijd}-{ts.terug_eind_tijd} (terug)")
    print()
    
    # Get CSV patients
    patients = Patient.objects.filter(status='nieuw')
    print(f"📊 CSV patiënten: {patients.count()}")
    
    patients_with_timeslots = 0
    for patient in patients:
        print(f"   - {patient.naam}:")
        print(f"     Ophaal tijd: {patient.ophaal_tijd}")
        print(f"     Eind behandeling: {patient.eind_behandel_tijd}")
        print(f"     Halen tijdblok: {patient.halen_tijdblok}")
        print(f"     Brengen tijdblok: {patient.bringen_tijdblok}")
        
        if patient.halen_tijdblok:
            patients_with_timeslots += 1
            print(f"     ✅ Heeft tijdblok")
        else:
            print(f"     ❌ Geen tijdblok!")
        print()
    
    print(f"📊 Patiënten met tijdblokken: {patients_with_timeslots}/{patients.count()}")
    
    if patients_with_timeslots == 0:
        print("⚠️  GEEN PATIËNTEN HEBBEN TIJDLOKKEN!")
        print("   Dit verklaart waarom de planning blijft hangen!")
        print("   We moeten eerst tijdblokken toewijzen.")

if __name__ == "__main__":
    check_patient_timeslots()
