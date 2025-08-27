from django.core.management.base import BaseCommand
from planning.models import Patient, TimeSlot

class Command(BaseCommand):
    help = 'Verwijder alle patiënt data voor een nieuwe upload'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Bevestig dat je alle data wilt verwijderen',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING(
                    'Dit commando verwijdert ALLE patiënt data!\n'
                    'Gebruik --confirm om door te gaan: python manage.py cleanup_data --confirm'
                )
            )
            return

        # Tel huidige data
        patient_count = Patient.objects.count()
        timeslot_count = TimeSlot.objects.filter(actief=True).count()

        self.stdout.write(f'Gevonden: {patient_count} patiënten en {timeslot_count} actieve tijdblokken')

        # Verwijder alle patiënten
        Patient.objects.all().delete()
        self.stdout.write(
            self.style.SUCCESS(f'✅ {patient_count} patiënten verwijderd')
        )

        # Reset tijdblokken (optioneel)
        TimeSlot.objects.update(actief=False)
        self.stdout.write(
            self.style.SUCCESS(f'✅ {timeslot_count} tijdblokken gedeactiveerd')
        )

        self.stdout.write(
            self.style.SUCCESS(
                '\n🎉 Database opgeschoond! Je kunt nu een nieuw CSV bestand uploaden.'
            )
        )
