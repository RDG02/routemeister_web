from django.core.management.base import BaseCommand
from planning.models import Patient, TimeSlot, Vehicle
from datetime import time

class Command(BaseCommand):
    help = 'Wijs HALEN en BRINGEN tijdblokken toe aan patiënten'

    def handle(self, *args, **options):
        self.stdout.write("🚀 ASSIGNING HALEN & BRINGEN TIJDBLOKKEN\n")
        
        # Reset alle toewijzingen
        Patient.objects.update(halen_tijdblok=None, bringen_tijdblok=None, status='nieuw')
        
        # Haal data op
        active_timeslots = TimeSlot.objects.filter(actief=True)
        halen_timeslots = [ts for ts in active_timeslots if "Halen" in ts.naam]
        bringen_timeslots = [ts for ts in active_timeslots if "Bringen" in ts.naam]
        unassigned_patients = Patient.objects.all().order_by('ophaal_tijd')
        
        available_vehicles = Vehicle.objects.filter(status='beschikbaar')
        total_capacity = sum(vehicle.aantal_zitplaatsen - 1 for vehicle in available_vehicles)
        
        self.stdout.write(f"📊 {unassigned_patients.count()} patiënten")
        self.stdout.write(f"📥 {len(halen_timeslots)} HALEN tijdblokken")
        self.stdout.write(f"📤 {len(bringen_timeslots)} BRINGEN tijdblokken")
        self.stdout.write(f"🚗 Capaciteit: {total_capacity} per tijdblok\n")
        
        fully_assigned = 0
        partial_assigned = 0
        
        for patient in unassigned_patients:
            if not patient.ophaal_tijd or not patient.eind_behandel_tijd:
                continue
                
            halen_assigned = False
            bringen_assigned = False
            
            # 1. HALEN tijdblok toewijzen
            eerste_behandeling = patient.ophaal_tijd.time()
            for timeslot in halen_timeslots:
                if timeslot.heen_start_tijd <= eerste_behandeling <= timeslot.heen_eind_tijd:
                    current_patients = Patient.objects.filter(halen_tijdblok=timeslot).count()
                    if current_patients < total_capacity:
                        patient.halen_tijdblok = timeslot
                        halen_assigned = True
                        break
            
            # 2. BRINGEN tijdblok toewijzen
            laatste_behandeling = patient.eind_behandel_tijd.time()
            bringen_sorted = sorted(bringen_timeslots, key=lambda ts: ts.terug_start_tijd)
            
            for timeslot in bringen_sorted:
                wegbreng_tijd = timeslot.terug_start_tijd
                if laatste_behandeling <= wegbreng_tijd:
                    current_patients = Patient.objects.filter(bringen_tijdblok=timeslot).count()
                    if current_patients < total_capacity:
                        patient.bringen_tijdblok = timeslot
                        bringen_assigned = True
                        break
            
            # 3. Status bepalen en opslaan
            if halen_assigned and bringen_assigned:
                patient.status = 'gepland'
                fully_assigned += 1
                status_icon = "✅"
            elif halen_assigned or bringen_assigned:
                patient.status = 'gedeeltelijk_gepland'
                partial_assigned += 1
                status_icon = "⚠️"
            else:
                status_icon = "❌"
            
            patient.save()
            
            # Toon resultaat
            behandeltijd = patient.ophaal_tijd.strftime('%H:%M')
            eindtijd = patient.eind_behandel_tijd.strftime('%H:%M')
            halen_naam = patient.halen_tijdblok.naam if patient.halen_tijdblok else "Geen"
            bringen_naam = patient.bringen_tijdblok.naam if patient.bringen_tijdblok else "Geen"
            
            self.stdout.write(
                f"{status_icon} {patient.naam}: {behandeltijd}-{eindtijd}"
            )
            self.stdout.write(f"   📥 HALEN: {halen_naam}")
            self.stdout.write(f"   📤 BRINGEN: {bringen_naam}\n")
        
        self.stdout.write(f"🎉 RESULTAAT:")
        self.stdout.write(f"   ✅ Volledig toegewezen: {fully_assigned}")
        self.stdout.write(f"   ⚠️  Gedeeltelijk toegewezen: {partial_assigned}")
        self.stdout.write(f"   ❌ Niet toegewezen: {unassigned_patients.count() - fully_assigned - partial_assigned}")
        
        # Overzicht per tijdblok
        self.stdout.write(f"\n📋 OVERZICHT PER TIJDBLOK:")
        
        self.stdout.write("📥 HALEN TIJDBLOKKEN:")
        for timeslot in halen_timeslots:
            count = Patient.objects.filter(halen_tijdblok=timeslot).count()
            self.stdout.write(f"   🔸 {timeslot.naam}: {count} patiënten")
        
        self.stdout.write("\n📤 BRINGEN TIJDBLOKKEN:")
        for timeslot in bringen_timeslots:
            count = Patient.objects.filter(bringen_tijdblok=timeslot).count()
            self.stdout.write(f"   🔸 {timeslot.naam}: {count} patiënten")
