#!/usr/bin/env python
"""
Debug Ute Frank assignment
"""
import os
import django
from datetime import datetime, time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, TimeSlot

def debug_ute_frank_assignment():
    print("🔍 Debug Ute Frank Assignment")
    print("=" * 40)
    
    # Haal Ute Frank op
    try:
        ute_frank = Patient.objects.get(naam="Ute Frank")
        print(f"👤 Patiënt: {ute_frank.naam}")
        print(f"📅 Eerste afspraak: {ute_frank.ophaal_tijd}")
        print(f"🕐 Eerste afspraak tijd: {ute_frank.ophaal_tijd.time()}")
        print()
    except Patient.DoesNotExist:
        print("❌ Ute Frank niet gevonden")
        return
    
    # Haal geselecteerde tijdblokken op
    selected_timeslots = TimeSlot.objects.filter(actief=True, default_selected=True).order_by('heen_start_tijd')
    halen_timeslots = [ts for ts in selected_timeslots if ts.naam.startswith('Holen')]
    
    print("📅 HALEN Tijdblokken:")
    print("-" * 40)
    for i, ts in enumerate(halen_timeslots):
        next_start = None
        if i + 1 < len(halen_timeslots):
            next_start = halen_timeslots[i + 1].heen_start_tijd
        else:
            next_start = ts.heen_eind_tijd
        
        print(f"   {ts.naam}: {ts.heen_start_tijd} - {next_start}")
    print()
    
    # Test de logica stap voor stap
    first_appointment_time = ute_frank.ophaal_tijd.time()
    print(f"🎯 Test voor {ute_frank.naam} ({first_appointment_time}):")
    print("-" * 40)
    
    for i, ts in enumerate(halen_timeslots):
        current_block_start = ts.heen_start_tijd
        
        # Zoek volgende Halen tijdblok
        next_block_start = None
        for j in range(i + 1, len(halen_timeslots)):
            next_ts = halen_timeslots[j]
            if next_ts.naam.startswith('Holen'):
                next_block_start = next_ts.heen_start_tijd
                break
        
        # Als er geen volgende Halen tijdblok is, gebruik dan het einde van het huidige blok
        if next_block_start is None:
            next_block_start = ts.heen_eind_tijd
        
        # Check of patiënt tijd valt tussen huidige blok start en volgende blok start
        condition = current_block_start <= first_appointment_time < next_block_start
        
        print(f"   {ts.naam}: {current_block_start} <= {first_appointment_time} < {next_block_start} = {condition}")
        
        if condition:
            print(f"   ✅ {ute_frank.naam} wordt toegewezen aan {ts.naam}")
            break

if __name__ == "__main__":
    debug_ute_frank_assignment()
    print(f"\n✅ Debug voltooid!")
