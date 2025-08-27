#!/usr/bin/env python
"""
Script to create standard time slots based on the old web app configuration
"""

import os
import django
from datetime import time

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import TimeSlot

def create_standard_timeslots():
    """
    Create standard time slots based on the old web app configuration
    """
    print("🚀 Creating standard time slots...")
    
    # Standard time slots from old web app
    standard_timeslots = [
        # Pickup time slots (Holen) - voor halen tijdblokken gebruiken we dezelfde tijd voor terug
        {
            'naam': 'Holen 08:30 Uhr',
            'heen_start_tijd': time(8, 30),  # 08:30
            'heen_eind_tijd': time(9, 30),   # 09:30
            'terug_start_tijd': time(8, 30), # Gebruik dezelfde tijd voor verplicht veld
            'terug_eind_tijd': time(9, 30),  # Gebruik dezelfde tijd voor verplicht veld
            'actief': True
        },
        {
            'naam': 'Holen 09:30 Uhr', 
            'heen_start_tijd': time(9, 30),  # 09:30
            'heen_eind_tijd': time(10, 30),  # 10:30
            'terug_start_tijd': time(9, 30), # Gebruik dezelfde tijd voor verplicht veld
            'terug_eind_tijd': time(10, 30), # Gebruik dezelfde tijd voor verplicht veld
            'actief': True
        },
        {
            'naam': 'Holen 10:30 Uhr',
            'heen_start_tijd': time(10, 30), # 10:30
            'heen_eind_tijd': time(11, 30),  # 11:30
            'terug_start_tijd': time(10, 30),# Gebruik dezelfde tijd voor verplicht veld
            'terug_eind_tijd': time(11, 30), # Gebruik dezelfde tijd voor verplicht veld
            'actief': True
        },
        {
            'naam': 'Holen 12:00 Uhr',
            'heen_start_tijd': time(12, 0),  # 12:00
            'heen_eind_tijd': time(13, 0),   # 13:00
            'terug_start_tijd': time(12, 0), # Gebruik dezelfde tijd voor verplicht veld
            'terug_eind_tijd': time(13, 0),  # Gebruik dezelfde tijd voor verplicht veld
            'actief': True
        },
        
        # Delivery time slots (Bringen) - voor brengen tijdblokken gebruiken we dezelfde tijd voor heen
        {
            'naam': 'Bringen 12:00 Uhr',
            'heen_start_tijd': time(12, 0),  # Gebruik dezelfde tijd voor verplicht veld
            'heen_eind_tijd': time(13, 0),   # Gebruik dezelfde tijd voor verplicht veld
            'terug_start_tijd': time(12, 0), # 12:00
            'terug_eind_tijd': time(13, 0),  # 13:00
            'actief': True
        },
        {
            'naam': 'Bringen 13:30 Uhr',
            'heen_start_tijd': time(13, 30), # Gebruik dezelfde tijd voor verplicht veld
            'heen_eind_tijd': time(14, 30),  # Gebruik dezelfde tijd voor verplicht veld
            'terug_start_tijd': time(13, 30),# 13:30
            'terug_eind_tijd': time(14, 30), # 14:30
            'actief': True
        },
        {
            'naam': 'Bringen 16:00 Uhr',
            'heen_start_tijd': time(16, 0),  # Gebruik dezelfde tijd voor verplicht veld
            'heen_eind_tijd': time(17, 0),   # Gebruik dezelfde tijd voor verplicht veld
            'terug_start_tijd': time(16, 0), # 16:00
            'terug_eind_tijd': time(17, 0),  # 17:00
            'actief': True
        }
    ]
    
    created_count = 0
    updated_count = 0
    
    for timeslot_data in standard_timeslots:
        timeslot, created = TimeSlot.objects.get_or_create(
            naam=timeslot_data['naam'],
            defaults=timeslot_data
        )
        
        if created:
            print(f"✅ Created: {timeslot.naam}")
            created_count += 1
        else:
            # Update existing timeslot with new data
            for key, value in timeslot_data.items():
                setattr(timeslot, key, value)
            timeslot.save()
            print(f"🔄 Updated: {timeslot.naam}")
            updated_count += 1
    
    print(f"\n🎯 Summary:")
    print(f"   Created: {created_count} time slots")
    print(f"   Updated: {updated_count} time slots")
    print(f"   Total: {TimeSlot.objects.count()} time slots in database")
    
    # Show all time slots
    print(f"\n📋 All time slots in database:")
    for timeslot in TimeSlot.objects.all().order_by('naam'):
        heen_str = f"{timeslot.heen_start_tijd}-{timeslot.heen_eind_tijd}" if timeslot.heen_start_tijd else "N/A"
        terug_str = f"{timeslot.terug_start_tijd}-{timeslot.terug_eind_tijd}" if timeslot.terug_start_tijd else "N/A"
        status = "✅ Active" if timeslot.actief else "❌ Inactive"
        print(f"   {timeslot.naam}: Halen={heen_str}, Brengen={terug_str} - {status}")

if __name__ == "__main__":
    create_standard_timeslots()
