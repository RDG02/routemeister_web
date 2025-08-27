#!/usr/bin/env python
"""
Test script voor snelle planner in web interface
"""
import os
import django
from datetime import datetime, time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, Vehicle, TimeSlot, Location
from planning.services.simple_router import simple_route_service

def test_simple_planner_web():
    print("🌐 Testing Snelle Planner Web Interface")
    print("=" * 50)
    
    # Haal test data op
    vehicles = Vehicle.objects.all()[:3]
    patients = Patient.objects.filter(ophaal_tijd__date='2025-08-21')[:5]
    home_location = Location.get_home_location()
    
    print(f"🚗 Vehicles: {[v.kenteken for v in vehicles]}")
    print(f"👥 Patients: {[p.naam for p in patients]}")
    print(f"🏠 Home: {home_location.name if home_location else 'None'}")
    print()
    
    # Test complete route planning
    print("🚀 Testing Complete Route Planning:")
    print("-" * 40)
    
    try:
        routes = simple_route_service.plan_simple_routes(vehicles, patients)
        print(f"✅ {len(routes)} routes gegenereerd")
        
        # Simuleer web interface output
        print("\n📋 Web Interface Output:")
        print("=" * 30)
        
        for i, route in enumerate(routes[:3]):  # Toon eerste 3 routes
            print(f"\n🚗 Route {i+1}: {route.get('vehicle_name', 'Onbekend')}")
            print(f"   Type: {route.get('route_type', 'Onbekend')}")
            print(f"   Tijdblok: {route.get('timeslot_name', 'Onbekend')}")
            print(f"   Start: {route.get('start_time', 'Onbekend')} - Eind: {route.get('end_time', 'Onbekend')}")
            print(f"   Patiënten: {route.get('total_patients', 0)}")
            print(f"   Stops: {route.get('total_stops', 0)}")
            print(f"   Geschatte duur: {route.get('estimated_duration', 0)} minuten")
            
            # Constraint informatie
            constraints = route.get('constraints', {})
            if constraints:
                print(f"   ✅ Hard constraints: {'Valid' if constraints.get('hard_constraints_valid', False) else 'Invalid'}")
                print(f"   🎯 Optimalisatie score: {constraints.get('soft_constraints_score', 0):.1f}")
                
                violations = constraints.get('hard_constraint_violations', [])
                if violations:
                    print(f"   ❌ Violations: {len(violations)}")
                    for violation in violations[:2]:  # Toon eerste 2
                        print(f"     - {violation}")
            
            # Stops informatie
            stops = route.get('stops', [])
            print(f"   📍 Stops:")
            for stop in stops:
                stop_type = stop.get('type', 'Unknown')
                patient_name = stop.get('patient_name', 'Unknown')
                estimated_time = stop.get('estimated_time', 'Unknown')
                address = stop.get('address', 'Unknown')
                
                if stop_type == 'PICKUP':
                    print(f"     🚗 Ophalen: {patient_name} ({estimated_time})")
                elif stop_type == 'DROPOFF':
                    print(f"     🏠 Afzetten: {patient_name} ({estimated_time})")
                elif stop_type == 'ORIGIN':
                    print(f"     🏥 Vertrek: {patient_name} ({estimated_time})")
                elif stop_type == 'DESTINATION':
                    print(f"     🏥 Aankomst: {patient_name} ({estimated_time})")
                
                # Geocoding waarschuwingen
                geocoding_warning = stop.get('geocoding_warning')
                if geocoding_warning:
                    print(f"       ⚠️ {geocoding_warning}")
        
        print(f"\n🎉 Snelle planner test voltooid!")
        print(f"📊 Totaal routes: {len(routes)}")
        
        # Statistieken
        valid_routes = sum(1 for r in routes if r.get('constraints', {}).get('hard_constraints_valid', False))
        print(f"✅ Geldige routes: {valid_routes}")
        print(f"❌ Ongeldige routes: {len(routes) - valid_routes}")
        
        if routes:
            avg_score = sum(r.get('constraints', {}).get('soft_constraints_score', 0) for r in routes) / len(routes)
            print(f"🎯 Gemiddelde optimalisatie score: {avg_score:.1f}")
        
    except Exception as e:
        print(f"❌ Error in route planning: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_planner_web()
