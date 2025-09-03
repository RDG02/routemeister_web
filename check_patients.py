#!/usr/bin/env python
"""
Script om alle patiënten van vandaag te controleren
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
from datetime import date

def check_patients():
    """Controleer alle patiënten van vandaag"""
    print("🔍 Check Patiënten")
    print("=" * 40)
    
    today = date.today()
    
    # Haal alle patiënten van vandaag op
    patients = Patient.objects.filter(ophaal_tijd__date=today)
    print(f"📊 Patiënten van vandaag: {patients.count()}")
    
    print(f"\n📋 Alle patiënten:")
    for i, patient in enumerate(patients, 1):
        timeslot_info = f" → {patient.toegewezen_tijdblok.naam}" if patient.toegewezen_tijdblok else " → Geen tijdblok"
        print(f"   {i}. {patient.naam} ({patient.ophaal_tijd.time()} - {patient.eind_behandel_tijd.time()}){timeslot_info}")
    
    return True

if __name__ == '__main__':
    check_patients()
