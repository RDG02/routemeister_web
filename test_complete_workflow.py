#!/usr/bin/env python
"""
Test script voor complete workflow van wizard tot routes weergave
"""
import os
import sys
import django
from datetime import date, datetime, time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, TimeSlot, Vehicle, GoogleMapsConfig, Location
from planning.views import _create_timeslot_assignments_from_patients
from planning.services.google_maps import google_maps_service

def test_complete_workflow():
    print("🧪 Test Complete Workflow")
    print("=" * 50)
    
    # 1. Controleer database status
    print("\n1. Database Status:")
    print(f"   Patiënten: {Patient.objects.count()}")
    print(f"   Tijdsblokken: {TimeSlot.objects.count()}")
    print(f"   Voertuigen: {Vehicle.objects.count()}")
    print(f"   Google Maps config: {GoogleMapsConfig.objects.count()}")
    
    # 2. Haal patiënten op voor vandaag
    today = date.today()
    patients_today = Patient.objects.filter(ophaal_tijd__date=today)
    print(f"\n2. Patiënten voor vandaag ({today}): {patients_today.count()}")
    
    if patients_today.count() == 0:
        print("   ❌ Geen patiënten gevonden voor vandaag!")
        return False
    
    # 3. Controleer tijdsblok toewijzing
    print("\n3. Tijdsblok Toewijzing:")
    patients_with_halen = 0
    patients_with_bringen = 0
    patients_with_vehicle = 0
    
    for patient in patients_today:
        if patient.halen_tijdblok:
            patients_with_halen += 1
        if patient.bringen_tijdblok:
            patients_with_bringen += 1
        if patient.toegewezen_voertuig:
            patients_with_vehicle += 1
    
    print(f"   Patiënten met halen tijdsblok: {patients_with_halen}")
    print(f"   Patiënten met brengen tijdsblok: {patients_with_bringen}")
    print(f"   Patiënten met voertuig: {patients_with_vehicle}")
    
    # 4. Test tijdsblok toewijzing als deze ontbreekt
    if patients_with_halen == 0 or patients_with_bringen == 0:
        print("\n4. Tijdsblok Toewijzing Test:")
        try:
            # Test de functie
            timeslot_assignments = _create_timeslot_assignments_from_patients(list(patients_today))
            print(f"   ✅ Tijdsblok assignments gemaakt: {len(timeslot_assignments)} tijdsblokken")
            
            # Controleer resultaat
            patients_with_halen_after = 0
            patients_with_bringen_after = 0
            
            for patient in Patient.objects.filter(ophaal_tijd__date=today):
                if patient.halen_tijdblok:
                    patients_with_halen_after += 1
                if patient.bringen_tijdblok:
                    patients_with_bringen_after += 1
            
            print(f"   Na toewijzing - Halen: {patients_with_halen_after}, Brengen: {patients_with_bringen_after}")
            
        except Exception as e:
            print(f"   ❌ Fout bij tijdsblok toewijzing: {e}")
            return False
    
    # 5. Test route generatie
    print("\n5. Route Generatie Test:")
    try:
        # Haal tijdsblokken op
        timeslots = TimeSlot.objects.filter(actief=True, default_selected=True).order_by('aankomst_tijd')
        print(f"   Tijdsblokken gevonden: {timeslots.count()}")
        
        # Haal voertuigen op
        vehicles = list(Vehicle.objects.filter(status='beschikbaar'))
        print(f"   Beschikbare voertuigen: {len(vehicles)}")
        
        # Test fallback optimalisatie
        if 'timeslot_assignments' in locals() and timeslot_assignments:
            optimized_routes = google_maps_service._fallback_optimization(timeslot_assignments, vehicles)
            print(f"   ✅ Routes gegenereerd: {len(optimized_routes)} tijdsblokken")
            
            # Controleer voertuig toewijzing
            patients_with_vehicle_after = 0
            for patient in Patient.objects.filter(ophaal_tijd__date=today):
                if patient.toegewezen_voertuig:
                    patients_with_vehicle_after += 1
            print(f"   Patiënten met voertuig na optimalisatie: {patients_with_vehicle_after}")
            
        else:
            print("   ⚠️ Geen tijdsblok assignments beschikbaar")
            
    except Exception as e:
        print(f"   ❌ Fout bij route generatie: {e}")
        return False
    
    # 6. Test routes weergave data
    print("\n6. Routes Weergave Data Test:")
    try:
        routes_by_timeslot = {}
        
        for timeslot in timeslots:
            # Haal patiënten op voor dit tijdsblok
            if timeslot.tijdblok_type == 'halen':
                patients_in_timeslot = Patient.objects.filter(
                    ophaal_tijd__date=today,
                    halen_tijdblok=timeslot
                ).select_related('toegewezen_voertuig')
            else:  # brengen
                patients_in_timeslot = Patient.objects.filter(
                    ophaal_tijd__date=today,
                    bringen_tijdblok=timeslot
                ).select_related('toegewezen_voertuig')
            
            print(f"   Tijdsblok {timeslot.aankomst_tijd} ({timeslot.tijdblok_type}): {patients_in_timeslot.count()} patiënten")
            
            # Groepeer per voertuig
            vehicles_with_patients = {}
            for patient in patients_in_timeslot:
                if patient.toegewezen_voertuig:
                    vehicle_id = patient.toegewezen_voertuig.id
                    if vehicle_id not in vehicles_with_patients:
                        vehicles_with_patients[vehicle_id] = {
                            'vehicle': patient.toegewezen_voertuig,
                            'patients': []
                        }
                    vehicles_with_patients[vehicle_id]['patients'].append(patient)
            
            routes_by_timeslot[timeslot.id] = {
                'timeslot': timeslot,
                'vehicle_assignments': list(vehicles_with_patients.values()),
                'total_patients': patients_in_timeslot.count()
            }
        
        print(f"   ✅ Routes data gemaakt voor {len(routes_by_timeslot)} tijdsblokken")
        
        # Toon samenvatting
        total_patients = sum(data['total_patients'] for data in routes_by_timeslot.values())
        total_vehicles = sum(len(data['vehicle_assignments']) for data in routes_by_timeslot.values())
        print(f"   Totaal patiënten: {total_patients}")
        print(f"   Totaal voertuigen gebruikt: {total_vehicles}")
        
    except Exception as e:
        print(f"   ❌ Fout bij routes weergave data: {e}")
        return False
    
    print("\n✅ Complete workflow test succesvol!")
    return True

if __name__ == "__main__":
    success = test_complete_workflow()
    sys.exit(0 if success else 1)