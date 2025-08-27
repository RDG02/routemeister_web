from django.core.management.base import BaseCommand
from planning.models import TimeSlot
from datetime import time

class Command(BaseCommand):
    help = 'Pas tijdblokken aan zodat ze beter passen bij patiënt tijden'

    def handle(self, *args, **options):
        self.stdout.write("🔧 FIXING TIMESLOTS FOR BETTER PATIENT MATCHING\n")
        
        # Nieuwe tijdblok definities gebaseerd op de patiënt data
        new_timeslots = {
            'Haal Blok 1': {
                'heen_start_tijd': time(8, 0),   # 08:00
                'heen_eind_tijd': time(9, 0),    # 09:00  
                'terug_start_tijd': time(14, 0), # 14:00
                'terug_eind_tijd': time(16, 0),  # 16:00
            },
            'Haal Blok 2': {
                'heen_start_tijd': time(9, 0),   # 09:00
                'heen_eind_tijd': time(11, 0),   # 11:00
                'terug_start_tijd': time(15, 0), # 15:00
                'terug_eind_tijd': time(17, 0),  # 17:00
            },
            'Haal Blok 3': {
                'heen_start_tijd': time(11, 0),  # 11:00
                'heen_eind_tijd': time(13, 0),   # 13:00
                'terug_start_tijd': time(16, 0), # 16:00
                'terug_eind_tijd': time(18, 0),  # 18:00
            },
            'Breng Blok 1': {
                'heen_start_tijd': time(14, 0),  # 14:00
                'heen_eind_tijd': time(16, 0),   # 16:00
                'terug_start_tijd': time(16, 0), # 16:00
                'terug_eind_tijd': time(18, 0),  # 18:00
            },
        }
        
        # Update bestaande tijdblokken
        updated_count = 0
        for naam, tijden in new_timeslots.items():
            try:
                timeslot = TimeSlot.objects.get(naam=naam)
                timeslot.heen_start_tijd = tijden['heen_start_tijd']
                timeslot.heen_eind_tijd = tijden['heen_eind_tijd']
                timeslot.terug_start_tijd = tijden['terug_start_tijd']
                timeslot.terug_eind_tijd = tijden['terug_eind_tijd']
                timeslot.actief = True
                timeslot.save()
                updated_count += 1
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ {naam}: {tijden['heen_start_tijd']}-{tijden['heen_eind_tijd']} → {tijden['terug_start_tijd']}-{tijden['terug_eind_tijd']}"
                    )
                )
            except TimeSlot.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"⚠️  Tijdblok '{naam}' niet gevonden")
                )
        
        # Deactiveer Breng Blok 2 en 3 (niet meer nodig)
        for naam in ['Breng Blok 2', 'Breng Blok 3']:
            try:
                timeslot = TimeSlot.objects.get(naam=naam)
                timeslot.actief = False
                timeslot.save()
                self.stdout.write(
                    self.style.WARNING(f"🔄 {naam} gedeactiveerd")
                )
            except TimeSlot.DoesNotExist:
                pass
        
        self.stdout.write(
            self.style.SUCCESS(f"\n🎉 {updated_count} tijdblokken aangepast!")
        )
        
        self.stdout.write("\n📋 NIEUWE TIJDBLOK DEKKING:")
        self.stdout.write("• Haal Blok 1 (08:00-09:00): Voor vroege patiënten zoals Anette & Wilfried")
        self.stdout.write("• Haal Blok 2 (09:00-11:00): Voor middagochtend patiënten")  
        self.stdout.write("• Haal Blok 3 (11:00-13:00): Voor late ochtend patiënten")
        self.stdout.write("• Breng Blok 1 (14:00-16:00): Voor terugbrengen")
        self.stdout.write("\n💡 Probeer nu opnieuw de automatische toewijzing!")
