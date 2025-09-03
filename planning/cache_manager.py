"""
Cache Manager voor patiënten data om geocoding te hergebruiken
"""
import hashlib
import json
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
from .models import Patient

class PatientCacheManager:
    """
    Slimme cache manager voor patiënten data
    Cachet geocoding resultaten en patiënt informatie voor 30 dagen
    """
    
    CACHE_PREFIX = "patient_cache"
    CACHE_TTL = 30 * 24 * 60 * 60  # 30 dagen in seconden
    
    @staticmethod
    def generate_patient_hash(naam, straat, postcode, plaats):
        """
        Genereer unieke hash voor patiënt op basis van naam + adres
        """
        patient_data = f"{naam.lower()}|{straat.lower()}|{postcode.lower()}|{plaats.lower()}"
        return hashlib.md5(patient_data.encode('utf-8')).hexdigest()
    
    @staticmethod
    def get_cache_key(patient_hash):
        """
        Genereer cache key voor patiënt
        """
        return f"{PatientCacheManager.CACHE_PREFIX}:{patient_hash}"
    
    @staticmethod
    def cache_patient(patient_hash, patient_data):
        """
        Cache patiënt data voor 30 dagen
        """
        cache_key = PatientCacheManager.get_cache_key(patient_hash)
        cache.set(cache_key, patient_data, PatientCacheManager.CACHE_TTL)
        
    @staticmethod
    def get_cached_patient(patient_hash):
        """
        Haal gecachte patiënt data op
        """
        cache_key = PatientCacheManager.get_cache_key(patient_hash)
        return cache.get(cache_key)
    
    @staticmethod
    def is_patient_cached(patient_hash):
        """
        Controleer of patiënt gecached is
        """
        return PatientCacheManager.get_cached_patient(patient_hash) is not None
    
    @staticmethod
    def get_or_create_patient_with_cache(naam, straat, postcode, plaats, telefoon, 
                                       eerste_behandeling_tijd, laatste_behandeling_tijd, 
                                       bestemming="Routemeister Transport"):
        """
        Haal patiënt op uit cache of maak nieuwe aan
        Behoudt geocoding en andere data
        """
        # Genereer hash voor patiënt
        patient_hash = PatientCacheManager.generate_patient_hash(naam, straat, postcode, plaats)
        
        # Probeer uit cache te halen
        cached_data = PatientCacheManager.get_cached_patient(patient_hash)
        
        if cached_data:
            # Patiënt gevonden in cache - update alleen tijden
            print(f"🔄 Patiënt gevonden in cache: {naam}")
            
            try:
                # Zoek bestaande patiënt in database
                existing_patient = Patient.objects.get(
                    naam=naam,
                    straat=straat,
                    postcode=postcode,
                    plaats=plaats
                )
                
                # Update alleen de tijden
                existing_patient.ophaal_tijd = eerste_behandeling_tijd
                existing_patient.eind_behandel_tijd = laatste_behandeling_tijd
                existing_patient.telefoonnummer = telefoon
                existing_patient.bestemming = bestemming
                existing_patient.save()
                
                print(f"   ✅ Tijden bijgewerkt voor bestaande patiënt")
                return existing_patient, False  # False = niet nieuw aangemaakt
                
            except Patient.DoesNotExist:
                # Patiënt bestaat niet meer in database, maak nieuwe aan
                print(f"   ⚠️  Patiënt niet meer in database, maak nieuwe aan")
                pass
        
        # Patiënt niet in cache of niet gevonden - maak nieuwe aan
        print(f"🆕 Nieuwe patiënt: {naam}")
        
        # Maak nieuwe patiënt aan
        new_patient = Patient.objects.create(
            naam=naam,
            straat=straat,
            postcode=postcode,
            plaats=plaats,
            telefoonnummer=telefoon,
            ophaal_tijd=eerste_behandeling_tijd,
            eind_behandel_tijd=laatste_behandeling_tijd,
            bestemming=bestemming,
            status='nieuw'
        )
        
        # Cache de nieuwe patiënt data
        cache_data = {
            'id': new_patient.id,
            'naam': naam,
            'straat': straat,
            'postcode': postcode,
            'plaats': plaats,
            'telefoonnummer': telefoon,
            'created_at': datetime.now().isoformat(),
            'cached': True
        }
        
        PatientCacheManager.cache_patient(patient_hash, cache_data)
        
        # Start geocoding voor nieuwe patiënt
        print(f"   🗺️  Start geocoding voor nieuwe patiënt...")
        # Hier zou je de geocoding logica kunnen toevoegen
        
        return new_patient, True  # True = nieuw aangemaakt
    
    @staticmethod
    def bulk_update_patients_from_csv(csv_data, detection_result):
        """
        Bulk update patiënten uit CSV met caching
        """
        mappings = detection_result.get('mappings', {})
        patients_created = 0
        patients_updated = 0
        patients_cached = 0
        
        print(f"🚀 Start bulk update met caching voor {len(csv_data)} rijen")
        
        for row_index, row in enumerate(csv_data):
            try:
                if not row.get('data'):
                    continue
                
                data = row['data']
                
                # Extraheer patiënt informatie (gebruik hardcoded kolom mapping zoals in views.py)
                patient_id = data[1]          # Kolom B
                achternaam = data[2]          # Kolom C
                voornaam = data[3]            # Kolom D
                straat = data[6]              # Kolom G
                plaats = data[8]              # Kolom I
                postcode = data[9]            # Kolom J
                telefoon1 = data[10]          # Kolom K
                telefoon2 = data[11]          # Kolom L
                eerste_behandeling_tijd = data[19] if len(data) > 19 else "0800"   # Kolom 19 (start tijd)
                laatste_behandeling_tijd = data[20] if len(data) > 20 else "1600"  # Kolom 20 (eind tijd)
                
                # Skip lege rijen
                if not patient_id or not voornaam:
                    continue
                
                telefoon = telefoon1 if telefoon1 else telefoon2
                
                # Combineer voor- en achternaam
                volledige_naam = f"{voornaam} {achternaam}".strip()
                
                if not volledige_naam or not eerste_behandeling_tijd:
                    continue
                
                # Parse tijden
                start_uur, start_minuut = PatientCacheManager.parse_time_string(eerste_behandeling_tijd, "08", "00")
                eind_uur, eind_minuut = PatientCacheManager.parse_time_string(laatste_behandeling_tijd, "16", "00")
                
                # Maak datetime objecten
                today = datetime.now().date()
                ophaal_tijd = datetime(
                    year=today.year,
                    month=today.month,
                    day=today.day,
                    hour=int(start_uur),
                    minute=int(start_minuut)
                )
                
                eind_tijd = datetime(
                    year=today.year,
                    month=today.month,
                    day=today.day,
                    hour=int(eind_uur),
                    minute=int(eind_minuut)
                )
                
                # Gebruik cache manager
                patient, is_new = PatientCacheManager.get_or_create_patient_with_cache(
                    volledige_naam, straat, postcode, plaats, telefoon,
                    ophaal_tijd, eind_tijd
                )
                
                if is_new:
                    patients_created += 1
                else:
                    patients_updated += 1
                
                # Controleer of patiënt uit cache kwam
                patient_hash = PatientCacheManager.generate_patient_hash(volledige_naam, straat, postcode, plaats)
                if PatientCacheManager.is_patient_cached(patient_hash):
                    patients_cached += 1
                
            except Exception as e:
                print(f"❌ Fout bij rij {row_index + 1}: {e}")
                continue
        
        print(f"🎯 Bulk update voltooid!")
        print(f"✅ Nieuwe patiënten: {patients_created}")
        print(f"🔄 Bijgewerkte patiënten: {patients_updated}")
        print(f"💾 Uit cache: {patients_cached}")
        
        return {
            'created': patients_created,
            'updated': patients_updated,
            'cached': patients_cached
        }
    
    @staticmethod
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
    
    @staticmethod
    def clear_expired_cache():
        """
        Ruim verlopen cache entries op
        """
        # Django cache heeft automatische TTL, maar we kunnen handmatig opruimen
        print("🧹 Cache opruiming gestart...")
        
        # Hier kunnen we specifieke cache keys opruimen indien nodig
        # Voor nu vertrouwen we op Django's automatische TTL
        
        print("✅ Cache opruiming voltooid")
    
    @staticmethod
    def get_cache_stats():
        """
        Haal cache statistieken op
        """
        # Dit is een vereenvoudigde versie
        # In productie zou je Redis/Memcached stats kunnen gebruiken
        return {
            'cache_prefix': PatientCacheManager.CACHE_PREFIX,
            'cache_ttl_days': PatientCacheManager.CACHE_TTL // (24 * 60 * 60),
            'status': 'active'
        }
