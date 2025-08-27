#!/usr/bin/env python
"""
Fix tijdblok ranges
"""
import os
import django
from datetime import datetime, time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import TimeSlot

def fix_timeslot_ranges():
    print("🔧 Fix Tijdblok Ranges")
    print("=" * 40)
    
    # Correcte ranges volgens de logica
    correct_ranges = {
        'Holen 08:00 Uhr': {
            'heen_start': time(8, 0),
            'heen_eind': time(9, 30),
            'terug_start': time(8, 0),
            'terug_eind': time(9, 30)
        },
        'Holen 09:30 Uhr': {
            'heen_start': time(9, 30),
            'heen_eind': time(10, 30),
            'terug_start': time(9, 30),
            'terug_eind': time(10, 30)
        },
        'Holen 10:30 Uhr': {
            'heen_start': time(10, 30),
            'heen_eind': time(12, 0),  # Gecorrigeerd: 10:30-12:00
            'terug_start': time(10, 30),
            'terug_eind': time(12, 0)
        },
        'Holen 12:00 Uhr': {
            'heen_start': time(12, 0),
            'heen_eind': time(13, 0),
            'terug_start': time(12, 0),
            'terug_eind': time(13, 0)
        }
    }
    
    print("📅 Correcte Ranges:")
    print("-" * 40)
    for name, ranges in correct_ranges.items():
        print(f"   {name}: {ranges['heen_start']} - {ranges['heen_eind']}")
    print()
    
    # Update tijdblokken
    updated_count = 0
    for name, ranges in correct_ranges.items():
        try:
            timeslot = TimeSlot.objects.get(naam=name, actief=True)
            
            # Check of update nodig is
            if (timeslot.heen_start_tijd != ranges['heen_start'] or 
                timeslot.heen_eind_tijd != ranges['heen_eind'] or
                timeslot.terug_start_tijd != ranges['terug_start'] or
                timeslot.terug_eind_tijd != ranges['terug_eind']):
                
                print(f"🔄 Updating {name}...")
                timeslot.heen_start_tijd = ranges['heen_start']
                timeslot.heen_eind_tijd = ranges['heen_eind']
                timeslot.terug_start_tijd = ranges['terug_start']
                timeslot.terug_eind_tijd = ranges['terug_eind']
                timeslot.save()
                updated_count += 1
                print(f"   ✅ {name} updated")
            else:
                print(f"   ✅ {name} already correct")
                
        except TimeSlot.DoesNotExist:
            print(f"   ❌ {name} not found")
    
    print(f"\n📊 {updated_count} tijdblokken updated")
    
    # Toon resultaat
    print(f"\n📋 Resultaat:")
    print("-" * 40)
    selected_timeslots = TimeSlot.objects.filter(actief=True, default_selected=True).order_by('heen_start_tijd')
    halen_timeslots = [ts for ts in selected_timeslots if ts.naam.startswith('Holen')]
    
    for i, ts in enumerate(halen_timeslots):
        next_start = None
        if i + 1 < len(halen_timeslots):
            next_start = halen_timeslots[i + 1].heen_start_tijd
        else:
            next_start = ts.heen_eind_tijd
        
        print(f"   {ts.naam}: {ts.heen_start_tijd} - {next_start}")

if __name__ == "__main__":
    fix_timeslot_ranges()
    print(f"\n✅ Fix voltooid!")
