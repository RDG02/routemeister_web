#!/usr/bin/env python
"""
Script om alleen de tijden van bestaande patiënten bij te werken
Behoudt geocoding, voertuig toewijzingen en andere data
"""
import os
import sys
import django
import csv
from datetime import datetime, date

# Voeg het project toe aan Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'routemeister.settings')
django.setup()

from planning.models import Patient, CSVImportLog

def update_patient_times_from_csv(csv_file_path):
    """
    Update alleen de tijden van bestaande patiënten uit CSV
    """
    print(f"🔄 Start bijwerken van patiënten tijden uit: {csv_file_path}")
    print("=" * 60)
    
    if not os.path.exists(csv_file_path):
        print(f"❌ CSV bestand niet gevonden: {csv_file_path}")
        return
    
    # Haal alle patiënten van vandaag op
    today = date.today()
    existing_patients = Patient.objects.filter(ophaal_tijd__date=today)
    
    if not existing_patients.exists():
        print(f"❌ Geen patiënten gevonden voor vandaag ({today})")
        return
    
    print(f"✅ {existing_patients.count()} patiënten gevonden voor vandaag")
    print()
    
    # Maak een mapping van patiënt naam naar database object
    patient_map = {}
    for patient in existing_patients:
        # Gebruik naam als key (kan ook gecombineerd worden met andere velden)
        patient_map[patient.naam.lower().strip()] = patient
    
    print(f"📋 Patiënten mapping gemaakt: {len(patient_map)} patiënten")
    print()
    
    # Lees CSV bestand
    updated_count = 0
    error_count = 0
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
            # Probeer verschillende delimiters
            for delimiter in [',', ';', '\t']:
                try:
                    csvfile.seek(0)  # Reset naar begin van bestand
                    reader = csv.reader(csvfile, delimiter=delimiter)
                    rows = list(reader)
                    if len(rows) > 1:  # Minimaal header + 1 rij
                        break
                except:
                    continue
            else:
                print("❌ Kon CSV niet lezen met bekende delimiters")
                return
            
            print(f"📊 CSV gelezen: {len(rows)} rijen met delimiter '{delimiter}'")
            
            # Skip header rij
            for row_index, row in enumerate(rows[1:], start=2):
                try:
                    if len(row) < 20:  # Minimaal 20 kolommen verwacht
                        continue
                    
                    # Extraheer patiënt informatie (pas kolom indices aan indien nodig)
                    achternaam = row[0].strip() if len(row) > 0 else ""
                    voornaam = row[1].strip() if len(row) > 1 else ""
                    eerste_behandeling_tijd = row[19].strip() if len(row) > 19 else ""  # Kolom 19 (0-indexed)
                    laatste_behandeling_tijd = row[20].strip() if len(row) > 20 else ""  # Kolom 20 (0-indexed)
                    
                    # Combineer voor- en achternaam
                    volledige_naam = f"{voornaam} {achternaam}".strip()
                    
                    if not volledige_naam or not eerste_behandeling_tijd:
                        continue
                    
                    # Zoek patiënt in database
                    patient_key = volledige_naam.lower()
                    if patient_key not in patient_map:
                        print(f"⚠️  Patiënt niet gevonden in database: {volledige_naam}")
                        continue
                    
                    patient = patient_map[patient_key]
                    
                    # Parse tijden (gebruik dezelfde logica als in views.py)
                    start_uur, start_minuut = parse_time_string(eerste_behandeling_tijd, "08", "00")
                    eind_uur, eind_minuut = parse_time_string(laatste_behandeling_tijd, "16", "00")
                    
                    # Maak nieuwe datetime objecten
                    nieuwe_ophaal_tijd = datetime(
                        year=today.year,
                        month=today.month,
                        day=today.day,
                        hour=int(start_uur),
                        minute=int(start_minuut)
                    )
                    
                    nieuwe_eind_tijd = datetime(
                        year=today.year,
                        month=today.month,
                        day=today.day,
                        hour=int(eind_uur),
                        minute=int(eind_minuut)
                    )
                    
                    # Controleer of tijden zijn veranderd
                    if (patient.ophaal_tijd != nieuwe_ophaal_tijd or 
                        patient.eind_behandel_tijd != nieuwe_eind_tijd):
                        
                        print(f"🔄 Update tijden voor {patient.naam}:")
                        print(f"   Ophaal: {patient.ophaal_tijd.strftime('%H:%M')} → {nieuwe_ophaal_tijd.strftime('%H:%M')}")
                        print(f"   Eind: {patient.eind_behandel_tijd.strftime('%H:%M')} → {nieuwe_eind_tijd.strftime('%H:%M')}")
                        
                        # Update alleen de tijden
                        patient.ophaal_tijd = nieuwe_ophaal_tijd
                        patient.eind_behandel_tijd = nieuwe_eind_tijd
                        patient.save()
                        
                        updated_count += 1
                        print(f"   ✅ Bijgewerkt")
                    else:
                        print(f"ℹ️  {patient.naam}: Tijden zijn al correct")
                    
                    print()
                    
                except Exception as e:
                    error_count += 1
                    print(f"❌ Fout bij rij {row_index}: {e}")
                    continue
    
    except Exception as e:
        print(f"❌ Fout bij lezen CSV: {e}")
        return
    
    # Resultaat
    print("=" * 60)
    print(f"🎯 Bijwerken voltooid!")
    print(f"✅ {updated_count} patiënten bijgewerkt")
    print(f"❌ {error_count} fouten")
    print(f"📊 Totaal patiënten: {existing_patients.count()}")
    
    if updated_count > 0:
        print(f"\n🔄 Refresh de dashboard pagina om de nieuwe tijden te zien!")

def parse_time_string(time_str, default_hour, default_minute):
    """
    Parse tijd string naar uur en minuut
    """
    if not time_str or len(time_str) < 3:
        return default_hour, default_minute
    
    # Handle both "845" and "0845" format
    if len(time_str) == 3:  # "845"
        start_uur = "0" + time_str[0]  # "0" + "8" = "08"
        start_minuut = time_str[1:3]   # "45"
    else:  # "0845"
        start_uur = time_str[:2]       # "08"
        start_minuut = time_str[2:4]   # "45"
    
    return start_uur, start_minuut

if __name__ == "__main__":
    # Vraag gebruiker om CSV bestand pad
    csv_path = input("📁 Voer het pad naar je CSV bestand in (bijv. routemeister_25082025.csv): ").strip()
    
    if not csv_path:
        print("❌ Geen pad ingevoerd")
        sys.exit(1)
    
    # Voer update uit
    update_patient_times_from_csv(csv_path)
