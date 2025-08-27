#!/usr/bin/env python
"""
Debug script to show exactly what API calls are being made to OptaPlanner
"""

import os
import django
import requests
import time

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, Vehicle, Location

def debug_optaplanner_calls():
    print("🔍 Debug OptaPlanner API Calls")
    print("=" * 50)
    
    # OptaPlanner base URL
    base_url = "http://localhost:8080"
    
    # Get test data
    vehicles = Vehicle.objects.all()[:3]  # First 3 vehicles
    patients = Patient.objects.filter(ophaal_tijd__date='2025-08-21')[:3]  # First 3 patients for today
    home_location = Location.get_home_location()
    
    print(f"🏠 Home Location: {home_location.name if home_location else 'None'}")
    print(f"🚗 Vehicles to test: {vehicles.count()}")
    print(f"👥 Patients to test: {patients.count()}")
    print()
    
    # Test 1: Clear
    print("🔄 TEST 1: Clear OptaPlanner")
    clear_url = f"{base_url}/api/clear"
    print(f"   URL: {clear_url}")
    try:
        response = requests.get(clear_url, timeout=5)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:100]}...")
    except Exception as e:
        print(f"   Error: {e}")
    print()
    
    # Test 2: Clear Vehicles
    print("🔄 TEST 2: Clear Vehicles")
    clear_vehicles_url = f"{base_url}/api/clearvehicle"
    print(f"   URL: {clear_vehicles_url}")
    try:
        response = requests.post(clear_vehicles_url, timeout=5)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:100]}...")
    except Exception as e:
        print(f"   Error: {e}")
    print()
    
    # Test 3: Add Depot
    if home_location and home_location.latitude and home_location.longitude:
        print("🏠 TEST 3: Add Depot")
        depot_url = f"{base_url}/api/locationadd/{home_location.name.replace(' ', '_')}/{home_location.longitude}/{home_location.latitude}/0/0/_/1"
        print(f"   URL: {depot_url}")
        try:
            response = requests.get(depot_url, timeout=5)
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:100]}...")
        except Exception as e:
            print(f"   Error: {e}")
        print()
    
    # Test 4: Add Vehicles
    print("🚗 TEST 4: Add Vehicles")
    for vehicle in vehicles:
        encoded_kenteken = vehicle.kenteken.replace(' ', '_').replace('-', '_')
        km_tarief_cents = int(float(vehicle.km_kosten_per_km) * 100)
        max_tijd_seconden = int(vehicle.maximale_rit_tijd * 3600) if vehicle.maximale_rit_tijd < 100 else int(vehicle.maximale_rit_tijd)
        
        vehicle_url = f"{base_url}/api/vehicleadd/{encoded_kenteken}/{vehicle.aantal_zitplaatsen}/{vehicle.speciale_zitplaatsen}/{km_tarief_cents}/{max_tijd_seconden}"
        print(f"   Vehicle: {vehicle.kenteken}")
        print(f"   URL: {vehicle_url}")
        try:
            response = requests.get(vehicle_url, timeout=5)
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:100]}...")
        except Exception as e:
            print(f"   Error: {e}")
        print()
    
    # Test 5: Add Patients
    print("👥 TEST 5: Add Patients")
    for patient in patients:
        if patient.latitude and patient.longitude:
            encoded_naam = patient.naam.replace(' ', '_').replace('-', '_').replace('.', '_')
            special_seating = "1" if patient.rolstoel else "0"
            pickup_type = "1"  # Always pickup for halen time slots
            
            location_url = f"{base_url}/api/locationadd/{encoded_naam}/{patient.longitude}/{patient.latitude}/{special_seating}/0/_/{pickup_type}"
            print(f"   Patient: {patient.naam}")
            print(f"   URL: {location_url}")
            try:
                response = requests.get(location_url, timeout=5)
                print(f"   Status: {response.status_code}")
                print(f"   Response: {response.text[:100]}...")
            except Exception as e:
                print(f"   Error: {e}")
            print()
    
    # Test 6: Get Route
    print("🛣️  TEST 6: Get Route")
    route_url = f"{base_url}/api/route"
    print(f"   URL: {route_url}")
    try:
        response = requests.get(route_url, timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}...")
    except Exception as e:
        print(f"   Error: {e}")
    print()

if __name__ == "__main__":
    debug_optaplanner_calls()
