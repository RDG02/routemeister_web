#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, TimeSlot, Vehicle
from datetime import date

def debug_dashboard_timeslots():
    """Debug welke tijdsblokken de dashboard ophaalt"""
    
    # Get today's date
    today = date.today()
    print(f"=== Debug Dashboard Tijdsblokken voor {today} ===\n")
    
    # Get today's patients with assigned vehicles
    today_patients = Patient.objects.filter(
        ophaal_tijd__date=today,
        toegewezen_voertuig__isnull=False,
        status__in=['gepland', 'onderweg']
    ).order_by('ophaal_tijd')
    
    print(f"Patiënten voor vandaag: {today_patients.count()}")
    for patient in today_patients[:5]:
        print(f"- {patient.naam}: {patient.ophaal_tijd} - {patient.eind_behandel_tijd}")
    
    # Get all active timeslots
    all_timeslots = TimeSlot.objects.filter(actief=True).order_by('aankomst_tijd')
    print(f"\nAlle actieve tijdsblokken: {all_timeslots.count()}")
    for timeslot in all_timeslots:
        print(f"- {timeslot.aankomst_tijd.strftime('%H:%M')} {timeslot.tijdblok_type}")
    
    # Simulate dashboard logic
    print(f"\n=== Dashboard Logic ===")
    used_timeslot_ids = set()
    for patient in today_patients:
        print(f"\nPatiënt: {patient.naam}")
        print(f"  Ophaal tijd: {patient.ophaal_tijd}")
        print(f"  Eind tijd: {patient.eind_behandel_tijd}")
        
        # Find matching timeslot
        for timeslot in all_timeslots:
            if timeslot.tijdblok_type == 'halen' and patient.ophaal_tijd.hour == timeslot.aankomst_tijd.hour:
                print(f"  -> Match HALEN: {timeslot.aankomst_tijd.strftime('%H:%M')} (ID: {timeslot.id})")
                used_timeslot_ids.add(timeslot.id)
                break
            elif timeslot.tijdblok_type == 'brengen' and patient.eind_behandel_tijd.hour == timeslot.aankomst_tijd.hour:
                print(f"  -> Match BRENGEN: {timeslot.aankomst_tijd.strftime('%H:%M')} (ID: {timeslot.id})")
                used_timeslot_ids.add(timeslot.id)
                break
    
    print(f"\nGebruikte tijdsblok IDs: {used_timeslot_ids}")
    
    # Get final timeslots for dashboard
    dashboard_timeslots = TimeSlot.objects.filter(
        id__in=used_timeslot_ids
    ).order_by('aankomst_tijd')
    
    print(f"\nDashboard toont {dashboard_timeslots.count()} tijdsblokken:")
    for timeslot in dashboard_timeslots:
        print(f"- {timeslot.aankomst_tijd.strftime('%H:%M')} {timeslot.tijdblok_type}")

if __name__ == '__main__':
    debug_dashboard_timeslots()
