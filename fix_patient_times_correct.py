#!/usr/bin/env python
"""
Fix patient times correctly
Kolom 18 = Start tijd (ophaal tijd) - NIET afspraak tijd!
Geen 1 uur aftrekken nodig!
"""

import os
import django
from datetime import datetime, timedelta

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient

def fix_patient_times_correct():
    print("🔧 Fixing Patient Times CORRECTLY")
    print("=" * 40)
    print("Kolom 18 = Start tijd (ophaal tijd) - NIET afspraak tijd!")
    print("Geen 1 uur aftrekken nodig!")
    print()
    
    # Get all patients and fix their times according to the correct logic
    patients = Patient.objects.all()
    
    # Expected times based on user's table
    expected_times = {
        'Anette Schnurpfeil': ('08:45', '15:15'),
        'Wilfried Hermanns': ('08:45', '15:15'),
        'Natalia Gerdt': ('10:15', '16:35'),
        'Beatrice Harig': ('10:25', '16:15'),
        'Brigitte Effelsberg': ('10:45', '16:15'),
        'Kubra Aydin': ('10:45', '16:15'),
        'Marita Buschmann': ('10:45', '16:15'),
        'Frank Suhre': ('10:45', '16:15'),
        'Ute Frank': ('11:45', '17:45'),
        'Birgit Schmidt': ('11:45', '17:15'),
        'Hannelore Kehl': ('12:15', '17:35'),
        'Stephan Roth': ('12:15', '17:05'),
    }
    
    fixed_count = 0
    for patient in patients:
        if patient.naam in expected_times:
            expected_start, expected_end = expected_times[patient.naam]
            
            # Parse expected times
            start_hour, start_minute = map(int, expected_start.split(':'))
            end_hour, end_minute = map(int, expected_end.split(':'))
            
            # Get current date
            current_date = patient.ophaal_tijd.date() if patient.ophaal_tijd else datetime.now().date()
            
            # Create correct datetime objects
            correct_start = datetime.combine(current_date, datetime.min.time().replace(hour=start_hour, minute=start_minute))
            correct_end = datetime.combine(current_date, datetime.min.time().replace(hour=end_hour, minute=end_minute))
            
            # Update patient
            old_start = patient.ophaal_tijd.strftime("%H:%M") if patient.ophaal_tijd else "None"
            old_end = patient.eind_behandel_tijd.strftime("%H:%M") if patient.eind_behandel_tijd else "None"
            
            patient.ophaal_tijd = correct_start
            patient.eind_behandel_tijd = correct_end
            patient.save()
            
            print(f"✅ {patient.naam}: {old_start}→{expected_start}, {old_end}→{expected_end}")
            fixed_count += 1
    
    print(f"\n🎯 Result: {fixed_count} patiënten aangepast")
    
    # Show verification
    print("\n📊 Verification:")
    for patient in Patient.objects.all()[:5]:  # Show first 5
        if patient.ophaal_tijd and patient.eind_behandel_tijd:
            print(f"   {patient.naam}: ophaal={patient.ophaal_tijd.strftime('%H:%M')}, eind={patient.eind_behandel_tijd.strftime('%H:%M')}")

if __name__ == "__main__":
    fix_patient_times_correct()
