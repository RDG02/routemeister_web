#!/usr/bin/env python
"""
Test script voor OptaPlanner-style constraints in de snelle planner
"""
import os
import django
from datetime import datetime, time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, Vehicle, TimeSlot, Location
from planning.services.simple_router import simple_route_service

def test_constraints():
    print("🧪 Testing OptaPlanner-style Constraints")
    print("=" * 50)
    
    # Haal test data op
    vehicles = Vehicle.objects.all()[:3]
    patients = Patient.objects.filter(ophaal_tijd__date='2025-08-21')[:5]
    home_location = Location.get_home_location()
    
    print(f"🚗 Vehicles: {[v.kenteken for v in vehicles]}")
    print(f"👥 Patients: {[p.naam for p in patients]}")
    print(f"🏠 Home: {home_location.name if home_location else 'None'}")
    print()
    
    # Test constraint validatie
    print("🔍 Testing Hard Constraints:")
    print("-" * 30)
    
    for vehicle in vehicles:
        print(f"\nVoertuig: {vehicle.kenteken}")
        print(f"  Capaciteit: {vehicle.aantal_zitplaatsen}")
        print(f"  Rolstoel plaatsen: {vehicle.speciale_zitplaatsen}")
        print(f"  Max reistijd: {vehicle.maximale_rit_tijd} uur")
        print(f"  Status: {vehicle.status}")
        
        # Test met alle patiënten
        test_route = {
            'stops': [],
            'vehicle': vehicle,
            'patients': list(patients)
        }
        
        is_valid, violations = simple_route_service.validate_hard_constraints(
            test_route, vehicle, list(patients)
        )
        
        print(f"  ✅ Valid: {is_valid}")
        if violations:
            print(f"  ❌ Violations:")
            for violation in violations:
                print(f"    - {violation}")
        print()
    
    # Test soft constraints
    print("🎯 Testing Soft Constraints:")
    print("-" * 30)
    
    for vehicle in vehicles[:2]:  # Test eerste 2 voertuigen
        print(f"\nVoertuig: {vehicle.kenteken}")
        
        # Test met verschillende patiënt groepen
        for i in range(1, min(4, len(patients) + 1)):
            patient_group = list(patients[:i])
            
            test_route = {
                'stops': [],
                'vehicle': vehicle,
                'patients': patient_group
            }
            
            score, breakdown = simple_route_service.calculate_soft_constraints_score(
                test_route, vehicle, patient_group
            )
            
            print(f"  {len(patient_group)} patiënten: score={score:.1f}")
            print(f"    Breakdown: {breakdown}")
        print()
    
    # Test complete route planning
    print("🚀 Testing Complete Route Planning:")
    print("-" * 40)
    
    try:
        routes = simple_route_service.plan_simple_routes(vehicles, patients)
        print(f"✅ {len(routes)} routes gegenereerd")
        
        for i, route in enumerate(routes[:3]):  # Toon eerste 3 routes
            print(f"\nRoute {i+1}: {route.get('vehicle_name', 'Onbekend')}")
            print(f"  Type: {route.get('route_type', 'Onbekend')}")
            print(f"  Patiënten: {route.get('total_patients', 0)}")
            print(f"  Stops: {route.get('total_stops', 0)}")
            
            constraints = route.get('constraints', {})
            if constraints:
                print(f"  ✅ Hard constraints valid: {constraints.get('hard_constraints_valid', False)}")
                print(f"  🎯 Soft score: {constraints.get('soft_constraints_score', 0):.1f}")
                
                violations = constraints.get('hard_constraint_violations', [])
                if violations:
                    print(f"  ❌ Violations: {len(violations)}")
                    for violation in violations[:2]:  # Toon eerste 2
                        print(f"    - {violation}")
                
                breakdown = constraints.get('soft_constraints_breakdown', {})
                if breakdown:
                    print(f"  📊 Score breakdown:")
                    for key, value in breakdown.items():
                        if key != 'total_score':
                            print(f"    {key}: {value:.1f}")
        
        print(f"\n🎉 Constraint test voltooid!")
        
    except Exception as e:
        print(f"❌ Error in route planning: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_constraints()
