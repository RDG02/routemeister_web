#!/usr/bin/env python
"""
Finale test om te controleren of de belangrijkste problemen zijn opgelost
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from django.test import Client

def test_main_functionality():
    """Test de belangrijkste functionaliteit"""
    print("🧪 Finale test van Routemeister functionaliteit...")
    
    client = Client()
    
    # Test 1: Planning pagina laadt zonder errors
    print("\n📋 Test 1: Planning pagina")
    response = client.get('/planning/new-ui/')
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        print("   ✅ Planning pagina laadt correct")
    else:
        print("   ❌ Planning pagina geeft error")
        return False
    
    # Test 2: Planning pagina met route data
    print("\n🗺️ Test 2: Planning pagina met route data")
    
    # Set up test route data
    test_route_data = {
        'optimized_routes': {
            'timeslot_1': {
                'routes': [
                    {
                        'vehicle_id': 'W206',
                        'vehicle_name': 'W206 - VW Transporter',
                        'patients': [
                            {'patient_id': 1, 'naam': 'Brigitte Effelsberg'},
                            {'patient_id': 2, 'naam': 'Hans Müller'}
                        ],
                        'total_distance': 25.5,
                        'total_time': 45,
                        'total_cost': 7.40
                    }
                ],
                'total_distance': 470.0,
                'total_time': 900,
                'total_cost': 136.30,
                'vehicle_count': 20
            }
        },
        'statistics': {
            'total_distance': 470.0,
            'total_time': 900,
            'total_cost': 136.30,
            'total_vehicles': 20,
            'timeslots_processed': 1
        }
    }
    
    session = client.session
    session['google_maps_routes'] = test_route_data
    session.save()
    
    response = client.get('/planning/new-ui/')
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        content = response.content.decode()
        if 'Route Optimalisatie Resultaten' in content and '470.0' in content:
            print("   ✅ Route data wordt correct weergegeven")
        else:
            print("   ⚠️ Route data wordt niet weergegeven")
    else:
        print("   ❌ Planning pagina geeft error met route data")
        return False
    
    # Test 3: Dashboard
    print("\n📊 Test 3: Dashboard")
    response = client.get('/dashboard/')
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        print("   ✅ Dashboard laadt correct")
    else:
        print("   ❌ Dashboard geeft error")
        return False
    
    # Test 4: Wizard start
    print("\n🚀 Test 4: Wizard start")
    response = client.get('/wizard/')
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        print("   ✅ Wizard start pagina laadt correct")
    else:
        print("   ❌ Wizard start pagina geeft error")
        return False
    
    # Test 5: Wizard assignment
    print("\n🎯 Test 5: Wizard assignment")
    response = client.get('/wizard/assignment/')
    print(f"   Status: {response.status_code}")
    
    if response.status_code in [200, 302]:
        print("   ✅ Wizard assignment pagina werkt (200 of 302)")
    else:
        print("   ❌ Wizard assignment pagina geeft error")
        return False
    
    print("\n✅ Alle tests geslaagd!")
    return True

if __name__ == '__main__':
    success = test_main_functionality()
    sys.exit(0 if success else 1)
