#!/usr/bin/env python
"""
Script om de database op te schonen voor een schone test
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

def clean_database():
    """Schoon de database op voor een schone test"""
    print("🧹 Database opschonen...")
    
    today = date.today()
    
    # Verwijder alle patiënten van vandaag
    today_patients = Patient.objects.filter(ophaal_tijd__date=today)
    patient_count = today_patients.count()
    today_patients.delete()
    print(f"🗑️ {patient_count} patiënten van vandaag verwijderd")
    
    # Check voertuigen
    vehicles = Vehicle.objects.all()
    print(f"🚗 {vehicles.count()} voertuigen in database")
    
    # Check tijdblokken
    timeslots = TimeSlot.objects.all()
    print(f"⏰ {timeslots.count()} tijdblokken in database")
    
    print("✅ Database opgeschoond!")
    return True

if __name__ == '__main__':
    clean_database()
