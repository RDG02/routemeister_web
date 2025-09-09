#!/usr/bin/env python
"""
Update patiënten naar vandaag
"""
import os
import sys
import django
from datetime import date, datetime, time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient

def update_patients_to_today():
    today = date.today()
    updated = 0
    
    for patient in Patient.objects.all():
        # Update ophaal_tijd naar vandaag
        if patient.ophaal_tijd:
            patient.ophaal_tijd = datetime.combine(today, patient.ophaal_tijd.time())
        
        # Update eind_behandel_tijd naar vandaag
        if patient.eind_behandel_tijd:
            patient.eind_behandel_tijd = datetime.combine(today, patient.eind_behandel_tijd.time())
        
        patient.save()
        updated += 1
        print(f"Updated {patient.naam} to {today}")
    
    print(f"\n✅ Updated {updated} patients to {today}")

if __name__ == "__main__":
    update_patients_to_today()
