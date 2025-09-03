#!/usr/bin/env python
"""
Test script om te controleren welke tijdblokken daadwerkelijk patiënten hebben
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, Vehicle, TimeSlot
from datetime import date

def test_used_timeslots():
    """Test welke tijdblokken daadwerkelijk patiënten hebben"""
    print("🧪 Gebruikte Tijdblokken Test")
    print("=" * 40)
    
    today = date.today()
    
    # Haal alle patiënten van vandaag op
    patients = Patient.objects.filter(ophaal_tijd__date=today)
    print(f"📊 Patiënten van vandaag: {patients.count()}")
    
    # Haal alle actieve tijdblokken op
    all_timeslots = TimeSlot.objects.filter(actief=True).order_by('aankomst_tijd')
    print(f"📅 Totaal actieve tijdblokken: {all_timeslots.count()}")
    
    # Bepaal welke tijdblokken patiënten hebben
    used_timeslots = set()
    patients_by_timeslot = {}
    
    for patient in patients:
        if patient.toegewezen_tijdblok:
            timeslot_id = patient.toegewezen_tijdblok.id
            used_timeslots.add(timeslot_id)
            
            if timeslot_id not in patients_by_timeslot:
                patients_by_timeslot[timeslot_id] = []
            patients_by_timeslot[timeslot_id].append(patient)
    
    print(f"🎯 Tijdblokken met patiënten: {len(used_timeslots)}")
    
    # Toon alleen de gebruikte tijdblokken
    print(f"\n📋 Gebruikte Tijdblokken:")
    used_timeslot_objects = []
    
    for timeslot in all_timeslots:
        if timeslot.id in used_timeslots:
            used_timeslot_objects.append(timeslot)
            patient_count = len(patients_by_timeslot.get(timeslot.id, []))
            icon = "🚐" if timeslot.tijdblok_type == 'halen' else "🏠"
            print(f"   {icon} {timeslot.naam} ({timeslot.aankomst_tijd.strftime('%H:%M')}) - {patient_count} patiënten")
            
            # Toon patiënten in dit tijdblok
            for patient in patients_by_timeslot.get(timeslot.id, []):
                print(f"     - {patient.naam} ({patient.ophaal_tijd.time()} - {patient.eind_behandel_tijd.time()})")
    
    # Test timeline segmenten generatie
    print(f"\n🔧 Timeline Segmenten (alleen gebruikt):")
    timeline_segments = []
    
    for timeslot in used_timeslot_objects:
        time_str = timeslot.aankomst_tijd.strftime('%H:%M')
        if time_str not in [seg['time'] for seg in timeline_segments]:
            timeline_segments.append({
                'time': time_str,
                'timeslot_id': timeslot.id,
                'type': timeslot.tijdblok_type,
                'name': timeslot.naam
            })
    
    # Sorteer op tijd
    timeline_segments.sort(key=lambda x: x['time'])
    
    for i, segment in enumerate(timeline_segments, 1):
        icon = "🚐" if segment['type'] == 'halen' else "🏠"
        print(f"   {i}. {segment['time']} {icon} {segment['name']} ({segment['type']})")
    
    # Test HTML generatie
    print(f"\n🔧 HTML Timeline generatie (alleen gebruikt):")
    print("   <div class=\"timeline-track\">")
    for segment in timeline_segments:
        icon = "🚐" if segment['type'] == 'halen' else "🏠"
        print(f"       <div class=\"timeline-segment\" data-timeslot-id=\"{segment['timeslot_id']}\" data-time=\"{segment['time']}\" data-type=\"{segment['type']}\">")
        print(f"           {segment['time']}")
        print(f"           <span class=\"segment-icon\">{icon}</span>")
        print(f"       </div>")
    print("       <div class=\"timeline-cursor\"></div>")
    print("   </div>")
    
    return True

if __name__ == '__main__':
    test_used_timeslots()
