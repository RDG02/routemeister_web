from django.core.management.base import BaseCommand
from planning.models import Location


class Command(BaseCommand):
    help = 'Geocode locaties op basis van hun adres'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Geocode alle locaties met een adres',
        )
        parser.add_argument(
            '--location-id',
            type=int,
            help='Geocode specifieke locatie ID',
        )

    def handle(self, *args, **options):
        if options['location_id']:
            # Geocode specifieke locatie
            try:
                location = Location.objects.get(id=options['location_id'])
                self.geocode_location(location)
            except Location.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Locatie met ID {options["location_id"]} niet gevonden.')
                )
        elif options['all']:
            # Geocode alle locaties
            locations = Location.objects.filter(address__isnull=False).exclude(address='')
            self.stdout.write(f'Geocoding {locations.count()} locaties...')
            
            success_count = 0
            failed_count = 0
            
            for location in locations:
                if self.geocode_location(location):
                    success_count += 1
                else:
                    failed_count += 1
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nGeocoding voltooid!\n'
                    f'Succesvol: {success_count}\n'
                    f'Mislukt: {failed_count}'
                )
            )
        else:
            # Toon locaties die geocoded kunnen worden
            locations = Location.objects.filter(
                address__isnull=False
            ).exclude(address='').filter(
                latitude__isnull=True
            ).exclude(latitude=0)
            
            if locations.exists():
                self.stdout.write('Locaties die geocoded kunnen worden:')
                for location in locations:
                    self.stdout.write(f'  ID {location.id}: {location.name} - {location.address}')
                self.stdout.write('\nGebruik --all om alle locaties te geocoden.')
            else:
                self.stdout.write('Geen locaties gevonden die geocoded moeten worden.')

    def geocode_location(self, location):
        """Geocode een specifieke locatie"""
        if not location.address:
            self.stdout.write(f'  ❌ {location.name}: Geen adres')
            return False
        
        self.stdout.write(f'  🔍 {location.name}: {location.address}')
        
        if location.geocode_address():
            location.save()
            self.stdout.write(f'  ✅ {location.name}: {location.latitude}, {location.longitude}')
            return True
        else:
            self.stdout.write(f'  ❌ {location.name}: Geocoding mislukt')
            return False
