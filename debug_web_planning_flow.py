#!/usr/bin/env python
"""
Debug web planning flow - waarom maar 1 route in plaats van 6?
"""
import os
import django
from datetime import datetime
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, Vehicle, TimeSlot, Location
from planning.services.simple_router import simple_route_service
from django.db import models

def debug_web_planning_flow():
    print("🔍 Web Planning Flow Debug")
    print("=" * 50)
    
    # Stap 1: Check huidige patiënten en tijdblok toewijzing
    print("📊 Stap 1: Patiënten en Tijdblok Toewijzing")
    print("-" * 40)
    
    today = datetime.now().date()
    patients = Patient.objects.filter(ophaal_tijd__date=today)
    
    print(f"👥 Patiënten vandaag: {patients.count()}")
    
    # Check tijdblok toewijzing per patiënt
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
        for p in patient_list:
            print(f"     - {p.naam} ({p.ophaal_tijd.strftime('%H:%M') if p.ophaal_tijd else 'Geen tijd'})")
    
    print(f"\n🏠 Brengen Tijdblokken:")
    for brengen_name, patient_list in brengen_groups.items():
        print(f"   {brengen_name}: {len(patient_list)} patiënten")
        for p in patient_list:
            print(f"     - {p.naam} ({p.eind_behandel_tijd.strftime('%H:%M') if p.eind_behandel_tijd else 'Geen tijd'})")
    
    # Stap 2: Test Simple Router met huidige data
    print(f"\n🚀 Stap 2: Simple Router Test")
    print("-" * 40)
    
    vehicles = Vehicle.objects.filter(status='beschikbaar')
    assigned_patients = patients.filter(
        models.Q(halen_tijdblok__isnull=False) | 
        models.Q(bringen_tijdblok__isnull=False)
    ).distinct()
    
    print(f"📊 Beschikbare voertuigen: {vehicles.count()}")
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

def analyze_simple_router_logic():
    """
    Analyseer de Simple Router logica
    """
    print(f"\n🔍 Stap 3: Simple Router Logica Analyse")
    print("-" * 40)
    
    # Import en analyseer de simple router
    from planning.services.simple_router import SimpleRouteService
    
    today = datetime.now().date()
    patients = Patient.objects.filter(ophaal_tijd__date=today)
    vehicles = Vehicle.objects.filter(status='beschikbaar')
    
    assigned_patients = patients.filter(
        models.Q(halen_tijdblok__isnull=False) | 
        models.Q(bringen_tijdblok__isnull=False)
    ).distinct()
    
    print(f"📊 Input voor Simple Router:")
    print(f"   - Voertuigen: {vehicles.count()}")
    print(f"   - Patiënten: {assigned_patients.count()}")
    
    # Groep patiënten per tijdblok
    patients_by_timeslot = {}
    for patient in assigned_patients:
        if patient.halen_tijdblok:
            timeslot_name = patient.halen_tijdblok.naam
            if timeslot_name not in patients_by_timeslot:
                patients_by_timeslot[timeslot_name] = []
            patients_by_timeslot[timeslot_name].append(patient)
        
        if patient.bringen_tijdblok:
            timeslot_name = patient.bringen_tijdblok.naam
            if timeslot_name not in patients_by_timeslot:
                patients_by_timeslot[timeslot_name] = []
            patients_by_timeslot[timeslot_name].append(patient)
    
    print(f"\n📅 Patiënten per tijdblok:")
    for timeslot_name, patient_list in patients_by_timeslot.items():
        print(f"   {timeslot_name}: {len(patient_list)} patiënten")
        for p in patient_list:
            print(f"     - {p.naam}")
    
    # Test distribute_patients_over_vehicles functie
    print(f"\n🔍 Test distribute_patients_over_vehicles:")
    
    router = SimpleRouteService()
    
    # Simuleer wat distribute_patients_over_vehicles doet
    print(f"   📊 Voertuigen beschikbaar: {vehicles.count()}")
    print(f"   📊 Patiënten totaal: {assigned_patients.count()}")
    
    # Check of er genoeg voertuigen zijn
    if vehicles.count() >= len(patients_by_timeslot):
        print(f"   ✅ Genoeg voertuigen voor alle tijdblokken")
    else:
        print(f"   ⚠️ Niet genoeg voertuigen! {vehicles.count()} voertuigen voor {len(patients_by_timeslot)} tijdblokken")
    
    # Check patiënten per tijdblok
    for timeslot_name, patient_list in patients_by_timeslot.items():
        print(f"   📅 {timeslot_name}: {len(patient_list)} patiënten")
        if len(patient_list) == 0:
            print(f"     ⚠️ Geen patiënten in dit tijdblok!")

def test_web_session_simulation():
    """
    Simuleer wat er in de web session gebeurt
    """
    print(f"\n💾 Stap 4: Web Session Simulatie")
    print("-" * 40)
    
    routes = debug_web_planning_flow()
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
            
            # Vergelijk met verwachting
            expected_routes = len(timeslot_routes)
            actual_routes = len(routes)
            
            print(f"\n🔍 Vergelijking:")
            print(f"   Verwachtte routes: {expected_routes}")
            print(f"   Werkelijke routes: {actual_routes}")
            
            if actual_routes < expected_routes:
                print(f"   ❌ Minder routes dan verwacht!")
                print(f"   Mogelijke oorzaken:")
                print(f"     - Simple Router combineert tijdblokken")
                print(f"     - Niet genoeg voertuigen beschikbaar")
                print(f"     - Patiënten worden gefilterd")
            else:
                print(f"   ✅ Aantal routes klopt")
    
    analyze_simple_router_logic()

if __name__ == "__main__":
    test_web_session_simulation()
    print(f"\n✅ Debug voltooid!")
