#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient

def check_all_patients():
    print("=== ALL PATIENTS IN DATABASE ===")
    
    patients = Patient.objects.all()
    
    for p in patients:
        pickup_time = p.ophaal_tijd.time() if p.ophaal_tijd else "None"
        halen_name = p.halen_tijdblok.naam if p.halen_tijdblok else "None"
        print(f"  - {p.naam}: pickup={pickup_time} -> halen_tijdblok={halen_name}")

if __name__ == "__main__":
    check_all_patients()
