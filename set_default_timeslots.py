#!/usr/bin/env python
"""
Script to set default time slots for testing
"""

import os
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import TimeSlot

def set_default_timeslots():
    """
    Set some time slots as default selected
    """
    print("🚀 Setting default time slots...")
    
    # Set some standard time slots as default
    default_timeslot_names = [
        'Holen 09:30 Uhr',
        'Holen 10:00 Uhr', 
        'Bringen 16:00'
    ]
    
    updated_count = 0
    
    for timeslot_name in default_timeslot_names:
        try:
            timeslot = TimeSlot.objects.get(naam=timeslot_name)
            timeslot.default_selected = True
            timeslot.save()
            print(f"✅ Set as default: {timeslot.naam}")
            updated_count += 1
        except TimeSlot.DoesNotExist:
            print(f"❌ Not found: {timeslot_name}")
    
    print(f"\n🎯 Summary:")
    print(f"   Updated: {updated_count} time slots set as default")
    
    # Show all default time slots
    print(f"\n📋 Default time slots:")
    default_timeslots = TimeSlot.objects.filter(default_selected=True)
    for timeslot in default_timeslots:
        print(f"   ✅ {timeslot.naam}")

if __name__ == "__main__":
    set_default_timeslots()
