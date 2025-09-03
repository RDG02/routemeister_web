#!/usr/bin/env python
"""
Test script om te controleren of de timeline segmenten correct worden gegenereerd
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

def test_timeline_segments():
    """Test de timeline segmenten generatie"""
    print("🧪 Timeline Segmenten Test")
    print("=" * 40)
    
    # Haal alle actieve tijdblokken op
    timeslots = TimeSlot.objects.filter(actief=True).order_by('aankomst_tijd')
    
    print(f"📊 Totaal actieve tijdblokken: {timeslots.count()}")
    
    # Genereer timeline segmenten zoals in de view
    timeline_segments = []
    for timeslot in timeslots:
        time_str = timeslot.aankomst_tijd.strftime('%H:%M')
        if time_str not in [seg['time'] for seg in timeline_segments]:
            timeline_segments.append({
                'time': time_str,
                'timeslot_id': timeslot.id,
                'type': timeslot.tijdblok_type,
                'name': timeslot.naam
            })
    
    print(f"🎯 Unieke timeline segmenten: {len(timeline_segments)}")
    
    print("\n📋 Timeline Segmenten:")
    for i, segment in enumerate(timeline_segments, 1):
        icon = "🚐" if segment['type'] == 'halen' else "🏠"
        print(f"   {i}. {segment['time']} {icon} {segment['name']} ({segment['type']})")
    
    # Check patiënten per tijdblok
    today = date.today()
    patients = Patient.objects.filter(ophaal_tijd__date=today)
    
    print(f"\n👥 Patiënten van vandaag: {patients.count()}")
    
    # Groepeer patiënten per tijdblok
    patients_by_timeslot = {}
    for patient in patients:
        if patient.toegewezen_tijdblok:
            timeslot_name = patient.toegewezen_tijdblok.naam
            if timeslot_name not in patients_by_timeslot:
                patients_by_timeslot[timeslot_name] = []
            patients_by_timeslot[timeslot_name].append(patient)
    
    print(f"\n📅 Patiënten per tijdblok:")
    for timeslot_name, timeslot_patients in patients_by_timeslot.items():
        print(f"   {timeslot_name}: {len(timeslot_patients)} patiënten")
        for patient in timeslot_patients:
            print(f"     - {patient.naam} ({patient.ophaal_tijd.time()} - {patient.eind_behandel_tijd.time()})")
    
    # Test HTML generatie
    print(f"\n🔧 HTML Timeline generatie test:")
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
    test_timeline_segments()
