#!/usr/bin/env python
"""
Script to test CSV parsing and time slot assignment
"""

import os
import django
import csv
import io
from datetime import datetime

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, TimeSlot

def test_csv_parsing():
    """
    Test CSV parsing with sample data
    """
    print("🧪 Testing CSV parsing and time slot assignment...")
    
    # Sample CSV data based on the actual CSV file format
    sample_csv_data = """FL25002609;;Schnurpfeil;Anette;;;Thelengasse 41;;Niederkassel;53859;D;0228-43328686;01735176280;;;21-8-2025;;0845;1515
FL25004041;;Hermanns;Wilfried;;;Blucherstrasse 24;;Siegburg;53721;D;022419388933;01603112992;;;21-8-2025;;0845;1515"""
    
    # Parse CSV
    csv_reader = csv.reader(io.StringIO(sample_csv_data), delimiter=';')
    
    for row_index, row in enumerate(csv_reader):
        if len(row) >= 15:
            print(f"\n📋 Row {row_index + 1}:")
            print(f"   Patient ID: {row[0]}")
            print(f"   Name: {row[2]} {row[3]}")
            print(f"   Address: {row[6]}")
            print(f"   Date: {row[15]}")
            print(f"   Pickup time: {row[17]} (kolom 18)")
            print(f"   End time: {row[18]} (kolom 19)")
            
            # Parse times
            try:
                # Parse pickup time: "0845" -> 08:45
                pickup_time_str = row[17]
                if len(pickup_time_str) >= 4:
                    start_uur = int(pickup_time_str[:2])
                    start_minuut = int(pickup_time_str[2:4])
                    pickup_time = datetime.now().replace(hour=start_uur, minute=start_minuut).time()
                    print(f"   Parsed pickup time: {pickup_time}")
                    
                    # Find matching time slot
                    timeslots = TimeSlot.objects.filter(actief=True, naam__startswith='Holen')
                    for timeslot in timeslots:
                        if (timeslot.heen_start_tijd and timeslot.heen_eind_tijd and
                            timeslot.heen_start_tijd <= pickup_time <= timeslot.heen_eind_tijd):
                            print(f"   ✅ Matches: {timeslot.naam} ({timeslot.heen_start_tijd}-{timeslot.heen_eind_tijd})")
                            break
                    else:
                        print(f"   ❌ No matching time slot found!")
                        
            except (ValueError, IndexError) as e:
                print(f"   ❌ Error parsing time: {e}")

def check_existing_patients():
    """
    Check existing patients and their time slot assignments
    """
    print("\n🔍 Checking existing patients...")
    
    patients = Patient.objects.filter(status='nieuw').order_by('ophaal_tijd')
    
    for patient in patients:
        print(f"\n👤 {patient.naam}:")
        print(f"   Pickup time: {patient.ophaal_tijd}")
        print(f"   End time: {patient.eind_behandel_tijd}")
        print(f"   Halen tijdblok: {patient.halen_tijdblok}")
        print(f"   Brengen tijdblok: {patient.bringen_tijdblok}")
        
        # Check time slot assignment
        if patient.halen_tijdblok:
            timeslot = patient.halen_tijdblok
            pickup_time = patient.ophaal_tijd.time()
            if (timeslot.heen_start_tijd and timeslot.heen_eind_tijd and
                timeslot.heen_start_tijd <= pickup_time <= timeslot.heen_eind_tijd):
                print(f"   ✅ Correct halen assignment: {timeslot.naam}")
            else:
                print(f"   ❌ Incorrect halen assignment: {timeslot.naam}")

if __name__ == "__main__":
    test_csv_parsing()
    check_existing_patients()
