from django.core.management.base import BaseCommand
from planning.models import TimeSlot
from datetime import time

class Command(BaseCommand):
    help = 'Maak simpele tijdblokken met één tijd per blok'

    def handle(self, *args, **options):
        self.stdout.write("🔧 CREATING SIMPLE TIME BLOCKS\n")
        
        # Reset alle tijdblokken
        TimeSlot.objects.all().delete()
        
        # HALEN blokken (één tijd)
        halen_blocks = [
            {
                'naam': 'Halen 08:00',
                'heen_start_tijd': time(8, 0),   
                'heen_eind_tijd': time(10, 0),   # 2 uur window voor behandelingen
                'terug_start_tijd': time(14, 0), 
                'terug_eind_tijd': time(16, 0),
                'actief': True
            },
            {
                'naam': 'Halen 10:00',
                'heen_start_tijd': time(10, 0),  
                'heen_eind_tijd': time(12, 0),   
                'terug_start_tijd': time(15, 0), 
                'terug_eind_tijd': time(17, 0),
                'actief': True
            },
            {
                'naam': 'Halen 12:00',
                'heen_start_tijd': time(12, 0),  
                'heen_eind_tijd': time(14, 0),   
                'terug_start_tijd': time(16, 0), 
                'terug_eind_tijd': time(18, 0),
                'actief': True
            }
        ]
        
        # BRINGEN blokken (één tijd)
        bringen_blocks = [
            {
                'naam': 'Bringen 12:00',
                'heen_start_tijd': time(10, 0),  # Laatste behandeling window
                'heen_eind_tijd': time(12, 0),   
                'terug_start_tijd': time(12, 0), # Wegbrengen om 12:00
                'terug_eind_tijd': time(14, 0),
                'actief': True
            },
            {
                'naam': 'Bringen 14:00',
                'heen_start_tijd': time(12, 0),  
                'heen_eind_tijd': time(14, 0),   
                'terug_start_tijd': time(14, 0), # Wegbrengen om 14:00
                'terug_eind_tijd': time(16, 0),
                'actief': True
            },
            {
                'naam': 'Bringen 16:00',
                'heen_start_tijd': time(14, 0),  
                'heen_eind_tijd': time(16, 0),   
                'terug_start_tijd': time(16, 0), # Wegbrengen om 16:00
                'terug_eind_tijd': time(18, 0),
                'actief': True
            },
            {
                'naam': 'Bringen 18:00',
                'heen_start_tijd': time(16, 0),  
                'heen_eind_tijd': time(18, 0),   
                'terug_start_tijd': time(18, 0), # Wegbrengen om 18:00
                'terug_eind_tijd': time(20, 0),
                'actief': True
            }
        ]
        
        # Maak HALEN blokken
        self.stdout.write("📥 HALEN BLOKKEN:")
        for data in halen_blocks:
            timeslot = TimeSlot.objects.create(**data)
            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✅ {data['naam']}: Behandelingen {data['heen_start_tijd']}-{data['heen_eind_tijd']}"
                )
            )
        
        # Maak BRINGEN blokken
        self.stdout.write("\n📤 BRINGEN BLOKKEN:")
        for data in bringen_blocks:
            timeslot = TimeSlot.objects.create(**data)
            wegbreng_tijd = data['terug_start_tijd']
            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✅ {data['naam']}: Laatste behandeling {data['heen_start_tijd']}-{data['heen_eind_tijd']} → Wegbrengen om {wegbreng_tijd}"
                )
            )
        
        total_created = len(halen_blocks) + len(bringen_blocks)
        self.stdout.write(
            self.style.SUCCESS(f"\n🎉 {total_created} tijdblokken aangemaakt!")
        )
        
        self.stdout.write("\n📋 SIMPELE LOGICA:")
        self.stdout.write("🔹 HALEN: Behandeling om 09:30 → 'Halen 08:00' blok")
        self.stdout.write("🔹 BRINGEN: Laatste behandeling 13:00 → 'Bringen 14:00' blok")
