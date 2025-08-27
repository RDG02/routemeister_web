#!/usr/bin/env python
"""
Fix tijdblok toewijzingen voor alle patiënten
"""
import os
import django
from datetime import datetime
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, TimeSlot
from django.db import models

def fix_all_timeslot_assignments():
    print("🔧 Fix Alle Tijdblok Toewijzingen")
    print("=" * 50)
    
    today = datetime.now().date()
    patients = Patient.objects.filter(ophaal_tijd__date=today)
    timeslots = TimeSlot.objects.filter(actief=True).order_by('heen_start_tijd')
    
    print(f"👥 Patiënten vandaag: {patients.count()}")
    print(f"⏰ Beschikbare tijdblokken: {timeslots.count()}")
    print()
    
    fixed_count = 0
    
    for patient in patients:
        print(f"📍 {patient.naam}")
        print(f"   📅 Eerste afspraak: {patient.ophaal_tijd}")
        print(f"   📅 Eind tijd: {patient.eind_behandel_tijd}")
        
        # Zoek halen tijdblok (eerste afspraak tijd)
        halen_timeslot = None
        if patient.ophaal_tijd:
            first_appointment_time = patient.ophaal_tijd.time()
            print(f"   🚗 Eerste afspraak tijd: {first_appointment_time}")
            
            # Zoek tijdblok waar eerste afspraak tijd in past
            for ts in timeslots:
                if ts.heen_start_tijd <= first_appointment_time <= ts.heen_eind_tijd:
                    halen_timeslot = ts
                    print(f"   ✅ Halen tijdblok gevonden: {ts.naam}")
                    break
            
            if not halen_timeslot:
                print(f"   ❌ Geen halen tijdblok gevonden voor {first_appointment_time}")
        
        # Zoek brengen tijdblok (eind tijd)
        brengen_timeslot = None
        if patient.eind_behandel_tijd:
            end_time = patient.eind_behandel_tijd.time()
            print(f"   🏠 Eind tijd: {end_time}")
            
            # Zoek eerste tijdblok waar eind tijd <= terug_start_tijd
            for ts in timeslots:
                if end_time <= ts.terug_start_tijd:
                    brengen_timeslot = ts
                    print(f"   ✅ Brengen tijdblok gevonden: {ts.naam}")
                    break
            
            if not brengen_timeslot:
                print(f"   ❌ Geen brengen tijdblok gevonden voor {end_time}")
        
        # Update patiënt
        if halen_timeslot:
            patient.halen_tijdblok = halen_timeslot
            print(f"   🚗 Halen toegewezen: {halen_timeslot.naam}")
        
        if brengen_timeslot:
            patient.bringen_tijdblok = brengen_timeslot
            print(f"   🏠 Brengen toegewezen: {brengen_timeslot.naam}")
        
        if halen_timeslot or brengen_timeslot:
            patient.save()
            fixed_count += 1
            print(f"   ✅ Opgeslagen")
        else:
            print(f"   ❌ Geen tijdblokken toegewezen")
        
        print()
    
    print(f"📊 {fixed_count} patiënten gefixed")
    
    # Toon resultaat
    print(f"\n📋 Resultaat:")
    print("-" * 30)
    
    for patient in patients:
        halen = patient.halen_tijdblok.naam if patient.halen_tijdblok else "Geen"
        brengen = patient.bringen_tijdblok.naam if patient.bringen_tijdblok else "Geen"
        print(f"   {patient.naam}: {halen} / {brengen}")

if __name__ == "__main__":
    fix_all_timeslot_assignments()
    print(f"\n✅ Fix voltooid!")
