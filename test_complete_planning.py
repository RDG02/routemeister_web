#!/usr/bin/env python
"""
Test complete planning flow en route opslag
"""
import os
import django
from datetime import datetime
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, Vehicle, TimeSlot, Location
from planning.services.simple_router import simple_route_service
from django.db import models

def test_complete_planning_flow():
    print("🔍 Complete Planning Flow Test")
    print("=" * 50)
    
    # Stap 1: Check data
    print("📊 Stap 1: Data Check")
    print("-" * 30)
    
    today = datetime.now().date()
    patients = Patient.objects.filter(ophaal_tijd__date=today)
    vehicles = Vehicle.objects.filter(status='beschikbaar')
    
    print(f"👥 Patiënten vandaag: {patients.count()}")
    print(f"🚗 Beschikbare voertuigen: {vehicles.count()}")
    
    # Stap 2: Tijdblok toewijzing
    print(f"\n📅 Stap 2: Tijdblok Toewijzing")
    print("-" * 30)
    
    # Check huidige toewijzing
    assigned_patients = patients.filter(
        models.Q(halen_tijdblok__isnull=False) | 
        models.Q(bringen_tijdblok__isnull=False)
    ).distinct()
    
    print(f"📊 Patiënten met tijdblok: {assigned_patients.count()}")
    
    if assigned_patients.count() == 0:
        print("🔄 Geen tijdblok toewijzing, toewijzen...")
        
        # Import en run tijdblok toewijzing
        try:
            from assign_timeslots_now import assign_timeslots
            assign_timeslots()
            print("✅ Tijdblokken toegewezen!")
            
            # Refresh patiënten
            assigned_patients = patients.filter(
                models.Q(halen_tijdblok__isnull=False) | 
                models.Q(bringen_tijdblok__isnull=False)
            ).distinct()
            print(f"📊 Patiënten met tijdblok na toewijzing: {assigned_patients.count()}")
            
        except Exception as e:
            print(f"❌ Error bij tijdblok toewijzing: {e}")
            return None
    
    # Stap 3: Route Planning
    print(f"\n🚀 Stap 3: Route Planning")
    print("-" * 30)
    
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
                        for stop in stops[:3]:  # Toon eerste 3
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
            print(f"❌ Error in route planning: {e}")
            import traceback
            traceback.print_exc()
            return None
    else:
        print("❌ Geen patiënten met tijdblok toewijzing!")
        return None

def test_session_simulation():
    """
    Simuleer session data zoals in de web app
    """
    print(f"\n💾 Session Data Simulation")
    print("-" * 30)
    
    routes = test_complete_planning_flow()
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
            
            # Test route_results view logica
            print(f"\n🔍 Route Results View Test")
            print("-" * 30)
            
            # Simuleer wat route_results zou doen
            if isinstance(routes, list):
                processed_routes = routes
            else:
                processed_routes = []
            
            print(f"   📊 Processed routes: {len(processed_routes)}")
            print(f"   📊 Total stops: {sum(route.get('total_stops', 0) for route in processed_routes)}")
            print(f"   📊 Total patients: {sum(route.get('total_patients', 0) for route in processed_routes)}")
            
            return True
    else:
        print("❌ Geen routes gegenereerd!")
        return False

def test_web_flow():
    """
    Test de complete web flow
    """
    print(f"\n🌐 Web Flow Test")
    print("-" * 30)
    
    print("1. 📁 CSV upload (routemeister_27062025 (19).csv)")
    print("2. 📅 Tijdblok toewijzing")
    print("3. 🚀 Route planning (Simple Router)")
    print("4. 📊 Resultaten opslag in session")
    print("5. 🌐 Redirect naar /planning/results/")
    
    success = test_session_simulation()
    
    if success:
        print(f"\n✅ Web flow zou moeten werken!")
        print(f"   Ga naar: http://localhost:8000/planning/new/")
        print(f"   Upload CSV, ga door de stappen, kies '⚡ Snelle Planner'")
        print(f"   Resultaten zouden moeten verschijnen op /planning/results/")
    else:
        print(f"\n❌ Web flow heeft problemen!")
        print(f"   Controleer de bovenstaande errors")

if __name__ == "__main__":
    test_web_flow()
    print(f"\n✅ Test voltooid!")
