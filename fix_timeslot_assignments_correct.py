#!/usr/bin/env python
"""
Fix tijdblok toewijzingen - alleen geselecteerde tijdblokken
"""
import os
import django
from datetime import datetime
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, TimeSlot
from django.db import models

def fix_timeslot_assignments_with_selected():
    print("🔧 Fix Tijdblok Toewijzingen - Geselecteerde Tijdblokken")
    print("=" * 60)
    
    today = datetime.now().date()
    patients = Patient.objects.filter(ophaal_tijd__date=today)
    
    # Alleen geselecteerde tijdblokken (default_selected=True)
    selected_timeslots = TimeSlot.objects.filter(actief=True, default_selected=True).order_by('heen_start_tijd')
    
    print(f"👥 Patiënten vandaag: {patients.count()}")
    print(f"⏰ Geselecteerde tijdblokken: {selected_timeslots.count()}")
    print()
    
    # Toon geselecteerde tijdblokken
    print("📅 Geselecteerde Tijdblokken:")
    print("-" * 30)
    for ts in selected_timeslots:
        print(f"   {ts.naam}: {ts.heen_start_tijd}-{ts.heen_eind_tijd} / {ts.terug_start_tijd}-{ts.terug_eind_tijd}")
    print()
    
    fixed_count = 0
    
    for patient in patients:
        print(f"📍 {patient.naam}")
        print(f"   📅 Eerste afspraak: {patient.ophaal_tijd}")
        print(f"   📅 Eind tijd: {patient.eind_behandel_tijd}")
        
        # Zoek halen tijdblok (eerste afspraak tijd) - alleen in geselecteerde tijdblokken
        halen_timeslot = None
        if patient.ophaal_tijd:
            first_appointment_time = patient.ophaal_tijd.time()
            print(f"   🚗 Eerste afspraak tijd: {first_appointment_time}")
            
            # Zoek tijdblok waar eerste afspraak tijd in past (alleen geselecteerde)
            for ts in selected_timeslots:
                if ts.heen_start_tijd <= first_appointment_time <= ts.heen_eind_tijd:
                    halen_timeslot = ts
                    print(f"   ✅ Halen tijdblok gevonden: {ts.naam}")
                    break
            
            if not halen_timeslot:
                print(f"   ❌ Geen halen tijdblok gevonden voor {first_appointment_time}")
        
        # Zoek brengen tijdblok (eind tijd) - alleen in geselecteerde tijdblokken
        brengen_timeslot = None
        if patient.eind_behandel_tijd:
            end_time = patient.eind_behandel_tijd.time()
            print(f"   🏠 Eind tijd: {end_time}")
            
            # Zoek eerste tijdblok waar eind tijd <= terug_start_tijd (alleen geselecteerde)
            for ts in selected_timeslots:
                if end_time <= ts.terug_start_tijd:
                    brengen_timeslot = ts
                    print(f"   ✅ Brengen tijdblok gevonden: {ts.naam}")
                    break
            
            if not brengen_timeslot:
                print(f"   ❌ Geen brengen tijdblok gevonden voor {end_time}")
        
        # Update patiënt
        if halen_timeslot:
            patient.halen_tijdblok = halen_timeslot
            print(f"   🚗 Halen toegewezen: {halen_timeslot.naam}")
        
        if brengen_timeslot:
            patient.bringen_tijdblok = brengen_timeslot
            print(f"   🏠 Brengen toegewezen: {brengen_timeslot.naam}")
        
        if halen_timeslot or brengen_timeslot:
            patient.save()
            fixed_count += 1
            print(f"   ✅ Opgeslagen")
        else:
            print(f"   ❌ Geen tijdblokken toegewezen")
        
        print()
    
    print(f"📊 {fixed_count} patiënten gefixed")
    
    # Toon resultaat
    print(f"\n📋 Resultaat:")
    print("-" * 30)
    
    for patient in patients:
        halen = patient.halen_tijdblok.naam if patient.halen_tijdblok else "Geen"
        brengen = patient.bringen_tijdblok.naam if patient.bringen_tijdblok else "Geen"
        print(f"   {patient.naam}: {halen} / {brengen}")

def test_with_web_flow():
    """
    Test de web flow met geselecteerde tijdblokken
    """
    print(f"\n🌐 Test Web Flow met Geselecteerde Tijdblokken")
    print("-" * 50)
    
    # Simuleer wat er in de web flow gebeurt
    from planning.services.simple_router import simple_route_service
    from planning.models import Vehicle
    
    today = datetime.now().date()
    patients = Patient.objects.filter(ophaal_tijd__date=today)
    vehicles = Vehicle.objects.filter(status='beschikbaar')
    
    # Alleen patiënten met tijdblok toewijzing
    assigned_patients = patients.filter(
        models.Q(halen_tijdblok__isnull=False) | 
        models.Q(bringen_tijdblok__isnull=False)
    ).distinct()
    
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

if __name__ == "__main__":
    fix_timeslot_assignments_with_selected()
    test_with_web_flow()
    print(f"\n✅ Fix voltooid!")
