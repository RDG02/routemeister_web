#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, Vehicle, TimeSlot, Location
from planning.services.optaplanner import optaplanner_service
from django.db import models
import requests

def test_planning():
    print("=== STARTING MANUAL PLANNING TEST ===")
    
    # Step 1: Check data
    print("\n1. Checking data...")
    patients = Patient.objects.filter(status='nieuw')
    vehicles = Vehicle.objects.filter(status='beschikbaar')
    timeslots = TimeSlot.objects.filter(actief=True)
    
    print(f"   - Patients: {patients.count()}")
    print(f"   - Vehicles: {vehicles.count()}")
    print(f"   - TimeSlots: {timeslots.count()}")
    print(f"   - Patients with coords: {patients.filter(latitude__isnull=False).count()}")
    
    # Filter patients with time slots
    patients_with_timeslots = patients.filter(
        django.db.models.Q(halen_tijdblok__isnull=False) | 
        django.db.models.Q(bringen_tijdblok__isnull=False)
    ).distinct()
    print(f"   - Patients with time slots: {patients_with_timeslots.count()}")
    
    if patients_with_timeslots.count() == 0:
        print("   - WARNING: No patients have time slots assigned!")
        print("   - This is why OptaPlanner returns 0 locations")
        return
    
    # Step 2: Get home location
    print("\n2. Getting home location...")
    home_location = Location.get_home_location()
    if home_location:
        print(f"   - Home location: {home_location.name}")
        print(f"   - Coordinates: {home_location.latitude}, {home_location.longitude}")
    else:
        print("   - No home location found!")
        return
    
    # Step 3: Clear OptaPlanner
    print("\n3. Clearing OptaPlanner...")
    try:
        clear_response = requests.get(f"{optaplanner_service.base_url}/api/clear", timeout=5)
        print(f"   - Clear response: {clear_response.status_code}")
        
        clear_vehicles_response = requests.post(f"{optaplanner_service.base_url}/api/clearvehicle", timeout=5)
        print(f"   - Clear vehicles response: {clear_vehicles_response.status_code}")
    except Exception as e:
        print(f"   - Clear error: {e}")
        return
    
    # Step 4: Add depot FIRST
    print("\n4. Adding depot...")
    try:
        depot_url = f"{optaplanner_service.base_url}/api/locationadd/{home_location.name.replace(' ', '_')}/{home_location.longitude}/{home_location.latitude}/0/0/_/1"
        depot_response = requests.get(depot_url, timeout=5)
        print(f"   - Depot {home_location.name} added: {depot_response.status_code}")
        if depot_response.status_code != 200:
            print(f"   - Depot error response: {depot_response.text}")
    except Exception as e:
        print(f"   - Depot error: {e}")
        return
    
    # Step 5: Add vehicles
    print("\n5. Adding vehicles...")
    vehicles_added = 0
    for vehicle in vehicles:
        try:
            encoded_kenteken = vehicle.kenteken.replace(' ', '_').replace('-', '_')
            km_tarief_cents = int(float(vehicle.km_kosten_per_km) * 100)
            max_tijd_seconden = int(vehicle.maximale_rit_tijd * 3600) if vehicle.maximale_rit_tijd < 100 else int(vehicle.maximale_rit_tijd)
            
            vehicle_url = f"{optaplanner_service.base_url}/api/vehicleadd/{encoded_kenteken}/{vehicle.aantal_zitplaatsen}/{vehicle.speciale_zitplaatsen}/{km_tarief_cents}/{max_tijd_seconden}"
            vehicle_response = requests.get(vehicle_url, timeout=5)
            print(f"   - Vehicle {vehicle.kenteken} added: {vehicle_response.status_code}")
            if vehicle_response.status_code == 200:
                vehicles_added += 1
        except Exception as e:
            print(f"   - Vehicle {vehicle.kenteken} error: {e}")
    
    # Step 6: Add patients WITH TIME SLOTS
    print("\n6. Adding patients with time slots...")
    patients_added = 0
    for patient in patients_with_timeslots:
        if patient.latitude and patient.longitude:
            try:
                pickup_type = "1" if patient.halen_tijdblok else "0"
                encoded_naam = patient.naam.replace(' ', '_').replace('-', '_').replace('.', '_')
                special_seating = "1" if patient.rolstoel else "0"
                
                location_url = f"{optaplanner_service.base_url}/api/locationadd/{encoded_naam}/{patient.longitude}/{patient.latitude}/{special_seating}/0/_/{pickup_type}"
                location_response = requests.get(location_url, timeout=5)
                print(f"   - Patient {patient.naam} added: {location_response.status_code} (lat: {patient.latitude}, lon: {patient.longitude})")
                if location_response.status_code == 200:
                    patients_added += 1
            except Exception as e:
                print(f"   - Patient {patient.naam} error: {e}")
        else:
            print(f"   - Patient {patient.naam} has no coordinates!")
    
    print(f"\n   - Total vehicles added: {vehicles_added}/{vehicles.count()}")
    print(f"   - Total patients added: {patients_added}/{patients_with_timeslots.count()}")
    
    # Step 7: Get routes
    print("\n7. Getting routes...")
    try:
        route_response = requests.get(f"{optaplanner_service.base_url}/api/route", timeout=10)
        print(f"   - Route response: {route_response.status_code}")
        if route_response.status_code == 200:
            route_data = route_response.json()
            print(f"   - Vehicle count: {route_data.get('vehicleCount', 0)}")
            print(f"   - Routes: {len(route_data.get('routes', []))}")
            
            # Check locations per route
            total_locations = 0
            for route in route_data.get('routes', []):
                locations = route.get('locations', [])
                total_locations += len(locations)
                print(f"   - Route {route.get('vehicle', {}).get('name', 'Unknown')}: {len(locations)} locations")
            
            print(f"   - Total locations: {total_locations}")
            print(f"   - Distance: {route_data.get('distance', 'Unknown')}")
            print(f"   - Score: {route_data.get('score', {})}")
        else:
            print(f"   - Route error: {route_response.text}")
    except Exception as e:
        print(f"   - Route error: {e}")
    
    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    test_planning()
