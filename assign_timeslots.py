#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, TimeSlot

def assign_timeslots():
    print("=== MANUALLY ASSIGNING TIME SLOTS ===")
    
    # Get patients and time slots
    patients = Patient.objects.filter(status='nieuw')
    halen_timeslots = TimeSlot.objects.filter(actief=True, tijdblok_type='halen')
    brengen_timeslots = TimeSlot.objects.filter(actief=True, tijdblok_type='brengen')
    
    print(f"Patients: {patients.count()}")
    print(f"Active halen time slots: {halen_timeslots.count()}")
    print(f"Active brengen time slots: {brengen_timeslots.count()}")
    
    # Assign time slots based on pickup time
    assigned_count = 0
    for patient in patients:
        pickup_time = patient.ophaal_tijd.time()
        end_time = patient.eind_behandel_tijd.time()
        
        # Find suitable halen time slot (based on aankomst_tijd)
        halen_timeslot = None
        for ts in halen_timeslots:
            # Voor halen: zoek het tijdblok waar de ophaal tijd het dichtst bij de aankomst tijd ligt
            # We nemen het tijdblok waar de patiënt ongeveer 30-60 minuten voor aankomst wordt opgehaald
            from datetime import timedelta
            import datetime
            
            # Bereken de geschatte ophaal tijd (30 minuten voor aankomst)
            estimated_pickup = datetime.datetime.combine(datetime.date.today(), ts.aankomst_tijd) - timedelta(minutes=30)
            estimated_pickup_time = estimated_pickup.time()
            
            # Check of de patiënt ophaal tijd binnen 30 minuten van de geschatte ophaal tijd ligt
            time_diff = abs((datetime.datetime.combine(datetime.date.today(), pickup_time) - 
                           datetime.datetime.combine(datetime.date.today(), estimated_pickup_time)).total_seconds() / 60)
            
            if time_diff <= 30:  # Binnen 30 minuten
                halen_timeslot = ts
                break
        
        # Find suitable brengen time slot (based on aankomst_tijd)
        brengen_timeslot = None
        for ts in brengen_timeslots:
            # Voor brengen: zoek het tijdblok waar de eind behandeling tijd het dichtst bij de aankomst tijd ligt
            time_diff = abs((datetime.datetime.combine(datetime.date.today(), end_time) - 
                           datetime.datetime.combine(datetime.date.today(), ts.aankomst_tijd)).total_seconds() / 60)
            
            if time_diff <= 30:  # Binnen 30 minuten
                brengen_timeslot = ts
                break
        
        # Assign time slots
        if halen_timeslot:
            patient.halen_tijdblok = halen_timeslot
            print(f"✅ {patient.naam}: Halen {halen_timeslot.naam} (aankomst {halen_timeslot.aankomst_tijd})")
            assigned_count += 1
        
        if brengen_timeslot:
            patient.bringen_tijdblok = brengen_timeslot
            print(f"✅ {patient.naam}: Brengen {brengen_timeslot.naam} (eind {brengen_timeslot.aankomst_tijd})")
        
        patient.save()
    
    print(f"\nAssigned time slots to {assigned_count} patients")

if __name__ == "__main__":
    assign_timeslots()
