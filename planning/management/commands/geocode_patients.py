"""
Management command om patiënten adressen te geocoderen naar GPS coordinaten
"""
from django.core.management.base import BaseCommand
from planning.models import Patient
import requests
import time

class Command(BaseCommand):
    help = 'Geocode patiënten met pending status'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force geocoding voor alle patiënten zonder coördinaten',
        )

    def handle(self, *args, **options):
        if options['force']:
            patients = Patient.objects.filter(
                latitude__isnull=True, 
                longitude__isnull=True
            )
        else:
            patients = Patient.objects.filter(
                geocoding_status='pending'
            )
        
        if not patients.exists():
            self.stdout.write(
                self.style.WARNING('Geen patiënten gevonden voor geocoding.')
            )
            return
        
        self.stdout.write(f"🗺️ Geocoding {patients.count()} patiënten...")
        
        success_count = 0
        error_count = 0
        
        for patient in patients:
            if patient.straat and patient.postcode and patient.plaats:
                # Maak volledig adres
                full_address = f"{patient.straat}, {patient.postcode} {patient.plaats}, Deutschland"
                
                try:
                    # Gebruik OpenStreetMap Nominatim API
                    url = "https://nominatim.openstreetmap.org/search"
                    params = {
                        'q': full_address,
                        'format': 'json',
                        'limit': 1
                    }
                    headers = {
                        'User-Agent': 'Routemeister/1.0 (https://routemeister.com)'
                    }
                    
                    response = requests.get(url, params=params, headers=headers, timeout=10)
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    if data and len(data) > 0:
                        result = data[0]
                        patient.latitude = float(result['lat'])
                        patient.longitude = float(result['lon'])
                        patient.geocoding_status = 'success'
                        patient.save()
                        success_count += 1
                        self.stdout.write(f"✅ {patient.naam}: {result['lat']}, {result['lon']}")
                    else:
                        patient.geocoding_status = 'failed'
                        patient.save()
                        error_count += 1
                        self.stdout.write(f"❌ {patient.naam}: Geen resultaten gevonden")
                        
                except Exception as e:
                    patient.geocoding_status = 'failed'
                    patient.save()
                    error_count += 1
                    self.stdout.write(f"❌ {patient.naam}: {str(e)}")
                
                # Pauze tussen requests om API niet te overbelasten
                time.sleep(1)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Geocoding voltooid: {success_count} succesvol, {error_count} gefaald'
            )
        )
