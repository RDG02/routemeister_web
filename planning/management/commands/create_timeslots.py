from django.core.management.base import BaseCommand
from planning.models import TimeSlot
from datetime import time


class Command(BaseCommand):
    help = 'Maak standaard tijdblokken aan tussen 8:00 en 17:00'

    def handle(self, *args, **options):
        # Verwijder bestaande tijdblokken eerst (optioneel)
        TimeSlot.objects.all().delete()
        
        # Definieer tijdblokken (heen_start, heen_eind, terug_start, terug_eind)
        timeslots = [
            {
                'naam': 'Ochtend Blok 1',
                'heen_start': time(8, 0),   # 08:00
                'heen_eind': time(8, 30),   # 08:30
                'terug_start': time(10, 0), # 10:00
                'terug_eind': time(10, 30), # 10:30
                'max_rijtijd': 60,
                'max_patienten': 4
            },
            {
                'naam': 'Ochtend Blok 2',
                'heen_start': time(8, 30),
                'heen_eind': time(9, 0),
                'terug_start': time(10, 30),
                'terug_eind': time(11, 0),
                'max_rijtijd': 60,
                'max_patienten': 4
            },
            {
                'naam': 'Ochtend Blok 3',
                'heen_start': time(9, 0),
                'heen_eind': time(9, 30),
                'terug_start': time(11, 0),
                'terug_eind': time(11, 30),
                'max_rijtijd': 60,
                'max_patienten': 4
            },
            {
                'naam': 'Ochtend Blok 4',
                'heen_start': time(9, 30),
                'heen_eind': time(10, 0),
                'terug_start': time(11, 30),
                'terug_eind': time(12, 0),
                'max_rijtijd': 60,
                'max_patienten': 4
            },
            {
                'naam': 'Middag Blok 1',
                'heen_start': time(12, 0),
                'heen_eind': time(12, 30),
                'terug_start': time(14, 0),
                'terug_eind': time(14, 30),
                'max_rijtijd': 60,
                'max_patienten': 4
            },
            {
                'naam': 'Middag Blok 2',
                'heen_start': time(12, 30),
                'heen_eind': time(13, 0),
                'terug_start': time(14, 30),
                'terug_eind': time(15, 0),
                'max_rijtijd': 60,
                'max_patienten': 4
            },
            {
                'naam': 'Middag Blok 3',
                'heen_start': time(13, 0),
                'heen_eind': time(13, 30),
                'terug_start': time(15, 0),
                'terug_eind': time(15, 30),
                'max_rijtijd': 60,
                'max_patienten': 4
            },
            {
                'naam': 'Middag Blok 4',
                'heen_start': time(13, 30),
                'heen_eind': time(14, 0),
                'terug_start': time(15, 30),
                'terug_eind': time(16, 0),
                'max_rijtijd': 60,
                'max_patienten': 4
            },
            {
                'naam': 'Namiddag Blok 1',
                'heen_start': time(14, 0),
                'heen_eind': time(14, 30),
                'terug_start': time(16, 0),
                'terug_eind': time(16, 30),
                'max_rijtijd': 60,
                'max_patienten': 4
            },
            {
                'naam': 'Namiddag Blok 2',
                'heen_start': time(14, 30),
                'heen_eind': time(15, 0),
                'terug_start': time(16, 30),
                'terug_eind': time(17, 0),
                'max_rijtijd': 60,
                'max_patienten': 4
            }
        ]
        
        created_count = 0
        for slot_data in timeslots:
            timeslot = TimeSlot.objects.create(
                naam=slot_data['naam'],
                heen_start_tijd=slot_data['heen_start'],
                heen_eind_tijd=slot_data['heen_eind'],
                terug_start_tijd=slot_data['terug_start'],
                terug_eind_tijd=slot_data['terug_eind'],
                max_rijtijd_minuten=slot_data['max_rijtijd'],
                max_patienten_per_rit=slot_data['max_patienten'],
                actief=True,
                dag_van_week='alle_dagen'
            )
            created_count += 1
            self.stdout.write(f"✅ {timeslot.naam} aangemaakt")
        
        self.stdout.write(
            self.style.SUCCESS(f'🎉 {created_count} tijdblokken succesvol aangemaakt!')
        )
