#!/usr/bin/env python
"""
Fix patient pickup times by subtracting 1 hour from appointment times
Kolom 18 = Eerste afspraak tijd, ophaal tijd = afspraak tijd - 1 uur
"""

import os
import django
from datetime import datetime, timedelta

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient

def fix_patient_times():
    print("🔧 Fixing Patient Pickup Times")
    print("=" * 40)
    print("Kolom 18 = Eerste afspraak tijd op Reha Center")
    print("Ophaal tijd = Afspraak tijd - 1 uur")
    print()
    
    # Get all patients
    patients = Patient.objects.all()
    
    fixed_count = 0
    for patient in patients:
        if patient.ophaal_tijd:
            # Get appointment time (current ophaal_tijd is actually appointment time)
            appointment_time = patient.ophaal_tijd
            
            # Calculate pickup time (1 hour earlier)
            pickup_time = appointment_time - timedelta(hours=1)
            
            # Update patient
            old_time = patient.ophaal_tijd.strftime("%H:%M")
            patient.ophaal_tijd = pickup_time
            patient.save()
            
            new_time = patient.ophaal_tijd.strftime("%H:%M")
            print(f"✅ {patient.naam}: {old_time} → {new_time} (afspraak: {appointment_time.strftime('%H:%M')})")
            fixed_count += 1
    
    print(f"\n🎯 Result: {fixed_count} patiënten aangepast")
    
    # Show verification
    print("\n📊 Verification:")
    for patient in Patient.objects.all()[:5]:  # Show first 5
        if patient.ophaal_tijd and patient.eind_behandel_tijd:
            print(f"   {patient.naam}: ophaal={patient.ophaal_tijd.strftime('%H:%M')}, eind={patient.eind_behandel_tijd.strftime('%H:%M')}")

if __name__ == "__main__":
    fix_patient_times()
