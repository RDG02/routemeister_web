#!/usr/bin/env python
"""
Script om patiënten toe te wijzen aan de juiste tijdblokken zoals in de wizard assignment pagina
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
from datetime import date, time

def fix_patient_timeslots():
    """Wijs patiënten toe aan de juiste tijdblokken"""
    print("🔧 Fix Patient Timeslots")
    print("=" * 40)
    
    today = date.today()
    
    # Haal alle patiënten van vandaag op
    patients = Patient.objects.filter(ophaal_tijd__date=today)
    print(f"📊 Patiënten van vandaag: {patients.count()}")
    
    # Haal alle actieve tijdblokken op
    timeslots = TimeSlot.objects.filter(actief=True).order_by('aankomst_tijd')
    print(f"📅 Beschikbare tijdblokken: {timeslots.count()}")
    
    # Definieer de toewijzingen zoals in de wizard assignment pagina
    # Gebaseerd op de screenshot data
    patient_assignments = {
        # 10:00 Uhr (halen) - 3 patiënten
        '10:00': [
            'Wilfried Dose',
            'Andrea Pluschke', 
            'Hans Robert Alfred Boehm'
        ],
        # 10:30 Uhr (halen) - 4 patiënten
        '10:30': [
            'Iris Kihn',
            'Rainer Marx',
            'Magda Niesen',
            'Esther Katharina Ries'
        ],
        # 11:30 Uhr (halen) - 1 patiënt
        '11:30': [
            'Eugenie Philomene Djibo-Zongo'
        ],
        # 12:00 Uhr (halen) - 1 patiënt (Hans Robert Alfred Boehm is al toegewezen aan 10:00, dus skip)
        '12:00': [],
        # 15:30 Uhr (brengen) - 2 patiënten
        '15:30': [
            'Lofo Makonga',
            'Julia Gluckmann'
        ],
        # 16:30 Uhr (brengen) - 5 patiënten
        '16:30': [
            'Wilfried Dose',
            'Andrea Pluschke',
            'Rainer Marx',
            'Magda Niesen',
            'Esther Katharina Ries'
        ],
        # 17:00 Uhr (brengen) - 2 patiënten
        '17:00': [
            'Iris Kihn',
            'Eugenie Philomene Djibo-Zongo'
        ]
    }
    
    # Maak een mapping van tijd naar tijdblok objecten
    timeslot_map = {}
    for timeslot in timeslots:
        time_str = timeslot.aankomst_tijd.strftime('%H:%M')
        if time_str in patient_assignments:
            timeslot_map[time_str] = timeslot
    
    print(f"🎯 Tijdblokken die we gaan gebruiken:")
    for time_str, timeslot in timeslot_map.items():
        icon = "🚐" if timeslot.tijdblok_type == 'halen' else "🏠"
        print(f"   {time_str} {icon} {timeslot.naam} ({timeslot.tijdblok_type})")
    
    # Wijs patiënten toe
    assigned_count = 0
    for time_str, patient_names in patient_assignments.items():
        if time_str not in timeslot_map:
            print(f"⚠️ Tijdblok {time_str} niet gevonden")
            continue
            
        timeslot = timeslot_map[time_str]
        print(f"\n📅 Toewijzen aan {time_str} ({timeslot.naam}):")
        
        for patient_name in patient_names:
            # Zoek patiënt op naam
            patient = None
            for p in patients:
                if p.naam == patient_name:
                    patient = p
                    break
            
            if patient:
                patient.toegewezen_tijdblok = timeslot
                patient.save()
                assigned_count += 1
                print(f"   ✅ {patient.naam} → {timeslot.naam}")
            else:
                print(f"   ❌ Patiënt '{patient_name}' niet gevonden")
    
    print(f"\n📊 Toewijzing voltooid: {assigned_count} patiënten toegewezen")
    
    # Toon resultaat
    print(f"\n📋 Resultaat per tijdblok:")
    for time_str, timeslot in timeslot_map.items():
        timeslot_patients = Patient.objects.filter(
            ophaal_tijd__date=today,
            toegewezen_tijdblok=timeslot
        )
        icon = "🚐" if timeslot.tijdblok_type == 'halen' else "🏠"
        print(f"   {time_str} {icon} {timeslot.naam}: {timeslot_patients.count()} patiënten")
        for patient in timeslot_patients:
            print(f"     - {patient.naam} ({patient.ophaal_tijd.time()} - {patient.eind_behandel_tijd.time()})")
    
    return True

if __name__ == '__main__':
    fix_patient_timeslots()
