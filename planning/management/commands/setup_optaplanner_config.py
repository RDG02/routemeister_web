from django.core.management.base import BaseCommand
from planning.models import Configuration


class Command(BaseCommand):
    help = 'Setup standaard OptaPlanner configuratie in de database'

    def handle(self, *args, **options):
        self.stdout.write('Setting up OptaPlanner configuration...')
        
        # OptaPlanner configuraties
        configs = [
            {
                'key': 'OPTAPLANNER_URL',
                'value': 'http://localhost:8080',
                'description': 'URL van de OptaPlanner server (development)'
            },
            {
                'key': 'OPTAPLANNER_ENABLED',
                'value': 'True',
                'description': 'Of OptaPlanner route optimalisatie is ingeschakeld'
            },
            {
                'key': 'OPTAPLANNER_TIMEOUT',
                'value': '30',
                'description': 'Timeout in seconden voor OptaPlanner API calls'
            },
            {
                'key': 'OPTAPLANNER_MAX_RETRIES',
                'value': '3',
                'description': 'Maximum aantal retry pogingen voor OptaPlanner calls'
            },
            {
                'key': 'OPTAPLANNER_PRODUCTION_URL',
                'value': 'https://opta01.myidbv.com',
                'description': 'URL van de OptaPlanner server (production)'
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for config_data in configs:
            config, created = Configuration.objects.get_or_create(
                key=config_data['key'],
                defaults={
                    'value': config_data['value'],
                    'description': config_data['description'],
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'  ✅ Created: {config.key}')
            else:
                # Update bestaande configuratie
                config.value = config_data['value']
                config.description = config_data['description']
                config.save()
                updated_count += 1
                self.stdout.write(f'  🔄 Updated: {config.key}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nOptaPlanner configuratie setup voltooid!\n'
                f'Created: {created_count}, Updated: {updated_count}'
            )
        )
        
        self.stdout.write('\nBeschikbare configuraties:')
        for config in Configuration.objects.filter(is_active=True).order_by('key'):
            self.stdout.write(f'  {config.key}: {config.value}')
