#!/usr/bin/env python
"""
Script om nieuwe tijdblokken aan te maken volgens de nieuwe workflow
"""

import os
import django
from datetime import time

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import TimeSlot

def create_new_timeslots():
    """
    Maak nieuwe tijdblokken aan volgens de nieuwe workflow
    """
    print("🚀 Creating new time slots according to new workflow...")
    
    # Nieuwe tijdblokken volgens de specificatie
    new_timeslots = [
        # HALEN tijdblokken
        {
            'naam': '08:00 Uhr',
            'tijdblok_type': 'halen',
            'aankomst_tijd': time(8, 0),
            'actief': True,
            'default_selected': True
        },
        {
            'naam': '09:30 Uhr',
            'tijdblok_type': 'halen',
            'aankomst_tijd': time(9, 30),
            'actief': True,
            'default_selected': True
        },
        {
            'naam': '12:00 Uhr',
            'tijdblok_type': 'halen',
            'aankomst_tijd': time(12, 0),
            'actief': True,
            'default_selected': True
        },
        
        # BRENGEN tijdblokken
        {
            'naam': '12:00 Uhr',
            'tijdblok_type': 'brengen',
            'aankomst_tijd': time(12, 0),
            'actief': True,
            'default_selected': True
        },
        {
            'naam': '14:00 Uhr',
            'tijdblok_type': 'brengen',
            'aankomst_tijd': time(14, 0),
            'actief': True,
            'default_selected': True
        },
        {
            'naam': '16:00 Uhr',
            'tijdblok_type': 'brengen',
            'aankomst_tijd': time(16, 0),
            'actief': True,
            'default_selected': True
        },
        {
            'naam': '17:00 Uhr',
            'tijdblok_type': 'brengen',
            'aankomst_tijd': time(17, 0),
            'actief': True,
            'default_selected': True
        }
    ]
    
    # Verwijder alle bestaande tijdblokken
    print("🗑️  Deleting all existing time slots...")
    TimeSlot.objects.all().delete()
    
    # Maak nieuwe tijdblokken aan
    created_count = 0
    for timeslot_data in new_timeslots:
        timeslot = TimeSlot.objects.create(**timeslot_data)
        print(f"✅ Created: {timeslot.naam} ({timeslot.get_tijdblok_type_display()}) - {timeslot.aankomst_tijd}")
        created_count += 1
    
    print(f"\n🎯 Summary:")
    print(f"   Created: {created_count} time slots")
    print(f"   Total: {TimeSlot.objects.count()} time slots in database")
    
    # Toon alle tijdblokken
    print(f"\n📋 All time slots in database:")
    print("\nHALEN tijdblokken:")
    for timeslot in TimeSlot.objects.filter(tijdblok_type='halen').order_by('aankomst_tijd'):
        status = "✅ Active" if timeslot.actief else "❌ Inactive"
        print(f"   {timeslot.naam}: aankomst {timeslot.aankomst_tijd} - {status}")
    
    print("\nBRENGEN tijdblokken:")
    for timeslot in TimeSlot.objects.filter(tijdblok_type='brengen').order_by('aankomst_tijd'):
        status = "✅ Active" if timeslot.actief else "❌ Inactive"
        print(f"   {timeslot.naam}: eind {timeslot.aankomst_tijd} - {status}")

if __name__ == "__main__":
    create_new_timeslots()
