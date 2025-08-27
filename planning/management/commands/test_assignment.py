from django.core.management.base import BaseCommand
from planning.models import Patient, TimeSlot, Vehicle
from datetime import time

class Command(BaseCommand):
    help = 'Test de automatische toewijzing simulatie'

    def handle(self, *args, **options):
        self.stdout.write("🧪 TESTING AUTOMATIC ASSIGNMENT\n")
        
        # Reset alle toewijzingen
        Patient.objects.update(toegewezen_tijdblok=None, status='nieuw')
        
        # Haal alle data op
        active_timeslots = TimeSlot.objects.filter(actief=True).order_by('heen_start_tijd')
        unassigned_patients = Patient.objects.filter(toegewezen_tijdblok__isnull=True).order_by('ophaal_tijd')
        available_vehicles = Vehicle.objects.filter(status='beschikbaar')
        total_capacity = sum(vehicle.aantal_zitplaatsen - 1 for vehicle in available_vehicles)
        
        self.stdout.write(f"📊 {unassigned_patients.count()} patiënten, {active_timeslots.count()} tijdblokken, capaciteit: {total_capacity}")
        
        # Simuleer de toewijzing
        assigned_count = 0
        
        for patient in unassigned_patients:
            if not patient.ophaal_tijd:
                continue
                
            best_timeslot = None
            
            # Zoek HALEN tijdblokken
            halen_timeslots = [ts for ts in active_timeslots if "Halen" in ts.naam]
            bringen_timeslots = [ts for ts in active_timeslots if "Bringen" in ts.naam]
            
            # Probeer HALEN eerst
            for timeslot in halen_timeslots:
                eerste_behandeling = patient.ophaal_tijd.time()
                if timeslot.heen_start_tijd <= eerste_behandeling <= timeslot.heen_eind_tijd:
                    current_patients = Patient.objects.filter(toegewezen_tijdblok=timeslot).count()
                    if current_patients < total_capacity:
                        best_timeslot = timeslot
                        break
            
            # Als geen HALEN, probeer BRINGEN
            if not best_timeslot and patient.eind_behandel_tijd:
                laatste_behandeling = patient.eind_behandel_tijd.time()
                bringen_sorted = sorted(bringen_timeslots, key=lambda ts: ts.terug_start_tijd)
                
                for timeslot in bringen_sorted:
                    wegbreng_tijd = timeslot.terug_start_tijd
                    if laatste_behandeling <= wegbreng_tijd:
                        current_patients = Patient.objects.filter(toegewezen_tijdblok=timeslot).count()
                        if current_patients < total_capacity:
                            best_timeslot = timeslot
                            break
            
            # Toewijzen
            if best_timeslot:
                patient.toegewezen_tijdblok = best_timeslot
                patient.status = 'gepland'
                patient.save()
                assigned_count += 1
                
                # Bepaal type
                is_halen = "Halen" in best_timeslot.naam
                behandeltijd = patient.ophaal_tijd.strftime('%H:%M')
                eindtijd = patient.eind_behandel_tijd.strftime('%H:%M') if patient.eind_behandel_tijd else "?"
                
                self.stdout.write(
                    f"✅ {patient.naam}: {behandeltijd}-{eindtijd} → {best_timeslot.naam} {'(HALEN)' if is_halen else '(BRINGEN)'}"
                )
            else:
                behandeltijd = patient.ophaal_tijd.strftime('%H:%M')
                eindtijd = patient.eind_behandel_tijd.strftime('%H:%M') if patient.eind_behandel_tijd else "?"
                self.stdout.write(
                    self.style.WARNING(f"❌ {patient.naam}: {behandeltijd}-{eindtijd} → Geen tijdblok gevonden")
                )
        
        self.stdout.write(f"\n🎉 RESULTAAT: {assigned_count}/{unassigned_patients.count()} patiënten toegewezen!")
        
        # Toon overzicht per tijdblok
        self.stdout.write("\n📋 OVERZICHT PER TIJDBLOK:")
        for timeslot in active_timeslots:
            patients_in_slot = Patient.objects.filter(toegewezen_tijdblok=timeslot)
            if patients_in_slot.exists():
                self.stdout.write(f"🔸 {timeslot.naam}: {patients_in_slot.count()} patiënten")
                for p in patients_in_slot:
                    behandeltijd = p.ophaal_tijd.strftime('%H:%M')
                    eindtijd = p.eind_behandel_tijd.strftime('%H:%M') if p.eind_behandel_tijd else "?"
                    self.stdout.write(f"   • {p.naam} ({behandeltijd}-{eindtijd})")
            else:
                self.stdout.write(f"🔹 {timeslot.naam}: 0 patiënten")
