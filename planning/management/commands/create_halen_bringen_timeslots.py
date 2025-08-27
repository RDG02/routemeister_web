from django.core.management.base import BaseCommand
from planning.models import TimeSlot
from datetime import time

class Command(BaseCommand):
    help = 'Maak tijdblokken voor HALEN en BRINGEN met correcte logica'

    def handle(self, *args, **options):
        self.stdout.write("🔧 CREATING HALEN & BRINGEN TIMESLOTS\n")
        
        # Reset alle tijdblokken
        TimeSlot.objects.all().delete()
        
        # HALEN tijdblokken (gebaseerd op eerste behandeltijd)
        halen_timeslots = [
            {
                'naam': 'Holen 0800 Uhr',
                'heen_start_tijd': time(8, 0),   # Behandelingen 08:00-10:00
                'heen_eind_tijd': time(10, 0),   
                'terug_start_tijd': time(14, 0), # Terugbrengen later
                'terug_eind_tijd': time(16, 0),
                'actief': True
            },
            {
                'naam': 'Holen 1000 Uhr',
                'heen_start_tijd': time(10, 0),  # Behandelingen 10:00-12:00
                'heen_eind_tijd': time(12, 0),   
                'terug_start_tijd': time(15, 0), 
                'terug_eind_tijd': time(17, 0),
                'actief': True
            },
            {
                'naam': 'Holen 1200 Uhr',
                'heen_start_tijd': time(12, 0),  # Behandelingen 12:00-14:00
                'heen_eind_tijd': time(14, 0),   
                'terug_start_tijd': time(16, 0), 
                'terug_eind_tijd': time(18, 0),
                'actief': True
            }
        ]
        
        # BRINGEN tijdblokken (gebaseerd op laatste behandeltijd)
        bringen_timeslots = [
            {
                'naam': 'Bringen 1400 Uhr',
                'heen_start_tijd': time(12, 0),  # Laatste behandeling 12:00-14:00
                'heen_eind_tijd': time(14, 0),   # Wegbrengen om 14:00
                'terug_start_tijd': time(14, 0), 
                'terug_eind_tijd': time(16, 0),
                'actief': True
            },
            {
                'naam': 'Bringen 1600 Uhr',
                'heen_start_tijd': time(14, 0),  # Laatste behandeling 14:00-16:00
                'heen_eind_tijd': time(16, 0),   # Wegbrengen om 16:00
                'terug_start_tijd': time(16, 0), 
                'terug_eind_tijd': time(18, 0),
                'actief': True
            },
            {
                'naam': 'Bringen 1800 Uhr',
                'heen_start_tijd': time(16, 0),  # Laatste behandeling 16:00-18:00
                'heen_eind_tijd': time(18, 0),   # Wegbrengen om 18:00
                'terug_start_tijd': time(18, 0), 
                'terug_eind_tijd': time(20, 0),
                'actief': True
            }
        ]
        
        # Maak HALEN tijdblokken
        for data in halen_timeslots:
            timeslot = TimeSlot.objects.create(**data)
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ {data['naam']}: Eerste behandeling {data['heen_start_tijd']}-{data['heen_eind_tijd']}"
                )
            )
        
        # Maak BRINGEN tijdblokken
        for data in bringen_timeslots:
            timeslot = TimeSlot.objects.create(**data)
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ {data['naam']}: Laatste behandeling {data['heen_start_tijd']}-{data['heen_eind_tijd']}"
                )
            )
        
        total_created = len(halen_timeslots) + len(bringen_timeslots)
        self.stdout.write(
            self.style.SUCCESS(f"\n🎉 {total_created} tijdblokken aangemaakt!")
        )
        
        self.stdout.write("\n📋 LOGICA:")
        self.stdout.write("🔹 HALEN: Eerste behandeltijd bepaalt tijdsblok")
        self.stdout.write("   • Patient behandeling 09:30 → 'Holen 0800 Uhr' → Aanwezig 08:00")
        self.stdout.write("🔹 BRINGEN: Laatste behandeltijd bepaalt tijdsblok") 
        self.stdout.write("   • Patient laatste behandeling 13:00 → 'Bringen 1400 Uhr' → Wegbrengen 14:00")
