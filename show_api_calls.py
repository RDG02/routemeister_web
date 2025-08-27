#!/usr/bin/env python
"""
Show exact API calls being made to OptaPlanner during planning
"""

import os
import django
import requests
import time

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, Vehicle, Location

def show_api_calls():
    print("🔍 Exact API Calls to OptaPlanner")
    print("=" * 50)
    
    # OptaPlanner base URL
    base_url = "http://localhost:8080"
    
    # Get test data
    vehicles = Vehicle.objects.all()[:2]  # First 2 vehicles
    patients = Patient.objects.filter(ophaal_tijd__date='2025-08-21')[:2]  # First 2 patients for today
    home_location = Location.get_home_location()
    
    print(f"🏠 Home Location: {home_location.name if home_location else 'None'}")
    print(f"🚗 Vehicles: {[v.kenteken for v in vehicles]}")
    print(f"👥 Patients: {[p.naam for p in patients]}")
    print()
    
    # Simulate the exact planning process
    print("🚀 SIMULATING PLANNING PROCESS")
    print("=" * 30)
    
    # Step 1: Clear
    print("1️⃣ CLEAR OPTAPLANNER")
    clear_url = f"{base_url}/api/clear"
    print(f"   GET {clear_url}")
    try:
        response = requests.get(clear_url, timeout=5)
        print(f"   → Status: {response.status_code}")
        print(f"   → Response: {response.text}")
    except Exception as e:
        print(f"   → Error: {e}")
    print()
    
    # Step 2: Clear Vehicles
    print("2️⃣ CLEAR VEHICLES")
    clear_vehicles_url = f"{base_url}/api/clearvehicle"
    print(f"   POST {clear_vehicles_url}")
    try:
        response = requests.post(clear_vehicles_url, timeout=5)
        print(f"   → Status: {response.status_code}")
        print(f"   → Response: {response.text}")
    except Exception as e:
        print(f"   → Error: {e}")
    print()
    
    # Step 3: Add Depot
    if home_location and home_location.latitude and home_location.longitude:
        print("3️⃣ ADD DEPOT")
        depot_url = f"{base_url}/api/locationadd/{home_location.name.replace(' ', '_')}/{home_location.longitude}/{home_location.latitude}/0/0/_/1"
        print(f"   GET {depot_url}")
        try:
            response = requests.get(depot_url, timeout=5)
            print(f"   → Status: {response.status_code}")
            print(f"   → Response: {response.text}")
        except Exception as e:
            print(f"   → Error: {e}")
        print()
    
    # Step 4: Add Vehicles
    print("4️⃣ ADD VEHICLES")
    for vehicle in vehicles:
        encoded_kenteken = vehicle.kenteken.replace(' ', '_').replace('-', '_')
        km_tarief_cents = int(float(vehicle.km_kosten_per_km) * 100)
        max_tijd_seconden = int(vehicle.maximale_rit_tijd * 3600) if vehicle.maximale_rit_tijd < 100 else int(vehicle.maximale_rit_tijd)
        
        vehicle_url = f"{base_url}/api/vehicleadd/{encoded_kenteken}/{vehicle.aantal_zitplaatsen}/{vehicle.speciale_zitplaatsen}/{km_tarief_cents}/{max_tijd_seconden}"
        print(f"   GET {vehicle_url}")
        try:
            response = requests.get(vehicle_url, timeout=5)
            print(f"   → Status: {response.status_code}")
            print(f"   → Response: {response.text}")
        except Exception as e:
            print(f"   → Error: {e}")
        print()
    
    # Step 5: Add Patients
    print("5️⃣ ADD PATIENTS")
    for patient in patients:
        if patient.latitude and patient.longitude:
            encoded_naam = patient.naam.replace(' ', '_').replace('-', '_').replace('.', '_')
            special_seating = "1" if patient.rolstoel else "0"
            pickup_type = "1"  # Always pickup for halen time slots
            
            location_url = f"{base_url}/api/locationadd/{encoded_naam}/{patient.longitude}/{patient.latitude}/{special_seating}/0/_/{pickup_type}"
            print(f"   GET {location_url}")
            try:
                response = requests.get(location_url, timeout=5)
                print(f"   → Status: {response.status_code}")
                print(f"   → Response: {response.text}")
            except Exception as e:
                print(f"   → Error: {e}")
            print()
    
    # Step 6: Get Route
    print("6️⃣ GET ROUTE")
    route_url = f"{base_url}/api/route"
    print(f"   GET {route_url}")
    try:
        response = requests.get(route_url, timeout=10)
        print(f"   → Status: {response.status_code}")
        print(f"   → Response: {response.text}")
    except Exception as e:
        print(f"   → Error: {e}")
    print()

if __name__ == "__main__":
    show_api_calls()
