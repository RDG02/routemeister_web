#!/usr/bin/env python
"""
Debug script voor complete planning flow met CSV bestand
"""
import os
import django
from datetime import datetime
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, Vehicle, TimeSlot, Location
from planning.services.simple_router import simple_route_service
from django.db import models

def debug_complete_flow():
    print("🔍 Complete Planning Flow Debug")
    print("=" * 50)
    
    # Stap 1: Check CSV bestand
    print("📁 Stap 1: CSV Bestand Check")
    print("-" * 30)
    
    csv_file = "routemeister_27062025 (19).csv"
    if os.path.exists(csv_file):
        print(f"✅ CSV bestand gevonden: {csv_file}")
        with open(csv_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print(f"   📊 Aantal regels: {len(lines)}")
            if len(lines) > 1:
                print(f"   📋 Eerste regel: {lines[0].strip()}")
                print(f"   📋 Tweede regel: {lines[1].strip()}")
    else:
        print(f"❌ CSV bestand niet gevonden: {csv_file}")
        return
    
    # Stap 2: Check huidige patiënten
    print(f"\n👥 Stap 2: Huidige Patiënten")
    print("-" * 30)
    
    today = datetime.now().date()
    patients = Patient.objects.filter(ophaal_tijd__date=today)
    
    print(f"📊 Patiënten vandaag: {patients.count()}")
    
    # Groep patiënten per tijdblok
    halen_groups = {}
    brengen_groups = {}
    
    for patient in patients:
        if patient.halen_tijdblok:
            halen_name = patient.halen_tijdblok.naam
            if halen_name not in halen_groups:
                halen_groups[halen_name] = []
            halen_groups[halen_name].append(patient)
        
        if patient.bringen_tijdblok:
            brengen_name = patient.bringen_tijdblok.naam
            if brengen_name not in brengen_groups:
                brengen_groups[brengen_name] = []
            brengen_groups[brengen_name].append(patient)
    
    print(f"\n🚗 Halen Tijdblokken:")
    for halen_name, patient_list in halen_groups.items():
        print(f"   {halen_name}: {len(patient_list)} patiënten")
        for p in patient_list[:3]:  # Toon eerste 3
            print(f"     - {p.naam} ({p.ophaal_tijd.strftime('%H:%M') if p.ophaal_tijd else 'Geen tijd'})")
    
    print(f"\n🏠 Brengen Tijdblokken:")
    for brengen_name, patient_list in brengen_groups.items():
        print(f"   {brengen_name}: {len(patient_list)} patiënten")
        for p in patient_list[:3]:  # Toon eerste 3
            print(f"     - {p.naam} ({p.eind_behandel_tijd.strftime('%H:%M') if p.eind_behandel_tijd else 'Geen tijd'})")
    
    # Stap 3: Check voertuigen
    print(f"\n🚗 Stap 3: Voertuigen Check")
    print("-" * 30)
    
    vehicles = Vehicle.objects.filter(status='beschikbaar')
    print(f"📊 Beschikbare voertuigen: {vehicles.count()}")
    for v in vehicles:
        print(f"   - {v.kenteken} (capaciteit: {v.aantal_zitplaatsen})")
    
    # Stap 4: Test Simple Router
    print(f"\n🚀 Stap 4: Simple Router Test")
    print("-" * 30)
    
    assigned_patients = patients.filter(
        models.Q(halen_tijdblok__isnull=False) | 
        models.Q(bringen_tijdblok__isnull=False)
    ).distinct()
    
    print(f"📊 Patiënten met tijdblok: {assigned_patients.count()}")
    print(f"📊 Patiënten zonder tijdblok: {patients.count() - assigned_patients.count()}")
    
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
                        for stop in stops[:5]:  # Toon eerste 5
                            patient_name = stop.get('patient_name', 'Onbekend')
                            stop_type = stop.get('type', 'Onbekend')
                            print(f"       - {patient_name} ({stop_type})")
                    
                    constraints = route.get('constraints', {})
                    if constraints:
                        print(f"     ✅ Hard constraints valid: {constraints.get('hard_constraints_valid', False)}")
                        print(f"     🎯 Soft score: {constraints.get('soft_constraints_score', 0):.1f}")
                    
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

def test_session_data():
    """
    Test wat er in de session zou moeten staan
    """
    print(f"\n💾 Session Data Test")
    print("-" * 30)
    
    routes = debug_complete_flow()
    if routes:
        print(f"📦 Routes voor session: {len(routes)} routes")
        print(f"   Session key: 'planned_routes'")
        print(f"   Data type: {type(routes)}")
        
        if routes:
            print(f"   Eerste route keys: {list(routes[0].keys())}")
            
            # Test of routes correct zijn voor template
            total_stops = sum(route.get('total_stops', 0) for route in routes)
            total_patients = sum(route.get('total_patients', 0) for route in routes)
            
            print(f"   📊 Total stops: {total_stops}")
            print(f"   📊 Total patients: {total_patients}")
            
            # Check of routes per tijdblok zijn
            timeslot_routes = {}
            for route in routes:
                timeslot = route.get('timeslot_name', 'Onbekend')
                if timeslot not in timeslot_routes:
                    timeslot_routes[timeslot] = []
                timeslot_routes[timeslot].append(route)
            
            print(f"   📅 Routes per tijdblok:")
            for timeslot, route_list in timeslot_routes.items():
                print(f"     {timeslot}: {len(route_list)} routes")

if __name__ == "__main__":
    test_session_data()
    print(f"\n✅ Debug voltooid!")
