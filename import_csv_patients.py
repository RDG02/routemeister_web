#!/usr/bin/env python
"""
Script om patiënten uit CSV bestand te importeren
"""
import os
import sys
import django
from datetime import date, time, datetime

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, TimeSlot, Vehicle
from planning.views import convert_time_format

def import_csv_patients():
    """Importeer patiënten uit CSV bestand"""
    print("🔍 IMPORTING PATIENTS FROM CSV")
    print("=" * 50)
    
    today = date.today()
    print(f"📅 Vandaag: {today}")
    
    # Lees CSV bestand
    csv_file = 'routemeister_25082025.csv'
    
    if not os.path.exists(csv_file):
        print(f"❌ CSV bestand niet gevonden: {csv_file}")
        return
    
    patients_data = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
                
            # Parse CSV regel (semicolon separated)
            parts = line.split(';')
            if len(parts) < 15:
                print(f"⚠️ Regel {line_num} heeft te weinig kolommen: {len(parts)}")
                continue
            
            try:
                patient_data = {
                    'id': parts[0].strip('"'),
                    'achternaam': parts[2].strip('"'),
                    'voornaam': parts[3].strip('"'),
                    'straat': parts[6].strip('"'),
                    'postcode': parts[9].strip('"'),
                    'plaats': parts[8].strip('"'),
                    'ophaal_tijd': parts[17].strip('"'),
                    'eind_tijd': parts[18].strip('"'),
                    'telefoon': parts[11].strip('"') if len(parts) > 11 else ''
                }
                
                # Controleer of het voor vandaag is
                datum = parts[15].strip('"')
                
                if datum == '4-9-2025':
                    patients_data.append(patient_data)
                    print(f"✅ Regel {line_num}: {patient_data['voornaam']} {patient_data['achternaam']}")
                else:
                    print(f"⚠️ Regel {line_num}: Verkeerde datum '{datum}'")
                    
            except Exception as e:
                print(f"❌ Fout bij regel {line_num}: {e}")
    
    print(f"\n📊 {len(patients_data)} patiënten gevonden voor vandaag")
    
    # Haal tijdsblokken en voertuigen op
    timeslots = TimeSlot.objects.filter(actief=True, default_selected=True).order_by('aankomst_tijd')
    vehicles = Vehicle.objects.filter(status='beschikbaar')
    
    print(f"📅 Beschikbare tijdsblokken: {timeslots.count()}")
    print(f"🚐 Beschikbare voertuigen: {vehicles.count()}")
    
    # Verwijder bestaande patiënten voor vandaag
    existing_patients = Patient.objects.filter(ophaal_tijd__date=today)
    if existing_patients.exists():
        print(f"🗑️ Verwijder {existing_patients.count()} bestaande patiënten voor vandaag")
        existing_patients.delete()
    
    created_count = 0
    
    for i, data in enumerate(patients_data):
        try:
            # Converteer tijden
            ophaal_tijd_str = convert_time_format(data['ophaal_tijd'])
            eind_tijd_str = convert_time_format(data['eind_tijd'])
            
            # Parse tijden
            ophaal_hour, ophaal_minute = map(int, ophaal_tijd_str.split(':'))
            eind_hour, eind_minute = map(int, eind_tijd_str.split(':'))
            
            ophaal_datetime = datetime.combine(today, time(ophaal_hour, ophaal_minute))
            eind_datetime = datetime.combine(today, time(eind_hour, eind_minute))
            
            # Vind beste tijdsblokken
            halen_timeslot = None
            bringen_timeslot = None
            
            # Voor halen: zoek tijdsblok dat het dichtst bij ophaaltijd ligt (≤ ophaaltijd)
            halen_timeslots = timeslots.filter(tijdblok_type='halen')
            for timeslot in halen_timeslots:
                if timeslot.aankomst_tijd <= time(ophaal_hour, ophaal_minute):
                    halen_timeslot = timeslot
            
            # Voor brengen: zoek tijdsblok dat het dichtst bij eindtijd ligt (≥ eindtijd)
            bringen_timeslots = timeslots.filter(tijdblok_type='brengen')
            for timeslot in bringen_timeslots:
                if timeslot.aankomst_tijd >= time(eind_hour, eind_minute):
                    if not bringen_timeslot or timeslot.aankomst_tijd < bringen_timeslot.aankomst_tijd:
                        bringen_timeslot = timeslot
            
            # Fallback als geen exacte match
            if not halen_timeslot and halen_timeslots.exists():
                halen_timeslot = halen_timeslots.first()
            
            if not bringen_timeslot and bringen_timeslots.exists():
                bringen_timeslot = bringen_timeslots.last()
            
            # Wijs voertuig toe (round-robin)
            assigned_vehicle = vehicles[i % len(vehicles)] if vehicles.exists() else None
            
            # Maak patiënt
            patient = Patient.objects.create(
                naam=f"{data['voornaam']} {data['achternaam']}",
                straat=data['straat'],
                postcode=data['postcode'],
                plaats=data['plaats'],
                telefoonnummer=data['telefoon'],
                ophaal_tijd=ophaal_datetime,
                eind_behandel_tijd=eind_datetime,
                bestemming='Reha Center',
                halen_tijdblok=halen_timeslot,
                bringen_tijdblok=bringen_timeslot,
                toegewezen_voertuig=assigned_vehicle,
                status='gepland'
            )
            
            created_count += 1
            print(f"   ✅ {patient.naam}")
            print(f"      📅 Ophaal: {ophaal_tijd_str} → Tijdsblok: {halen_timeslot}")
            print(f"      🏠 Eind: {eind_tijd_str} → Tijdsblok: {bringen_timeslot}")
            print(f"      🚗 Voertuig: {assigned_vehicle}")
            
        except Exception as e:
            print(f"❌ Fout bij patiënt {data['voornaam']} {data['achternaam']}: {e}")
    
    print(f"\n🎉 {created_count} patiënten geïmporteerd voor {today}")
    
    # Verificeer import
    today_patients = Patient.objects.filter(ophaal_tijd__date=today)
    print(f"📊 Totaal patiënten voor vandaag: {today_patients.count()}")
    
    # Toon overzicht per tijdsblok
    print(f"\n📅 OVERZICHT PER TIJDSBLOK:")
    for timeslot in timeslots:
        if timeslot.tijdblok_type == 'halen':
            patients = today_patients.filter(halen_tijdblok=timeslot)
        else:
            patients = today_patients.filter(bringen_tijdblok=timeslot)
        
        if patients.exists():
            print(f"   ⏰ {timeslot.aankomst_tijd} ({timeslot.tijdblok_type}): {patients.count()} patiënten")
            for patient in patients:
                print(f"      👤 {patient.naam} - Voertuig: {patient.toegewezen_voertuig}")
    
    return today_patients

if __name__ == '__main__':
    try:
        patients = import_csv_patients()
        print("\n✅ CSV IMPORT COMPLETED SUCCESSFULLY")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
