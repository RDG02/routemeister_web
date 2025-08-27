#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient

def check_new_patients():
    print("=== PATIENTS WITH STATUS 'NIEUW' ===")
    
    patients = Patient.objects.filter(status='nieuw')
    
    print(f"Total patients with status 'nieuw': {patients.count()}")
    
    for p in patients:
        pickup_time = p.ophaal_tijd.time() if p.ophaal_tijd else "None"
        halen_name = p.halen_tijdblok.naam if p.halen_tijdblok else "None"
        print(f"  - {p.naam}: pickup={pickup_time} -> halen_tijdblok={halen_name}")

if __name__ == "__main__":
    check_new_patients()
