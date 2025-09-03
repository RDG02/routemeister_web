#!/usr/bin/env python
"""
Script om te controleren of er patiënten van vandaag zijn in de database
"""
import os
import sys
import django
from datetime import date

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, Vehicle, TimeSlot

def check_today_patients():
    """Controleer patiënten van vandaag"""
    today = date.today()
    print(f"📅 Vandaag: {today.strftime('%d %B %Y')}")
    print("=" * 50)
    
    # Alle patiënten van vandaag
    today_patients = Patient.objects.filter(ophaal_tijd__date=today)
    print(f"👥 Totaal patiënten vandaag: {today_patients.count()}")
    
    if today_patients.exists():
        print("\n📋 Patiënten van vandaag:")
        for patient in today_patients:
            vehicle_info = "Geen voertuig"
            if patient.toegewezen_voertuig:
                vehicle_info = f"{patient.toegewezen_voertuig.referentie or patient.toegewezen_voertuig.kenteken}"
            
            print(f"  • {patient.naam} - {patient.ophaal_tijd.strftime('%H:%M')} - {vehicle_info}")
        
        # Patiënten met toegewezen voertuig
        assigned_patients = today_patients.filter(toegewezen_voertuig__isnull=False)
        print(f"\n🚐 Patiënten met toegewezen voertuig: {assigned_patients.count()}")
        
        # Voertuigen met patiënten
        vehicles_with_patients = Vehicle.objects.filter(
            patient__ophaal_tijd__date=today,
            patient__toegewezen_voertuig__isnull=False
        ).distinct()
        
        print(f"🚗 Voertuigen met patiënten: {vehicles_with_patients.count()}")
        
        if vehicles_with_patients.exists():
            print("\n🚗 Voertuigen details:")
            for vehicle in vehicles_with_patients:
                patients = Patient.objects.filter(
                    toegewezen_voertuig=vehicle,
                    ophaal_tijd__date=today
                )
                print(f"  • {vehicle.referentie or vehicle.kenteken}: {patients.count()} patiënten")
        
        return True
    else:
        print("❌ Geen patiënten gevonden voor vandaag")
        return False

def check_planning_status():
    """Controleer planning status"""
    print("\n🔍 Planning Status:")
    print("-" * 30)
    
    # Controleer of er planning sessies zijn
    try:
        from planning.models_extended import PlanningSession
        active_sessions = PlanningSession.objects.filter(status__in=['concept', 'processing'])
        print(f"📊 Actieve planning sessies: {active_sessions.count()}")
        
        if active_sessions.exists():
            for session in active_sessions:
                print(f"  • {session.name} - {session.status} - {session.created_at}")
    except ImportError:
        print("⚠️ PlanningSession model niet beschikbaar")
    
    # Controleer tijdblokken
    active_timeslots = TimeSlot.objects.filter(actief=True)
    print(f"⏰ Actieve tijdblokken: {active_timeslots.count()}")
    
    if active_timeslots.exists():
        print("  Tijdblokken:")
        for ts in active_timeslots.order_by('aankomst_tijd'):
            print(f"    • {ts.naam} - {ts.aankomst_tijd.strftime('%H:%M')} ({ts.tijdblok_type})")

if __name__ == "__main__":
    print("🔍 ROUTEMEISTER - Planning Status Check")
    print("=" * 50)
    
    has_patients = check_today_patients()
    check_planning_status()
    
    print("\n" + "=" * 50)
    if has_patients:
        print("✅ Er zijn patiënten van vandaag - Dashboard toont planning")
    else:
        print("❌ Geen patiënten van vandaag - Dashboard toont 'Nieuwe Planning Maken' knop")
    
    print("\n🌐 Ga naar: http://localhost:8000/dashboard/")
