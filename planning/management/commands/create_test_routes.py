from django.core.management.base import BaseCommand
from django.utils import timezone
from planning.models import Patient, Vehicle, TimeSlot
from datetime import datetime, time, timedelta
import random

class Command(BaseCommand):
    help = 'Maak test routes aan voor de dashboard kaart'

    def handle(self, *args, **options):
        # Maak een test voertuig aan als het nog niet bestaat
        vehicle, created = Vehicle.objects.get_or_create(
            kenteken='WAG001',
            defaults={
                'merk_model': 'Mercedes Sprinter',
                'max_patienten': 4,
                'aantal_zitplaatsen': 7,
                'speciale_zitplaatsen': 0,
                'kleur': '#3498db',
                'status': 'beschikbaar'
            }
        )
        
        if created:
            self.stdout.write(f'✅ Voertuig {vehicle.kenteken} aangemaakt')
        else:
            self.stdout.write(f'ℹ️ Voertuig {vehicle.kenteken} bestaat al')
        
        # Maak een test tijdblok aan
        timeslot, created = TimeSlot.objects.get_or_create(
            naam='Test Halen 0800',
            defaults={
                'heen_start_tijd': time(8, 0),
                'heen_eind_tijd': time(9, 30),
                'terug_start_tijd': time(14, 0),
                'terug_eind_tijd': time(15, 30),
                'max_rijtijd_minuten': 60,
                'max_patienten_per_rit': 4,
                'actief': True,
                'dag_van_week': 'maandag'
            }
        )
        
        if created:
            self.stdout.write(f'✅ Tijdblok {timeslot.naam} aangemaakt')
        else:
            self.stdout.write(f'ℹ️ Tijdblok {timeslot.naam} bestaat al')
        
        # Test patiënten met GPS coördinaten rond Bonn
        test_patients = [
            {
                'naam': 'Hans Müller',
                'straat': 'Koblenzer Straße 123',
                'postcode': '53177',
                'plaats': 'Bonn',
                'latitude': 50.7300,
                'longitude': 7.1000,
                'ophaal_tijd': timezone.now().replace(hour=8, minute=30, second=0, microsecond=0),
                'eind_behandel_tijd': timezone.now().replace(hour=12, minute=0, second=0, microsecond=0),
                'bestemming': 'Reha Center Bonn',
                'mobile_status': 'pending'
            },
            {
                'naam': 'Maria Schmidt',
                'straat': 'Kaiserstraße 456',
                'postcode': '53113',
                'plaats': 'Bonn',
                'latitude': 50.7350,
                'longitude': 7.0950,
                'ophaal_tijd': timezone.now().replace(hour=8, minute=45, second=0, microsecond=0),
                'eind_behandel_tijd': timezone.now().replace(hour=12, minute=30, second=0, microsecond=0),
                'bestemming': 'Reha Center Bonn',
                'mobile_status': 'notified'
            },
            {
                'naam': 'Peter Weber',
                'straat': 'Adenauerallee 789',
                'postcode': '53111',
                'plaats': 'Bonn',
                'latitude': 50.7400,
                'longitude': 7.1050,
                'ophaal_tijd': timezone.now().replace(hour=9, minute=0, second=0, microsecond=0),
                'eind_behandel_tijd': timezone.now().replace(hour=13, minute=0, second=0, microsecond=0),
                'bestemming': 'Reha Center Bonn',
                'mobile_status': 'in_transit'
            },
            {
                'naam': 'Anna Fischer',
                'straat': 'Poppelsdorfer Allee 321',
                'postcode': '53115',
                'plaats': 'Bonn',
                'latitude': 50.7250,
                'longitude': 7.1100,
                'ophaal_tijd': timezone.now().replace(hour=9, minute=15, second=0, microsecond=0),
                'eind_behandel_tijd': timezone.now().replace(hour=13, minute=30, second=0, microsecond=0),
                'bestemming': 'Reha Center Bonn',
                'mobile_status': 'completed'
            }
        ]
        
        created_count = 0
        for patient_data in test_patients:
            patient, created = Patient.objects.get_or_create(
                naam=patient_data['naam'],
                ophaal_tijd__date=patient_data['ophaal_tijd'].date(),
                defaults={
                    'straat': patient_data['straat'],
                    'postcode': patient_data['postcode'],
                    'plaats': patient_data['plaats'],
                    'latitude': patient_data['latitude'],
                    'longitude': patient_data['longitude'],
                    'ophaal_tijd': patient_data['ophaal_tijd'],
                    'eind_behandel_tijd': patient_data['eind_behandel_tijd'],
                    'bestemming': patient_data['bestemming'],
                    'halen_tijdblok': timeslot,
                    'bringen_tijdblok': timeslot,
                    'toegewezen_voertuig': vehicle,
                    'status': 'gepland',
                    'mobile_status': patient_data['mobile_status'],
                    'geocoding_status': 'success'
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'✅ Patiënt {patient.naam} aangemaakt')
            else:
                # Update bestaande patiënt met nieuwe data
                patient.halen_tijdblok = timeslot
                patient.bringen_tijdblok = timeslot
                patient.toegewezen_voertuig = vehicle
                patient.status = 'gepland'
                patient.mobile_status = patient_data['mobile_status']
                patient.save()
                self.stdout.write(f'🔄 Patiënt {patient.naam} bijgewerkt')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Test routes succesvol aangemaakt! {created_count} nieuwe patiënten toegevoegd.'
            )
        )
        self.stdout.write('🗺️ Ga naar het dashboard om de kaart te bekijken!')
