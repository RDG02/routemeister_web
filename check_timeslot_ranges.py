#!/usr/bin/env python
"""
Check tijdblok ranges
"""
import os
import django
from datetime import datetime
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import TimeSlot

def check_timeslot_ranges():
    print("🔍 Check Tijdblok Ranges")
    print("=" * 40)
    
    # Haal geselecteerde tijdblokken op
    selected_timeslots = TimeSlot.objects.filter(actief=True, default_selected=True).order_by('heen_start_tijd')
    
    print(f"⏰ Geselecteerde tijdblokken: {selected_timeslots.count()}")
    print()
    
    print("📅 Alle Geselecteerde Tijdblokken:")
    print("-" * 40)
    for ts in selected_timeslots:
        print(f"   {ts.naam}")
        print(f"     Halen: {ts.heen_start_tijd} - {ts.heen_eind_tijd}")
        print(f"     Brengen: {ts.terug_start_tijd} - {ts.terug_eind_tijd}")
        print()
    
    print("🚗 HALEN Tijdblokken:")
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
    print("🏠 BRENGEN Tijdblokken:")
    print("-" * 40)
    brengen_timeslots = [ts for ts in selected_timeslots if ts.naam.startswith('Bringen')]
    for ts in brengen_timeslots:
        print(f"   {ts.naam}: {ts.terug_start_tijd} - {ts.terug_eind_tijd}")

if __name__ == "__main__":
    check_timeslot_ranges()
    print(f"\n✅ Check voltooid!")
