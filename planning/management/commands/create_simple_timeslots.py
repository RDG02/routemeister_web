from django.core.management.base import BaseCommand
from planning.models import TimeSlot
from datetime import time

class Command(BaseCommand):
    help = 'Maak simpele tijdblokken gebaseerd op behandeltijden'

    def handle(self, *args, **options):
        self.stdout.write("🔧 CREATING SIMPLE TIMESLOTS BASED ON TREATMENT TIMES\n")
        
        # Reset alle tijdblokken
        TimeSlot.objects.all().delete()
        
        # Simpele tijdblokken gebaseerd op behandeltijden
        simple_timeslots = [
            {
                'naam': 'Holen 0800 Uhr',
                'heen_start_tijd': time(8, 0),   # Behandelingen tussen 08:00-10:00
                'heen_eind_tijd': time(10, 0),   
                'terug_start_tijd': time(14, 0), # Terugbrengen 14:00-16:00
                'terug_eind_tijd': time(16, 0),
                'actief': True
            },
            {
                'naam': 'Holen 1000 Uhr',
                'heen_start_tijd': time(10, 0),  # Behandelingen tussen 10:00-12:00
                'heen_eind_tijd': time(12, 0),   
                'terug_start_tijd': time(15, 0), # Terugbrengen 15:00-17:00
                'terug_eind_tijd': time(17, 0),
                'actief': True
            },
            {
                'naam': 'Holen 1200 Uhr',
                'heen_start_tijd': time(12, 0),  # Behandelingen tussen 12:00-14:00
                'heen_eind_tijd': time(14, 0),   
                'terug_start_tijd': time(16, 0), # Terugbrengen 16:00-18:00
                'terug_eind_tijd': time(18, 0),
                'actief': True
            },
            {
                'naam': 'Bringen 1400 Uhr',
                'heen_start_tijd': time(14, 0),  # Voor terugbrengen
                'heen_eind_tijd': time(16, 0),   
                'terug_start_tijd': time(16, 0), 
                'terug_eind_tijd': time(18, 0),
                'actief': True
            }
        ]
        
        # Maak nieuwe tijdblokken
        created_count = 0
        for data in simple_timeslots:
            timeslot = TimeSlot.objects.create(**data)
            created_count += 1
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ {data['naam']}: Behandelingen {data['heen_start_tijd']}-{data['heen_eind_tijd']}"
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS(f"\n🎉 {created_count} nieuwe tijdblokken aangemaakt!")
        )
        
        self.stdout.write("\n📋 LOGICA:")
        self.stdout.write("• Behandeltijd bepaalt het tijdsblok")
        self.stdout.write("• Anette behandeling 08:45 → 'Holen 0800 Uhr' (08:00-10:00)")
        self.stdout.write("• Ophaaltijd wordt automatisch vóór tijdsblok gepland")
        self.stdout.write("• Bijvoorbeeld: ophalen 07:45 → aankomst 08:00 → behandeling 08:45")
