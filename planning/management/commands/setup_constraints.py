from django.core.management.base import BaseCommand
from planning.models import PlanningConstraint


class Command(BaseCommand):
    help = 'Installeer default planning constraints'

    def handle(self, *args, **options):
        constraints_data = [
            {
                'name': 'Voertuig Capaciteit',
                'description': 'Voertuig mag niet overbeladen worden. Controleert of het totale aantal patiënten per voertuig niet de capaciteit overschrijdt.',
                'constraint_type': 'vehicle_capacity',
                'weight': 'HARD',
                'penalty': 1000000,
                'parameters': {
                    'max_capacity': 7,
                    'description': 'Maximum aantal patiënten per voertuig'
                }
            },
            {
                'name': 'Voertuig Speciale Capaciteit',
                'description': 'Speciale patiënten (rolstoel) mogen voertuig niet overbeladen. Controleert speciale capaciteit voor rolstoelpatiënten.',
                'constraint_type': 'vehicle_special_capacity',
                'weight': 'HARD',
                'penalty': 1000000,
                'parameters': {
                    'max_special_capacity': 2,
                    'description': 'Maximum aantal rolstoelpatiënten per voertuig'
                }
            },
            {
                'name': 'Voertuig Rijtijd',
                'description': 'Voertuig mag niet langer rijden dan toegestaan. Maximum 60 minuten vanaf eerste patiënt ophaal.',
                'constraint_type': 'vehicle_drive_time',
                'weight': 'HARD',
                'penalty': 1000000,
                'parameters': {
                    'max_drive_time_minutes': 60,
                    'description': 'Maximum rijtijd in minuten vanaf eerste ophaal'
                }
            },
            {
                'name': 'Afstand Kosten',
                'description': 'Minimaliseer de totale rijkosten. Soft constraint voor kostenoptimalisatie.',
                'constraint_type': 'distance_cost',
                'weight': 'SOFT',
                'penalty': 1,
                'parameters': {
                    'km_rate': 0.50,
                    'description': 'Kosten per kilometer'
                }
            },
            {
                'name': 'Voorkeurs Voertuig',
                'description': 'Patiënten moeten in hun voorkeursvoertuig geplaatst worden indien gespecificeerd.',
                'constraint_type': 'preferred_vehicle',
                'weight': 'HARD',
                'penalty': 1000000,
                'parameters': {
                    'strict_enforcement': True,
                    'description': 'Strikt afdwingen van voorkeursvoertuig'
                }
            },
            {
                'name': 'DRV Aantal',
                'description': 'Beperk aantal DRV patiënten per voertuig. Maximum 1 DRV patiënt per voertuig.',
                'constraint_type': 'drv_count',
                'weight': 'SOFT',
                'penalty': 600000,
                'parameters': {
                    'max_drv_per_vehicle': 1,
                    'description': 'Maximum aantal DRV patiënten per voertuig'
                }
            }
        ]

        created_count = 0
        updated_count = 0

        for constraint_data in constraints_data:
            constraint, created = PlanningConstraint.objects.update_or_create(
                constraint_type=constraint_data['constraint_type'],
                defaults={
                    'name': constraint_data['name'],
                    'description': constraint_data['description'],
                    'weight': constraint_data['weight'],
                    'penalty': constraint_data['penalty'],
                    'parameters': constraint_data['parameters'],
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Constraint aangemaakt: {constraint.name}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'🔄 Constraint bijgewerkt: {constraint.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 Constraint setup voltooid!\n'
                f'📊 Aangemaakt: {created_count}\n'
                f'🔄 Bijgewerkt: {updated_count}\n'
                f'📋 Totaal actief: {PlanningConstraint.objects.filter(is_active=True).count()}'
            )
        )
