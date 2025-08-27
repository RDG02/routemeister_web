#!/usr/bin/env python
"""
Test correcte HALEN logica
"""
import os
import django
from datetime import datetime
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, TimeSlot
from planning.views import assign_timeslots_to_patients
from django.db import models

def test_correct_halen_logic():
    print("🔍 Test Correcte HALEN Logica")
    print("=" * 50)
    
    today = datetime.now().date()
    patients = Patient.objects.filter(ophaal_tijd__date=today)
    
    # Haal geselecteerde tijdblokken op
    selected_timeslots = TimeSlot.objects.filter(actief=True, default_selected=True).order_by('heen_start_tijd')
    
    print(f"👥 Patiënten vandaag: {patients.count()}")
    print(f"⏰ Geselecteerde tijdblokken: {selected_timeslots.count()}")
    print()
    
    # Toon geselecteerde Halen tijdblokken
    print("📅 Geselecteerde HALEN Tijdblokken:")
    print("-" * 40)
    halen_timeslots = [ts for ts in selected_timeslots if ts.naam.startswith('Holen')]
    for i, ts in enumerate(halen_timeslots):
        next_start = None
        if i + 1 < len(halen_timeslots):
            next_start = halen_timeslots[i + 1].heen_start_tijd
        else:
            next_start = ts.heen_eind_tijd
        
        print(f"   {ts.naam}: {ts.heen_start_tijd} - {next_start}")
    print()
    
    # Clear bestaande toewijzingen
    print("🧹 Clearing bestaande toewijzingen...")
    for patient in patients:
        patient.halen_tijdblok = None
        patient.bringen_tijdblok = None
        patient.save()
    
    # Run verbeterde toewijzing
    print("🔄 Running verbeterde toewijzing...")
    assign_timeslots_to_patients(patients)
    
    # Check resultaat
    print(f"\n📋 Resultaat:")
    print("-" * 30)
    
    for patient in patients:
        halen = patient.halen_tijdblok.naam if patient.halen_tijdblok else "Geen"
        brengen = patient.bringen_tijdblok.naam if patient.bringen_tijdblok else "Geen"
        first_appointment = patient.ophaal_tijd.time() if patient.ophaal_tijd else "Geen"
        
        print(f"   {patient.naam}: {first_appointment} → {halen} / {brengen}")
    
    # Test specifieke gevallen
    print(f"\n🎯 Test Specifieke Gevallen:")
    print("-" * 30)
    
    test_cases = [
        ("Wilfried Hermanns", "08:45", "Holen 08:00 Uhr"),
        ("Natalia Gerdt", "10:15", "Holen 09:30 Uhr"),
        ("Beatrice Harig", "10:25", "Holen 09:30 Uhr"),
        ("Brigitte Effelsberg", "10:45", "Holen 10:30 Uhr"),
        ("Ute Frank", "11:45", "Holen 12:00 Uhr"),
        ("Hannelore Kehl", "12:15", "Holen 12:00 Uhr"),
    ]
    
    for test_name, expected_time, expected_block in test_cases:
        try:
            patient = patients.get(naam=test_name)
            actual_block = patient.halen_tijdblok.naam if patient.halen_tijdblok else "Geen"
            actual_time = patient.ophaal_tijd.time() if patient.ophaal_tijd else "Geen"
            
            status = "✅" if actual_block == expected_block else "❌"
            print(f"   {status} {test_name}: {actual_time} → {actual_block} (verwacht: {expected_block})")
            
        except Patient.DoesNotExist:
            print(f"   ❌ {test_name}: Niet gevonden in database")

if __name__ == "__main__":
    test_correct_halen_logic()
    print(f"\n✅ Test voltooid!")
