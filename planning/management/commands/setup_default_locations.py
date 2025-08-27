from django.core.management.base import BaseCommand
from planning.models import Location


class Command(BaseCommand):
    help = 'Setup standaard locaties in de database'

    def handle(self, *args, **options):
        self.stdout.write('Setting up default locations...')
        
        # Standaard locaties
        locations = [
            {
                'name': 'Reha Center Bonn',
                'location_type': 'home',
                'address': 'Reha Center, Bonn, Duitsland',
                'latitude': 50.8503,
                'longitude': 7.1017,
                'is_default': True,
                'description': 'Hoofdlocatie Reha Center in Bonn - start en eindpunt voor alle routes'
            },
            {
                'name': 'Depot Amsterdam',
                'location_type': 'depot',
                'address': 'Depot Amsterdam, Nederland',
                'latitude': 52.3676,
                'longitude': 4.9041,
                'is_default': False,
                'description': 'Depot locatie in Amsterdam'
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for location_data in locations:
            location, created = Location.objects.get_or_create(
                name=location_data['name'],
                defaults={
                    'location_type': location_data['location_type'],
                    'address': location_data['address'],
                    'latitude': location_data['latitude'],
                    'longitude': location_data['longitude'],
                    'is_default': location_data['is_default'],
                    'description': location_data['description'],
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'  ✅ Created: {location.name}')
            else:
                # Update bestaande locatie
                location.location_type = location_data['location_type']
                location.address = location_data['address']
                location.latitude = location_data['latitude']
                location.longitude = location_data['longitude']
                location.is_default = location_data['is_default']
                location.description = location_data['description']
                location.save()
                updated_count += 1
                self.stdout.write(f'  🔄 Updated: {location.name}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nLocaties setup voltooid!\n'
                f'Created: {created_count}, Updated: {updated_count}'
            )
        )
        
        self.stdout.write('\nBeschikbare locaties:')
        for location in Location.objects.filter(is_active=True).order_by('location_type', 'name'):
            self.stdout.write(f'  {location.name}: {location.latitude}, {location.longitude} ({location.get_location_type_display()})')
        
        # Toon standaard home locatie
        home_location = Location.get_home_location()
        if home_location:
            self.stdout.write(f'\n🏠 Standaard Home/Depot: {home_location.name} ({home_location.latitude}, {home_location.longitude})')
        else:
            self.stdout.write('\n⚠️  Geen standaard home/depot locatie gevonden!')
