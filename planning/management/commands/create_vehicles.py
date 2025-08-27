from django.core.management.base import BaseCommand
from planning.models import Vehicle


class Command(BaseCommand):
    help = 'Creates 5 default vehicles (WAG001-WAG005) for Routemeister'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starten met aanmaken van voertuigen...'))

        vehicles_data = [
            {
                'kenteken': 'WAG001',
                'merk_model': 'Mercedes Sprinter',
                'max_patienten': 4,
                'heeft_rolstoel_lift': True
            },
            {
                'kenteken': 'WAG002', 
                'merk_model': 'Volkswagen Crafter',
                'max_patienten': 6,
                'heeft_rolstoel_lift': False
            },
            {
                'kenteken': 'WAG003',
                'merk_model': 'Ford Transit',
                'max_patienten': 4,
                'heeft_rolstoel_lift': True
            },
            {
                'kenteken': 'WAG004',
                'merk_model': 'Renault Master', 
                'max_patienten': 5,
                'heeft_rolstoel_lift': False
            },
            {
                'kenteken': 'WAG005',
                'merk_model': 'Iveco Daily',
                'max_patienten': 3,
                'heeft_rolstoel_lift': True
            }
        ]

        created_count = 0
        for vehicle_data in vehicles_data:
            vehicle, created = Vehicle.objects.get_or_create(
                kenteken=vehicle_data['kenteken'],
                defaults={
                    'merk_model': vehicle_data['merk_model'],
                    'max_patienten': vehicle_data['max_patienten'],
                    'heeft_rolstoel_lift': vehicle_data['heeft_rolstoel_lift'],
                    'status': 'beschikbaar'
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ {vehicle_data["kenteken"]} - {vehicle_data["merk_model"]} aangemaakt')
                )
                created_count += 1
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠️ {vehicle_data["kenteken"]} bestaat al, overgeslagen')
                )

        self.stdout.write(
            self.style.SUCCESS(f'🎉 {created_count} nieuwe voertuigen succesvol aangemaakt!')
        )
