#!/usr/bin/env python
"""
Test script voor CSV parsing en auto-assignment
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.views import perform_auto_assignment
from datetime import datetime

def test_csv_auto_assignment():
    """Test de CSV auto-assignment functie"""
    
    # Simuleer upload data zoals het in de session zou staan
    upload_data = {
        'filename': 'routemeister_27062025 (19).csv',
        'patient_count': 12,
        'csv_data': [
            {
                'type': 'data',
                'data': ['P001', '', 'John', 'Doe', '', '', 'Teststraat 1', '', 'Teststad', '1234AB', '', '0612345678', '', '', '', '2025-08-27', '', '08:30', '09:30']
            },
            {
                'type': 'data', 
                'data': ['P002', '', 'Jane', 'Smith', '', '', 'Teststraat 2', '', 'Teststad', '1234CD', '', '0612345679', '', '', '', '2025-08-27', '', '09:00', '10:00']
            },
            {
                'type': 'data',
                'data': ['P003', '', 'Bob', 'Johnson', '', '', 'Teststraat 3', '', 'Teststad', '1234EF', '', '0612345680', '', '', '', '2025-08-27', '', '10:30', '11:30']
            }
        ],
        'detection_result': {
            'mappings': {
                'patient_id': 0,
                'achternaam': 2, 
                'voornaam': 3,
                'adres': 6,
                'plaats': 8,
                'postcode': 9,
                'telefoon1': 11,
                'telefoon2': 12,
                'datum': 15,
                'start_tijd': 17,
                'eind_tijd': 18
            }
        }
    }
    
    # Test constraints (lege lijst voor nu)
    constraints = []
    
    print("🚀 Start CSV auto-assignment test...")
    print(f"📁 Bestand: {upload_data['filename']}")
    print(f"👥 Patiënten: {upload_data['patient_count']}")
    print(f"📊 CSV rijen: {len(upload_data['csv_data'])}")
    print(f"🔧 Mappings: {upload_data['detection_result']['mappings']}")
    print("-" * 50)
    
    try:
        # Voer auto-assignment uit
        result = perform_auto_assignment(upload_data, constraints)
        
        print("\n✅ Resultaat:")
        print(f"Succes: {result.get('success', False)}")
        
        if result.get('success'):
            stats = result.get('statistics', {})
            print(f"📊 Statistieken:")
            print(f"   - Totaal patiënten: {stats.get('total_patients', 0)}")
            print(f"   - Toegewezen: {stats.get('assigned_patients', 0)}")
            print(f"   - Niet toegewezen: {stats.get('unassigned_patients', 0)}")
            print(f"   - Succes percentage: {stats.get('assignment_rate', 0):.1f}%")
            print(f"   - Tijdblokken gebruikt: {stats.get('timeslots_used', 0)}")
            
            # Toon tijdblok toewijzingen
            timeslot_assignments = result.get('timeslot_assignments', {})
            if timeslot_assignments:
                print(f"\n📅 Tijdblok toewijzingen:")
                for timeslot_id, patients in timeslot_assignments.items():
                    print(f"   Tijdblok {timeslot_id}: {len(patients)} patiënten")
                    for patient in patients:
                        print(f"     - {patient['voornaam']} {patient['achternaam']} ({patient['start_time']}-{patient['end_time']})")
            
            # Toon niet-toegewezen patiënten
            unassigned = result.get('unassigned_patients', [])
            if unassigned:
                print(f"\n❌ Niet toegewezen patiënten:")
                for patient in unassigned:
                    print(f"   - {patient['voornaam']} {patient['achternaam']} ({patient['start_time']}-{patient['end_time']})")
        else:
            print(f"❌ Fout: {result.get('error', 'Onbekende fout')}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_csv_auto_assignment()
