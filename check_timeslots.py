#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, TimeSlot

def check_timeslots():
    print("=== CORRECT TIMESLOT ANALYSIS ===")
    
    patients = Patient.objects.filter(status='nieuw')
    halen_timeslots = TimeSlot.objects.filter(actief=True, tijdblok_type='halen')
    brengen_timeslots = TimeSlot.objects.filter(actief=True, tijdblok_type='brengen')
    
    print("Active HALEN time slots:")
    for ts in halen_timeslots:
        print(f"  - {ts.naam}: aankomst={ts.aankomst_tijd}")
    
    print("\nActive BRENGEN time slots:")
    for ts in brengen_timeslots:
        print(f"  - {ts.naam}: eind={ts.aankomst_tijd}")
    
    print("\nPatient pickup times and assigned time slots:")
    for p in patients:
        halen_name = p.halen_tijdblok.naam if p.halen_tijdblok else "None"
        brengen_name = p.bringen_tijdblok.naam if p.bringen_tijdblok else "None"
        print(f"  - {p.naam}: pickup={p.ophaal_tijd.time()} -> halen_tijdblok={halen_name}")
        print(f"    eind={p.eind_behandel_tijd.time() if p.eind_behandel_tijd else 'None'} -> brengen_tijdblok={brengen_name}")
    
    # Group by halen time slot
    print("\nGrouping by HALEN time slot:")
    patients_by_halen = {}
    for p in patients:
        if p.halen_tijdblok:
            timeslot_name = p.halen_tijdblok.naam
            if timeslot_name not in patients_by_halen:
                patients_by_halen[timeslot_name] = []
            patients_by_halen[timeslot_name].append(p)
    
    for timeslot_name, patients_list in patients_by_halen.items():
        print(f"  📥 {timeslot_name}: {len(patients_list)} patients")
        for p in patients_list:
            print(f"    - {p.naam}")
    
    # Group by brengen time slot
    print("\nGrouping by BRENGEN time slot:")
    patients_by_brengen = {}
    for p in patients:
        if p.bringen_tijdblok:
            timeslot_name = p.bringen_tijdblok.naam
            if timeslot_name not in patients_by_brengen:
                patients_by_brengen[timeslot_name] = []
            patients_by_brengen[timeslot_name].append(p)
    
    for timeslot_name, patients_list in patients_by_brengen.items():
        print(f"  📤 {timeslot_name}: {len(patients_list)} patients")
        for p in patients_list:
            print(f"    - {p.naam}")

if __name__ == "__main__":
    check_timeslots()
