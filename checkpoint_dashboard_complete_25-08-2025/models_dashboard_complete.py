from django.db import models
from django.contrib.auth.models import User
import requests
import json

# Create your models here.

class Patient(models.Model):
    """
    Model voor patiënten die vervoerd moeten worden
    """
    # Basis patiëntgegevens
    naam = models.CharField(max_length=200, help_text="Volledige naam van de patiënt")
    telefoonnummer = models.CharField(max_length=20, blank=True, help_text="Contactnummer")
    
    # Adresgegevens
    straat = models.CharField(max_length=200, help_text="Straatnaam en huisnummer")
    postcode = models.CharField(max_length=10, help_text="Postcode")
    plaats = models.CharField(max_length=100, help_text="Woonplaats")
    
    # GPS Coördinaten voor OptaPlanner
    latitude = models.FloatField(null=True, blank=True, help_text="GPS Breedtegraad")
    longitude = models.FloatField(null=True, blank=True, help_text="GPS Lengtegraad")
    
    # Geocoding status
    GEOCODING_STATUS_CHOICES = [
        ('pending', 'Nog niet geocoded'),
        ('success', 'Succesvol geocoded'),
        ('failed', 'Adres niet gevonden'),
        ('manual', 'Handmatig ingevoerd'),
        ('default', 'Standaard locatie gebruikt'),
    ]
    geocoding_status = models.CharField(
        max_length=20, 
        choices=GEOCODING_STATUS_CHOICES, 
        default='pending',
        help_text="Status van adres geocoding"
    )
    geocoding_notes = models.TextField(
        blank=True, 
        help_text="Notities over geocoding problemen of wijzigingen"
    )
    
    # Transport details
    ophaal_tijd = models.DateTimeField(help_text="Gewenste ophaaltijd")
    eind_behandel_tijd = models.DateTimeField(null=True, blank=True, help_text="Tijd wanneer laatste behandeling eindigt")
    bestemming = models.CharField(max_length=300, help_text="Bestemming (ziekenhuis, kliniek, etc.)")
    
    # Planning
    toegewezen_tijdblok = models.ForeignKey('TimeSlot', on_delete=models.SET_NULL, null=True, blank=True,
                                           help_text="Toegewezen tijdblok voor planning (DEPRECATED - gebruik halen/bringen)")
    # Nieuwe velden voor HALEN en BRINGEN
    halen_tijdblok = models.ForeignKey('TimeSlot', on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='halen_patienten', help_text="Tijdblok voor ophalen (naar reha)")
    bringen_tijdblok = models.ForeignKey('TimeSlot', on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='bringen_patienten', help_text="Tijdblok voor terugbrengen (naar huis)")
    toegewezen_voertuig = models.ForeignKey('Vehicle', on_delete=models.SET_NULL, null=True, blank=True,
                                          help_text="Toegewezen voertuig voor transport")
    
    # Status
    STATUS_CHOICES = [
        ('nieuw', 'Nieuw verzoek'),
        ('gepland', 'Gepland'),
        ('onderweg', 'Onderweg'),
        ('afgeleverd', 'Afgeleverd'),
        ('geannuleerd', 'Geannuleerd'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='nieuw')
    
    # Speciale behoeften
    rolstoel = models.BooleanField(default=False, help_text="Heeft patiënt een rolstoel nodig?")
    
    # Mobile App Status (voor chauffeur notificaties)
    MOBILE_STATUS_CHOICES = [
        ('pending', 'Wacht op chauffeur'),
        ('notified', 'Chauffeur geïnformeerd'),
        ('in_transit', 'In transit (oranje)'),
        ('completed', 'Voltooid (groen)'),
    ]
    mobile_status = models.CharField(
        max_length=20, 
        choices=MOBILE_STATUS_CHOICES, 
        default='pending',
        help_text="Status voor mobile app notificaties"
    )
    mobile_notification_sent = models.DateTimeField(
        null=True, 
        blank=True, 
        help_text="Wanneer is de laatste notificatie naar de chauffeur gestuurd?"
    )
    
    # Metadata
    aangemaakt_op = models.DateTimeField(auto_now_add=True)
    bijgewerkt_op = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.naam} - {self.ophaal_tijd.strftime('%d-%m-%Y %H:%M')}"
    
    class Meta:
        verbose_name = "Patiënt"
        verbose_name_plural = "Patiënten"
        ordering = ['ophaal_tijd']


class Vehicle(models.Model):
    """
    Model voor voertuigen in het wagenpark
    """
    # Basis informatie
    referentie = models.CharField(max_length=50, unique=True, null=True, blank=True, help_text="Unieke referentie (bijv. W206)")
    kenteken = models.CharField(max_length=10, unique=True, help_text="Kenteken van het voertuig")
    merk_model = models.CharField(max_length=100, help_text="Merk en model (bijv. VW Transporter)")
    
    # Capaciteit
    aantal_zitplaatsen = models.IntegerField(default=7, help_text="Aantal normale zitplaatsen")
    speciale_zitplaatsen = models.IntegerField(default=0, help_text="Aantal speciale zitplaatsen (rolstoel, etc.)")
    
    # Kosten en tijden
    km_kosten_per_km = models.DecimalField(max_digits=5, decimal_places=2, default=0.29, help_text="Kosten per kilometer")
    maximale_rit_tijd = models.IntegerField(default=3600, help_text="Maximale rit tijd in seconden")
    
    # Visuele eigenschappen
    kleur = models.CharField(max_length=7, default='#3498db', help_text="Kleur voor dit voertuig (hex code, bijv. #FF5733)")
    foto = models.ImageField(upload_to='vehicles/', null=True, blank=True, help_text="Profiel foto van het voertuig")
    
    # Status
    STATUS_CHOICES = [
        ('beschikbaar', 'Beschikbaar'),
        ('onderhoud', 'Onderhoud'),
        ('niet_beschikbaar', 'Niet beschikbaar'),
        ('defect', 'Defect'),
        ('in_reparatie', 'In reparatie'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='beschikbaar')
    status_until = models.DateField(null=True, blank=True, help_text="Status geldig tot (voor onderhoud/reparatie)")
    
    # Metadata
    aangemaakt_op = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.kenteken} - {self.merk_model}"
    
    class Meta:
        verbose_name = "Voertuig"
        verbose_name_plural = "Voertuigen"


class TimeSlot(models.Model):
    """
    Tijdblokken voor het plannen van patiëntentransport
    """
    naam = models.CharField(max_length=100, help_text="Naam van het tijdblok (bijv. 'Ochtend blok 1')")
    
    # Heen tijden
    heen_start_tijd = models.TimeField(help_text="Start tijd voor ophalen patiënten")
    heen_eind_tijd = models.TimeField(help_text="Eind tijd voor ophalen patiënten")
    
    # Terug tijden  
    terug_start_tijd = models.TimeField(help_text="Start tijd voor terugbrengen patiënten")
    terug_eind_tijd = models.TimeField(help_text="Eind tijd voor terugbrengen patiënten")
    
    # Beperkingen
    max_rijtijd_minuten = models.IntegerField(default=60, help_text="Maximale rijtijd in minuten")
    max_patienten_per_rit = models.IntegerField(default=4, help_text="Maximum aantal patiënten per rit")
    
    # Planning
    actief = models.BooleanField(default=True, help_text="Is dit tijdblok actief voor planning?")
    default_selected = models.BooleanField(default=False, help_text="Standaard geselecteerd op planning pagina?")
    dag_van_week = models.CharField(max_length=20, choices=[
        ('maandag', 'Maandag'),
        ('dinsdag', 'Dinsdag'), 
        ('woensdag', 'Woensdag'),
        ('donderdag', 'Donderdag'),
        ('vrijdag', 'Vrijdag'),
        ('zaterdag', 'Zaterdag'),
        ('zondag', 'Zondag'),
        ('alle_dagen', 'Alle dagen'),
    ], default='alle_dagen')
    
    def __str__(self):
        return f"{self.naam} - Heen: {self.heen_start_tijd}-{self.heen_eind_tijd}, Terug: {self.terug_start_tijd}-{self.terug_eind_tijd}"
    
    def get_duration_minutes(self):
        """Bereken de duur van het tijdblok in minuten"""
        from datetime import datetime, timedelta
        start = datetime.combine(datetime.today(), self.heen_start_tijd)
        end = datetime.combine(datetime.today(), self.terug_eind_tijd)
        return int((end - start).total_seconds() / 60)
    
    class Meta:
        verbose_name = "Tijdblok"
        verbose_name_plural = "Tijdblokken"
        ordering = ['heen_start_tijd']


class UserProfile(models.Model):
    """
    Uitbreiding van Django's User model voor Routemeister specifieke info
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Rollen
    ROLE_CHOICES = [
        ('planner', 'Planner'),
        ('chauffeur', 'Chauffeur'),
        ('admin', 'Administrator'),
    ]
    rol = models.CharField(max_length=20, choices=ROLE_CHOICES, default='chauffeur')
    
    # Chauffeur specifiek
    rijbewijs_nummer = models.CharField(max_length=20, blank=True, help_text="Rijbewijsnummer")
    toegewezen_voertuig = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True,
                                          help_text="Standaard toegewezen voertuig")
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_rol_display()}"
    
    class Meta:
        verbose_name = "Gebruikersprofiel"
        verbose_name_plural = "Gebruikersprofielen"


class Configuration(models.Model):
    """
    Systeem configuratie voor REST API en andere instellingen
    """
    key = models.CharField(max_length=100, unique=True, help_text="Configuratie sleutel")
    value = models.TextField(help_text="Configuratie waarde")
    description = models.TextField(blank=True, help_text="Beschrijving van deze instelling")
    is_active = models.BooleanField(default=True, help_text="Of deze instelling actief is")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configuratie"
        verbose_name_plural = "Configuraties"
        ordering = ['key']
    
    def __str__(self):
        return f"{self.key}: {self.value}"
    
    @classmethod
    def get_value(cls, key, default=None):
        """Haal een configuratie waarde op"""
        try:
            config = cls.objects.get(key=key, is_active=True)
            return config.value
        except cls.DoesNotExist:
            return default
    
    @classmethod
    def set_value(cls, key, value, description=""):
        """Zet een configuratie waarde"""
        config, created = cls.objects.get_or_create(
            key=key,
            defaults={'value': value, 'description': description}
        )
        if not created:
            config.value = value
            config.description = description
            config.save()
        return config


class Location(models.Model):
    """
    Locaties voor het systeem (Reha Center, depots, etc.)
    """
    LOCATION_TYPES = [
        ('home', 'Home/Depot (Reha Center)'),
        ('depot', 'Depot'),
        ('office', 'Kantoor'),
        ('other', 'Anders'),
    ]
    
    name = models.CharField(max_length=100, help_text="Naam van de locatie")
    location_type = models.CharField(max_length=20, choices=LOCATION_TYPES, default='home', help_text="Type locatie")
    address = models.TextField(help_text="Volledig adres")
    latitude = models.DecimalField(max_digits=12, decimal_places=9, help_text="Latitude (breedtegraad)")
    longitude = models.DecimalField(max_digits=12, decimal_places=9, help_text="Longitude (lengtegraad)")
    is_active = models.BooleanField(default=True, help_text="Of deze locatie actief is")
    is_default = models.BooleanField(default=False, help_text="Standaard locatie voor routes")
    description = models.TextField(blank=True, help_text="Beschrijving van de locatie")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Locatie"
        verbose_name_plural = "Locaties"
        ordering = ['location_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_location_type_display()})"
    
    def save(self, *args, **kwargs):
        # Als deze locatie default wordt, maak andere home locaties niet-default
        if self.is_default and self.location_type == 'home':
            Location.objects.filter(location_type='home', is_default=True).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)
    
    @classmethod
    def get_home_location(cls):
        """Haal de standaard home/depot locatie op"""
        try:
            return cls.objects.get(location_type='home', is_default=True, is_active=True)
        except cls.DoesNotExist:
            # Fallback naar eerste actieve home locatie
            try:
                return cls.objects.filter(location_type='home', is_active=True).first()
            except:
                # Laatste fallback - hardcoded Bonn coördinaten
                return None
    
    def geocode_address(self):
        """Geocode het adres naar coördinaten"""
        if not self.address:
            return False
        
        try:
            # Gebruik OpenStreetMap Nominatim API (gratis)
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': self.address,
                'format': 'json',
                'limit': 1,
                'addressdetails': 1
            }
            headers = {
                'User-Agent': 'Routemeister/1.0 (https://routemeister.com)'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data and len(data) > 0:
                result = data[0]
                self.latitude = float(result['lat'])
                self.longitude = float(result['lon'])
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Geocoding error: {e}")
            return False
    
    def save(self, *args, **kwargs):
        # Als deze locatie default wordt, maak andere home locaties niet-default
        if self.is_default and self.location_type == 'home':
            Location.objects.filter(location_type='home', is_default=True).exclude(id=self.id).update(is_default=False)
        
        # Auto-geocode als coördinaten leeg zijn maar adres wel ingevuld
        if (not self.latitude or not self.longitude) and self.address:
            self.geocode_address()
        
        super().save(*args, **kwargs)


class CSVParserConfig(models.Model):
    """
    Configuratie voor CSV parser formaten die via de admin kunnen worden beheerd
    """
    naam = models.CharField(max_length=100, help_text="Naam van het CSV formaat (bijv. 'Fahrdlist', 'Routemeister')")
    actief = models.BooleanField(default=True, help_text="Of dit formaat actief is voor detectie")
    prioriteit = models.IntegerField(default=1, help_text="Prioriteit voor detectie (hogere nummer = hogere prioriteit)")
    
    # Detectie criteria
    bestandsnaam_patroon = models.CharField(max_length=200, blank=True, help_text="Regex patroon voor bestandsnaam detectie (bijv. 'fahrdlist.*\\.csv')")
    header_keywords = models.TextField(blank=True, help_text="Komma-gescheiden keywords voor header detectie (bijv. 'kunde,termin,fahrer')")
    
    # Kolom mapping
    kolom_mapping = models.JSONField(default=dict, help_text="JSON mapping van veldnamen naar kolom indices")
    
    # Validatie regels
    datum_formaten = models.TextField(blank=True, help_text="Komma-gescheiden datum formaten (bijv. 'DD-MM-YYYY,DD.MM.YYYY')")
    tijd_formaten = models.TextField(blank=True, help_text="Komma-gescheiden tijd formaten (bijv. 'HHMM,HH:MM')")
    
    # Metadata
    beschrijving = models.TextField(blank=True, help_text="Beschrijving van het CSV formaat")
    gemaakt_op = models.DateTimeField(auto_now_add=True)
    bijgewerkt_op = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-prioriteit', 'naam']
        verbose_name = "CSV Parser Configuratie"
        verbose_name_plural = "CSV Parser Configuraties"
    
    def __str__(self):
        return f"{self.naam} ({'Actief' if self.actief else 'Inactief'})"
    
    def get_kolom_mapping(self):
        """Retourneer de kolom mapping als dictionary"""
        if isinstance(self.kolom_mapping, str):
            import json
            return json.loads(self.kolom_mapping)
        return self.kolom_mapping or {}
    
    def get_header_keywords_list(self):
        """Retourneer header keywords als lijst"""
        if not self.header_keywords:
            return []
        return [kw.strip() for kw in self.header_keywords.split(',') if kw.strip()]
    
    def get_datum_formaten_list(self):
        """Retourneer datum formaten als lijst"""
        if not self.datum_formaten:
            return []
        return [fmt.strip() for fmt in self.datum_formaten.split(',') if fmt.strip()]
    
    def get_tijd_formaten_list(self):
        """Retourneer tijd formaten als lijst"""
        if not self.tijd_formaten:
            return []
        return [fmt.strip() for fmt in self.tijd_formaten.split(',') if fmt.strip()]
    
    def test_detectie(self, bestandsnaam, headers):
        """
        Test of deze configuratie past bij de gegeven bestandsnaam en headers
        """
        score = 0
        
        # Test bestandsnaam patroon
        if self.bestandsnaam_patroon:
            import re
            if re.search(self.bestandsnaam_patroon, bestandsnaam, re.IGNORECASE):
                score += 50
        
        # Test header keywords
        if self.header_keywords:
            header_text = ' '.join(str(h).lower() for h in headers)
            keywords = self.get_header_keywords_list()
            matches = sum(1 for kw in keywords if kw.lower() in header_text)
            if matches > 0:
                score += (matches / len(keywords)) * 50
        
        return score
