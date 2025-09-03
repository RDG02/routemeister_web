#!/usr/bin/env python
"""
Test script voor de PatientCacheManager
"""
import os
import sys
import django

# Voeg het project toe aan Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.cache_manager import PatientCacheManager
from planning.models import Patient
from datetime import datetime, date

def test_cache_manager():
    """Test de cache manager functionaliteit"""
    
    print("🧪 Test PatientCacheManager")
    print("=" * 50)
    
    # Test 1: Hash generatie
    print("1️⃣ Test hash generatie...")
    hash1 = PatientCacheManager.generate_patient_hash("John Doe", "Main St 123", "12345", "Amsterdam")
    hash2 = PatientCacheManager.generate_patient_hash("John Doe", "Main St 123", "12345", "Amsterdam")
    hash3 = PatientCacheManager.generate_patient_hash("Jane Doe", "Main St 123", "12345", "Amsterdam")
    
    print(f"   Hash 1: {hash1}")
    print(f"   Hash 2: {hash2}")
    print(f"   Hash 3: {hash3}")
    print(f"   Hash 1 == Hash 2: {hash1 == hash2}")
    print(f"   Hash 1 == Hash 3: {hash1 == hash3}")
    
    # Test 2: Cache operaties
    print("\n2️⃣ Test cache operaties...")
    
    test_data = {
        'id': 999,
        'naam': 'Test Patient',
        'straat': 'Test Straat 1',
        'postcode': '1234AB',
        'plaats': 'Test Stad',
        'telefoonnummer': '0612345678',
        'created_at': datetime.now().isoformat(),
        'cached': True
    }
    
    # Test cache set/get
    PatientCacheManager.cache_patient(hash1, test_data)
    cached_data = PatientCacheManager.get_cached_patient(hash1)
    
    print(f"   Data gecached: {cached_data is not None}")
    print(f"   Cached naam: {cached_data.get('naam') if cached_data else 'None'}")
    
    # Test 3: Patiënt matching
    print("\n3️⃣ Test patiënt matching...")
    
    # Maak test patiënt aan
    test_patient, created = PatientCacheManager.get_or_create_patient_with_cache(
        "Test Cache Patient",
        "Cache Straat 1",
        "5678CD",
        "Cache Stad",
        "0612345678",
        datetime.now(),
        datetime.now()
    )
    
    print(f"   Nieuwe patiënt aangemaakt: {created}")
    print(f"   Patiënt ID: {test_patient.id}")
    print(f"   Patiënt naam: {test_patient.naam}")
    
    # Test 4: Cache statistieken
    print("\n4️⃣ Test cache statistieken...")
    stats = PatientCacheManager.get_cache_stats()
    print(f"   Cache prefix: {stats['cache_prefix']}")
    print(f"   Cache TTL dagen: {stats['cache_ttl_days']}")
    print(f"   Status: {stats['status']}")
    
    # Test 5: Bestaande patiënten van vandaag
    print("\n5️⃣ Test bestaande patiënten van vandaag...")
    today = date.today()
    existing_patients = Patient.objects.filter(ophaal_tijd__date=today)
    
    if existing_patients.exists():
        print(f"   ✅ {existing_patients.count()} patiënten gevonden voor vandaag")
        
        # Cache alle bestaande patiënten
        for patient in existing_patients[:3]:  # Alleen eerste 3
            patient_hash = PatientCacheManager.generate_patient_hash(
                patient.naam, patient.straat, patient.postcode, patient.plaats
            )
            
            cache_data = {
                'id': patient.id,
                'naam': patient.naam,
                'straat': patient.straat,
                'postcode': patient.postcode,
                'plaats': patient.plaats,
                'telefoonnummer': patient.telefoonnummer,
                'created_at': patient.aangemaakt_op.isoformat() if patient.aangemaakt_op else datetime.now().isoformat(),
                'cached': True
            }
            
            PatientCacheManager.cache_patient(patient_hash, cache_data)
            print(f"   💾 Gecached: {patient.naam}")
    else:
        print(f"   ❌ Geen patiënten gevonden voor vandaag")
    
    print("\n✅ Test voltooid!")

if __name__ == "__main__":
    test_cache_manager()
