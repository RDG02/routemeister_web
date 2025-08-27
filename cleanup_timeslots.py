#!/usr/bin/env python
"""
Clean up duplicate and overlapping time slots
Keep only the correct time slots according to the user's logic
"""

import os
import django
from datetime import time

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import TimeSlot

def cleanup_timeslots():
    print("🧹 Cleaning up Time Slots")
    print("=" * 40)
    
    # Define the correct time slots
    correct_timeslots = [
        # HALEN (Pickup)
        {
            'naam': 'Holen 08:00 Uhr',
            'heen_start_tijd': time(8, 0),
            'heen_eind_tijd': time(9, 30),
            'terug_start_tijd': time(8, 0),
            'terug_eind_tijd': time(9, 30),
            'actief': True,
            'default_selected': True
        },
        {
            'naam': 'Holen 09:30 Uhr',
            'heen_start_tijd': time(9, 30),
            'heen_eind_tijd': time(10, 30),
            'terug_start_tijd': time(9, 30),
            'terug_eind_tijd': time(10, 30),
            'actief': True,
            'default_selected': True
        },
        {
            'naam': 'Holen 10:30 Uhr',
            'heen_start_tijd': time(10, 30),
            'heen_eind_tijd': time(11, 30),
            'terug_start_tijd': time(10, 30),
            'terug_eind_tijd': time(11, 30),
            'actief': True,
            'default_selected': True
        },
        {
            'naam': 'Holen 12:00 Uhr',
            'heen_start_tijd': time(12, 0),
            'heen_eind_tijd': time(13, 0),
            'terug_start_tijd': time(12, 0),
            'terug_eind_tijd': time(13, 0),
            'actief': True,
            'default_selected': True
        },
        # BRENGEN (Delivery)
        {
            'naam': 'Bringen 12:00 Uhr',
            'heen_start_tijd': time(12, 0),
            'heen_eind_tijd': time(13, 0),
            'terug_start_tijd': time(12, 0),
            'terug_eind_tijd': time(13, 0),
            'actief': True,
            'default_selected': True
        },
        {
            'naam': 'Bringen 13:00 Uhr',
            'heen_start_tijd': time(13, 0),
            'heen_eind_tijd': time(14, 0),
            'terug_start_tijd': time(13, 0),
            'terug_eind_tijd': time(14, 0),
            'actief': True,
            'default_selected': True
        },
        {
            'naam': 'Bringen 14:00 Uhr',
            'heen_start_tijd': time(14, 0),
            'heen_eind_tijd': time(15, 0),
            'terug_start_tijd': time(14, 0),
            'terug_eind_tijd': time(15, 0),
            'actief': True,
            'default_selected': True
        },
        {
            'naam': 'Bringen 15:00 Uhr',
            'heen_start_tijd': time(15, 0),
            'heen_eind_tijd': time(16, 0),
            'terug_start_tijd': time(15, 0),
            'terug_eind_tijd': time(16, 0),
            'actief': True,
            'default_selected': True
        },
        {
            'naam': 'Bringen 16:00 Uhr',
            'heen_start_tijd': time(16, 0),
            'heen_eind_tijd': time(17, 0),
            'terug_start_tijd': time(16, 0),
            'terug_eind_tijd': time(17, 0),
            'actief': True,
            'default_selected': True
        },
        {
            'naam': 'Bringen 17:00 Uhr',
            'heen_start_tijd': time(17, 0),
            'heen_eind_tijd': time(18, 0),
            'terug_start_tijd': time(17, 0),
            'terug_eind_tijd': time(18, 0),
            'actief': True,
            'default_selected': True
        }
    ]
    
    # Delete all existing time slots
    print("🗑️  Deleting all existing time slots...")
    TimeSlot.objects.all().delete()
    
    # Create new correct time slots
    print("✅ Creating correct time slots...")
    for ts_data in correct_timeslots:
        timeslot = TimeSlot.objects.create(**ts_data)
        print(f"   Created: {timeslot.naam}")
    
    print(f"\n🎯 Result: {TimeSlot.objects.count()} time slots created")
    
    # Show final result
    print("\n📊 Final Time Slots:")
    for ts in TimeSlot.objects.all().order_by('heen_start_tijd'):
        print(f"   {ts.naam}: {ts.heen_start_tijd}-{ts.heen_eind_tijd}")

if __name__ == "__main__":
    cleanup_timeslots()
