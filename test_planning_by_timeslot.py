#!/usr/bin/env python
import os
import sys
import django
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, Vehicle, TimeSlot, Location
from planning.services.optaplanner import optaplanner_service
from django.db import models
import requests

def test_planning_by_timeslot():
    print("=== STARTING PLANNING BY TIMESLOT TEST ===")
    
    # Step 1: Check data
    print("\n1. Checking data...")
    patients = Patient.objects.filter(status='nieuw')
    vehicles = Vehicle.objects.filter(status='beschikbaar')
    
    print(f"   - Patients: {patients.count()}")
    print(f"   - Vehicles: {vehicles.count()}")
    
    # Get patients with time slots
    patients_with_timeslots = patients.filter(
        models.Q(halen_tijdblok__isnull=False) | 
        models.Q(bringen_tijdblok__isnull=False)
    ).distinct()
    print(f"   - Patients with time slots: {patients_with_timeslots.count()}")
    
    if patients_with_timeslots.count() == 0:
        print("   - WARNING: No patients have time slots assigned!")
        return
    
    # Step 2: Get home location
    print("\n2. Getting home location...")
    home_location = Location.get_home_location()
    if not home_location:
        print("   - No home location found!")
        return
    print(f"   - Home location: {home_location.name}")
    
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
    
    # Step 6: Group patients by halen time slot
    print("\n6. Grouping patients by halen time slot...")
    patients_by_halen = {}
    for patient in patients_with_timeslots:
        if patient.halen_tijdblok:
            timeslot_name = patient.halen_tijdblok.naam
            if timeslot_name not in patients_by_halen:
                patients_by_halen[timeslot_name] = []
            patients_by_halen[timeslot_name].append(patient)
    
    print(f"   - Found {len(patients_by_halen)} halen time slots:")
    for timeslot_name, patients_list in patients_by_halen.items():
        print(f"     📥 {timeslot_name}: {len(patients_list)} patients")
        for p in patients_list:
            print(f"       - {p.naam} (pickup: {p.ophaal_tijd.time()})")
    
    # Step 7: Send patients per time slot
    print("\n7. Sending patients per time slot...")
    total_patients_added = 0
    
    for timeslot_name, patients_list in patients_by_halen.items():
        print(f"\n   🚀 Processing {timeslot_name} ({len(patients_list)} patients)...")
        
        # Add patients for this time slot
        patients_added = 0
        for patient in patients_list:
            if patient.latitude and patient.longitude:
                try:
                    pickup_type = "1" if patient.halen_tijdblok else "0"
                    encoded_naam = patient.naam.replace(' ', '_').replace('-', '_').replace('.', '_')
                    special_seating = "1" if patient.rolstoel else "0"
                    
                    location_url = f"{optaplanner_service.base_url}/api/locationadd/{encoded_naam}/{patient.longitude}/{patient.latitude}/{special_seating}/0/_/{pickup_type}"
                    location_response = requests.get(location_url, timeout=5)
                    print(f"     ✅ {patient.naam} added: {location_response.status_code}")
                    if location_response.status_code == 200:
                        patients_added += 1
                except Exception as e:
                    print(f"     ❌ {patient.naam} error: {e}")
        
        total_patients_added += patients_added
        print(f"     📊 Added {patients_added}/{len(patients_list)} patients for {timeslot_name}")
        
        # Wait a moment and check routes for this time slot
        print(f"     ⏳ Waiting 3 seconds for OptaPlanner to process...")
        time.sleep(3)
        
        # Check routes
        try:
            route_response = requests.get(f"{optaplanner_service.base_url}/api/route", timeout=10)
            if route_response.status_code == 200:
                route_data = route_response.json()
                total_locations = sum(len(route.get('locations', [])) for route in route_data.get('routes', []))
                print(f"     📍 Routes now have {total_locations} total locations")
            else:
                print(f"     ❌ Route check failed: {route_response.status_code}")
        except Exception as e:
            print(f"     ❌ Route check error: {e}")
    
    print(f"\n   - Total patients added: {total_patients_added}")
    
    # Step 8: Final route check
    print("\n8. Final route check...")
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
    test_planning_by_timeslot()
