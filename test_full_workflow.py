#!/usr/bin/env python
"""
Test full workflow from CSV upload to planning
"""

import os
import django
import requests
import time

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, Vehicle, Location, TimeSlot
from planning.services.optaplanner import OptaPlannerService

def test_full_workflow():
    print("🔍 Test Full Workflow")
    print("=" * 50)
    
    # Initialize OptaPlanner service
    optaplanner_service = OptaPlannerService()
    print(f"📍 OptaPlanner URL: {optaplanner_service.base_url}")
    print()
    
    # STEP 1: Check current state
    print("🚀 STEP 1: Current state check...")
    vehicles = Vehicle.objects.all()
    patients = Patient.objects.filter(status='nieuw')
    print(f"   📊 Voertuigen: {vehicles.count()}")
    print(f"   📊 CSV patiënten: {patients.count()}")
    
    # Check if patients have time slots
    patients_with_timeslots = patients.filter(halen_tijdblok__isnull=False)
    print(f"   📊 Patiënten met tijdblokken: {patients_with_timeslots.count()}")
    
    if patients_with_timeslots.count() == 0:
        print("   ⚠️  Geen patiënten met tijdblokken! Tijdblokken toewijzen...")
        # Import and run time slot assignment
        from assign_timeslots_now import assign_timeslots
        assign_timeslots()
        print("   ✅ Tijdblokken toegewezen!")
    
    print()
    
    # STEP 2: Simulate session data (what the web app would do)
    print("🚀 STEP 2: Simulate session data...")
    selected_vehicles = list(vehicles.values_list('id', flat=True))
    selected_timeslots = list(TimeSlot.objects.filter(actief=True).values_list('id', flat=True))
    
    print(f"   📊 Geselecteerde voertuigen: {len(selected_vehicles)}")
    print(f"   📊 Geselecteerde tijdblokken: {len(selected_timeslots)}")
    print()
    
    # STEP 3: Clear OptaPlanner
    print("🚀 STEP 3: OptaPlanner resetten...")
    try:
        clear_response = requests.get(f"{optaplanner_service.base_url}/api/clear", timeout=5)
        print(f"   📡 Clear response: {clear_response.status_code} - {clear_response.text}")
        
        clear_vehicles_response = requests.post(f"{optaplanner_service.base_url}/api/clearvehicle", timeout=5)
        print(f"   📡 Clear vehicles response: {clear_vehicles_response.status_code} - {clear_vehicles_response.text}")
    except Exception as e:
        print(f"   ❌ Clear error: {e}")
    print()
    
    # STEP 4: Add depot
    print("🚀 STEP 4: Home locatie toevoegen...")
    try:
        home_location = Location.get_home_location()
        if home_location and home_location.latitude and home_location.longitude:
            depot_url = f"{optaplanner_service.base_url}/api/locationadd/{home_location.name.replace(' ', '_')}/{home_location.longitude}/{home_location.latitude}/0/0/_/1"
            print(f"   📡 Depot URL: {depot_url}")
            
            depot_response = requests.get(depot_url, timeout=5)
            print(f"   📡 Depot response: {depot_response.status_code} - {depot_response.text}")
        else:
            print("   ⚠️  Geen home locatie gevonden!")
    except Exception as e:
        print(f"   ❌ Depot error: {e}")
    print()
    
    # STEP 5: Add vehicles
    print("🚀 STEP 5: Voertuigen toevoegen...")
    vehicles_added = 0
    for vehicle in vehicles:
        try:
            # URL encode kenteken
            encoded_kenteken = vehicle.kenteken.replace(' ', '_').replace('-', '_')
            # Convert km rate to cents
            km_tarief_cents = int(float(vehicle.km_kosten_per_km) * 100)
            # Convert max travel time to seconds
            max_tijd_seconden = int(vehicle.maximale_rit_tijd * 3600) if vehicle.maximale_rit_tijd < 100 else int(vehicle.maximale_rit_tijd)
            
            vehicle_url = f"{optaplanner_service.base_url}/api/vehicleadd/{encoded_kenteken}/{vehicle.aantal_zitplaatsen}/{vehicle.speciale_zitplaatsen}/{km_tarief_cents}/{max_tijd_seconden}"
            print(f"   📡 Vehicle URL: {vehicle_url}")
            
            vehicle_response = requests.get(vehicle_url, timeout=5)
            print(f"   📡 Vehicle response: {vehicle_response.status_code} - {vehicle_response.text}")
            
            if vehicle_response.status_code == 200:
                vehicles_added += 1
        except Exception as e:
            print(f"   ❌ Vehicle {vehicle.kenteken} error: {e}")
    print(f"   ✅ {vehicles_added}/{vehicles.count()} voertuigen toegevoegd")
    print()
    
    # STEP 6: Add patients
    print("🚀 STEP 6: Patiënten toevoegen...")
    patients = Patient.objects.filter(status='nieuw', halen_tijdblok__isnull=False)
    print(f"   📊 Patiënten met tijdblokken: {patients.count()}")
    
    # Group patients by time slot
    patients_by_halen = {}
    for patient in patients:
        if patient.halen_tijdblok:
            timeslot_name = patient.halen_tijdblok.naam
            if timeslot_name not in patients_by_halen:
                patients_by_halen[timeslot_name] = []
            patients_by_halen[timeslot_name].append(patient)
    
    print(f"   📊 Tijdblokken gevonden: {len(patients_by_halen)}")
    for timeslot_name, patients_list in patients_by_halen.items():
        print(f"      - {timeslot_name}: {len(patients_list)} patiënten")
    
    # Add patients per time slot
    total_patients_added = 0
    for timeslot_name, patients_list in patients_by_halen.items():
        print(f"   🚀 Tijdblok verwerken: {timeslot_name} ({len(patients_list)} patiënten)")
        
        patients_added = 0
        for patient in patients_list:
            if patient.latitude and patient.longitude:
                try:
                    # Determine pickup/dropoff type based on time slots
                    pickup_type = "1" if patient.halen_tijdblok else "0"
                    # URL encode speciale karakters in naam
                    encoded_naam = patient.naam.replace(' ', '_').replace('-', '_').replace('.', '_')
                    # Determine if patient needs special seating
                    special_seating = "1" if patient.rolstoel else "0"
                    
                    location_url = f"{optaplanner_service.base_url}/api/locationadd/{encoded_naam}/{patient.longitude}/{patient.latitude}/{special_seating}/0/_/{pickup_type}"
                    print(f"      📡 Patient URL: {location_url}")
                    
                    location_response = requests.get(location_url, timeout=5)
                    print(f"      📡 Patient response: {location_response.status_code} - {location_response.text}")
                    
                    if location_response.status_code == 200:
                        patients_added += 1
                except Exception as e:
                    print(f"      ❌ Patient {patient.naam} error: {e}")
            else:
                print(f"      ⚠️  Patient {patient.naam} heeft geen coördinaten!")
        
        total_patients_added += patients_added
        print(f"      ✅ {patients_added}/{len(patients_list)} patiënten toegevoegd voor {timeslot_name}")
        
        # Wait a moment for OptaPlanner to process this time slot
        print(f"      ⏳ Wachten 2 seconden voor OptaPlanner...")
        time.sleep(2)
    
    print(f"   ✅ Totaal {total_patients_added}/{patients.count()} patiënten toegevoegd")
    print()
    
    # STEP 7: Check final status
    print("🚀 STEP 7: Eindstatus controleren...")
    try:
        final_route_response = requests.get(f"{optaplanner_service.base_url}/api/route", timeout=10)
        print(f"   📡 Final route response: {final_route_response.status_code}")
        if final_route_response.status_code == 200:
            route_data = final_route_response.json()
            print(f"   📊 Route data: {route_data}")
            
            total_locations = sum(len(route.get('locations', [])) for route in route_data.get('routes', []))
            print(f"   📊 Totaal locaties in routes: {total_locations}")
            
            if total_locations > 0:
                print("   🎉 SUCCESS: Routes gegenereerd!")
            else:
                print("   ⚠️  Geen locaties in routes - OptaPlanner heeft nog geen routes gegenereerd")
        else:
            print(f"   ❌ Route error: {final_route_response.text}")
    except Exception as e:
        print(f"   ❌ Final status error: {e}")
    
    print()
    print("🎯 Full workflow test voltooid!")

if __name__ == "__main__":
    test_full_workflow()
