#!/usr/bin/env python
"""
Test finale tijdblok toewijzingen
"""
import os
import django
from datetime import datetime
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, TimeSlot
from planning.services.simple_router import simple_route_service
from planning.views import assign_timeslots_to_patients
from django.db import models

def test_final_assignments():
    print("🔍 Test Finale Tijdblok Toewijzingen")
    print("=" * 50)
    
    today = datetime.now().date()
    patients = Patient.objects.filter(ophaal_tijd__date=today)
    
    print(f"👥 Patiënten vandaag: {patients.count()}")
    
    # Clear bestaande toewijzingen
    print("🧹 Clearing bestaande toewijzingen...")
    for patient in patients:
        patient.halen_tijdblok = None
        patient.bringen_tijdblok = None
        patient.save()
    
    # Run verbeterde toewijzing
    print("🔄 Running verbeterde toewijzing...")
    assign_timeslots_to_patients(patients)
    
    # Check resultaat
    print(f"\n📋 Resultaat:")
    print("-" * 30)
    
    assigned_count = 0
    for patient in patients:
        halen = patient.halen_tijdblok.naam if patient.halen_tijdblok else "Geen"
        brengen = patient.bringen_tijdblok.naam if patient.bringen_tijdblok else "Geen"
        print(f"   {patient.naam}: {halen} / {brengen}")
        
        if patient.halen_tijdblok or patient.bringen_tijdblok:
            assigned_count += 1
    
    print(f"\n📊 {assigned_count}/{patients.count()} patiënten toegewezen")
    
    # Test route planning
    print(f"\n🚀 Test Route Planning:")
    print("-" * 30)
    
    from planning.models import Vehicle
    vehicles = Vehicle.objects.filter(status='beschikbaar')
    
    assigned_patients = patients.filter(
        models.Q(halen_tijdblok__isnull=False) | 
        models.Q(bringen_tijdblok__isnull=False)
    ).distinct()
    
    print(f"📊 Patiënten met tijdblok: {assigned_patients.count()}")
    
    if assigned_patients.count() > 0:
        try:
            routes = simple_route_service.plan_simple_routes(vehicles, assigned_patients)
            print(f"✅ Routes gegenereerd: {len(routes)}")
            
            if routes:
                print(f"\n📋 Route Details:")
                for i, route in enumerate(routes):
                    print(f"   Route {i+1}: {route.get('vehicle_name', 'Onbekend')}")
                    print(f"     Type: {route.get('route_type', 'Onbekend')}")
                    print(f"     Tijdblok: {route.get('timeslot_name', 'Onbekend')}")
                    print(f"     Patiënten: {route.get('total_patients', 0)}")
                    print(f"     Stops: {route.get('total_stops', 0)}")
                    
                    # Toon patiënten in deze route
                    stops = route.get('stops', [])
                    if stops:
                        print(f"     📍 Stops:")
                        for stop in stops:
                            patient_name = stop.get('patient_name', 'Onbekend')
                            stop_type = stop.get('type', 'Onbekend')
                            print(f"       - {patient_name} ({stop_type})")
                    
                    print()
            
            return routes
            
        except Exception as e:
            print(f"❌ Error in simple router: {e}")
            import traceback
            traceback.print_exc()
            return None
    else:
        print("❌ Geen patiënten met tijdblok toewijzing!")
        return None

if __name__ == "__main__":
    test_final_assignments()
    print(f"\n✅ Test voltooid!")
