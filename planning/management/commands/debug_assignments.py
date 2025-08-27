from django.core.management.base import BaseCommand
from planning.models import Patient, TimeSlot, Vehicle
from datetime import datetime, time

class Command(BaseCommand):
    help = 'Debug waarom patiënten niet worden toegewezen aan tijdblokken'

    def handle(self, *args, **options):
        self.stdout.write("🔍 DEBUGGING PATIENT ASSIGNMENTS\n")
        
        # Alle patiënten
        all_patients = Patient.objects.all().order_by('ophaal_tijd')
        self.stdout.write(f"📊 Totaal aantal patiënten: {all_patients.count()}")
        
        # Toegewezen vs niet-toegewezen
        assigned_patients = Patient.objects.filter(toegewezen_tijdblok__isnull=False)
        unassigned_patients = Patient.objects.filter(toegewezen_tijdblok__isnull=True)
        
        self.stdout.write(f"✅ Toegewezen: {assigned_patients.count()}")
        self.stdout.write(f"❌ Niet toegewezen: {unassigned_patients.count()}\n")
        
        # Actieve tijdblokken
        active_timeslots = TimeSlot.objects.filter(actief=True).order_by('heen_start_tijd')
        self.stdout.write(f"⏰ Actieve tijdblokken: {active_timeslots.count()}")
        for timeslot in active_timeslots:
            patient_count = Patient.objects.filter(toegewezen_tijdblok=timeslot).count()
            self.stdout.write(f"  - {timeslot.naam}: {timeslot.heen_start_tijd}-{timeslot.heen_eind_tijd} → {timeslot.terug_start_tijd}-{timeslot.terug_eind_tijd} ({patient_count} patiënten)")
        
        # Voertuigen
        available_vehicles = Vehicle.objects.filter(status='beschikbaar')
        total_capacity = sum(vehicle.aantal_zitplaatsen - 1 for vehicle in available_vehicles)
        self.stdout.write(f"\n🚗 Beschikbare voertuigen: {available_vehicles.count()}")
        self.stdout.write(f"🪑 Totale capaciteit: {total_capacity} patiënten")
        
        # Analyseer elke niet-toegewezen patiënt
        self.stdout.write(f"\n🔍 ANALYSE NIET-TOEGEWEZEN PATIËNTEN:")
        for patient in unassigned_patients:
            self.stdout.write(f"\n👤 {patient.naam}")
            self.stdout.write(f"   📍 {patient.plaats}")
            self.stdout.write(f"   🕐 Ophaal: {patient.ophaal_tijd.strftime('%H:%M')}")
            self.stdout.write(f"   🕐 Eind behandeling: {patient.eind_behandel_tijd.strftime('%H:%M')}")
            
            # Check welke tijdblokken zouden kunnen passen
            matching_slots = []
            for timeslot in active_timeslots:
                # Check of ophaal tijd binnen haal blok valt
                ophaal_tijd_obj = patient.ophaal_tijd.time()
                if timeslot.heen_start_tijd <= ophaal_tijd_obj <= timeslot.heen_eind_tijd:
                    # Check of eind behandel tijd past binnen breng blok
                    eind_tijd_obj = patient.eind_behandel_tijd.time()
                    if eind_tijd_obj <= timeslot.terug_eind_tijd:
                        # Check capaciteit
                        current_patients = Patient.objects.filter(toegewezen_tijdblok=timeslot).count()
                        if current_patients < total_capacity:
                            matching_slots.append((timeslot, current_patients))
            
            if matching_slots:
                self.stdout.write(f"   ✅ Zou kunnen passen in:")
                for slot, count in matching_slots:
                    self.stdout.write(f"      - {slot.naam} (nu {count} patiënten)")
            else:
                self.stdout.write(f"   ❌ Past in geen enkel tijdblok:")
                self.stdout.write(f"      Ophaal {patient.ophaal_tijd.strftime('%H:%M')} moet tussen haal tijden vallen")
                self.stdout.write(f"      Eind {patient.eind_behandel_tijd.strftime('%H:%M')} moet voor breng eindtijd zijn")
        
        # Toon toegewezen patiënten
        self.stdout.write(f"\n✅ TOEGEWEZEN PATIËNTEN:")
        for patient in assigned_patients:
            self.stdout.write(f"👤 {patient.naam} → {patient.toegewezen_tijdblok.naam}")
            self.stdout.write(f"   🕐 {patient.ophaal_tijd.strftime('%H:%M')} - {patient.eind_behandel_tijd.strftime('%H:%M')}")
