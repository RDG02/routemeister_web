"""
Geocoding service voor het omzetten van adressen naar GPS coordinaten
Ondersteunt meerdere providers (OpenStreetMap Nominatim, Google Maps API)
"""
import requests
import logging
import time
from django.conf import settings
from django.utils import timezone
from typing import Tuple, Optional
import re

logger = logging.getLogger(__name__)


class GeocodingService:
    """
    Service voor het geocoderen van adressen naar GPS coordinaten
    """
    
    def __init__(self):
        self.nominatim_base_url = "https://nominatim.openstreetmap.org/search"
        self.google_api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
        self.default_country = "Deutschland"  # Voor Duitse adressen
        self.rate_limit_delay = 1  # Seconde tussen requests (Nominatim vereiste)
        
        # Cache voor geocoding resultaten
        self._cache = {}
    
    def clean_address(self, address: str, postcode: str = None, city: str = None) -> str:
        """
        Maak adres schoon voor betere geocoding resultaten
        """
        if not address:
            return ""
        
        # Combineer adres componenten
        parts = []
        
        # Voeg adres toe
        cleaned_address = address.strip()
        if cleaned_address:
            parts.append(cleaned_address)
        
        # Voeg postcode en stad toe als beschikbaar
        if postcode and postcode.strip():
            parts.append(postcode.strip())
        
        if city and city.strip():
            parts.append(city.strip())
        
        # Voeg land toe voor betere resultaten
        parts.append(self.default_country)
        
        full_address = ", ".join(parts)
        logger.debug(f"Cleaned address: {full_address}")
        return full_address
    
    def geocode_with_nominatim(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Geocodeer adres met OpenStreetMap Nominatim (gratis)
        Returns: (latitude, longitude) of None
        """
        try:
            # Rate limiting voor Nominatim
            time.sleep(self.rate_limit_delay)
            
            params = {
                'q': address,
                'format': 'json',
                'limit': 1,
                'addressdetails': 1,
                'countrycodes': 'de',  # Limiteer tot Duitsland
            }
            
            headers = {
                'User-Agent': 'Routemeister/1.0 (contact@routemeister.com)'  # Vereist voor Nominatim
            }
            
            response = requests.get(
                self.nominatim_base_url, 
                params=params, 
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                results = response.json()
                if results:
                    result = results[0]
                    lat = float(result['lat'])
                    lon = float(result['lon'])
                    
                    logger.info(f"Geocoded '{address}' to ({lat}, {lon})")
                    return (lat, lon)
                else:
                    logger.warning(f"No results found for address: {address}")
                    return None
            else:
                logger.error(f"Nominatim API error {response.status_code}: {response.text}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Network error geocoding '{address}': {e}")
            return None
        except (ValueError, KeyError) as e:
            logger.error(f"Data parsing error for '{address}': {e}")
            return None
    
    def geocode_with_google(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Geocodeer adres met Google Maps API (vereist API key)
        Returns: (latitude, longitude) of None
        """
        if not self.google_api_key:
            logger.debug("Google Maps API key not configured")
            return None
        
        try:
            params = {
                'address': address,
                'key': self.google_api_key,
                'region': 'de',  # Duitsland
            }
            
            response = requests.get(
                'https://maps.googleapis.com/maps/api/geocode/json',
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'OK' and data['results']:
                    location = data['results'][0]['geometry']['location']
                    lat = location['lat']
                    lon = location['lng']
                    
                    logger.info(f"Google geocoded '{address}' to ({lat}, {lon})")
                    return (lat, lon)
                else:
                    logger.warning(f"Google geocoding failed for '{address}': {data['status']}")
                    return None
            else:
                logger.error(f"Google API error {response.status_code}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Network error with Google API for '{address}': {e}")
            return None
        except (ValueError, KeyError) as e:
            logger.error(f"Google API data parsing error for '{address}': {e}")
            return None
    
    def geocode_address(self, address: str, postcode: str = None, city: str = None) -> Optional[Tuple[float, float]]:
        """
        Hoofdfunctie: geocodeer een adres naar GPS coordinaten
        Probeert eerst cache, dan Nominatim, dan Google als backup
        """
        # Maak adres schoon
        clean_addr = self.clean_address(address, postcode, city)
        
        if not clean_addr:
            logger.warning("Empty address provided for geocoding")
            return None
        
        # Check cache eerst
        cache_key = clean_addr.lower()
        if cache_key in self._cache:
            logger.debug(f"Using cached coordinates for '{clean_addr}'")
            return self._cache[cache_key]
        
        # Probeer Nominatim eerst (gratis)
        coordinates = self.geocode_with_nominatim(clean_addr)
        
        # Als Nominatim faalt, probeer Google (als API key beschikbaar)
        if not coordinates:
            coordinates = self.geocode_with_google(clean_addr)
        
        # Sla resultaat op in cache (ook None om herhaalde verzoeken te voorkomen)
        self._cache[cache_key] = coordinates
        
        return coordinates
    
    def get_default_coordinates(self, city: str = None) -> Tuple[float, float]:
        """
        Geef standaard coordinaten terug voor een stad of regio
        """
        # Duitse steden coordinaten
        city_coords = {
            'bonn': (50.7374, 7.0982),
            'köln': (50.9375, 6.9603),
            'düsseldorf': (51.2277, 6.7735),
            'siegburg': (50.7943, 7.2064),
            'niederkassel': (50.8167, 7.0333),
            'bad honnef': (50.6408, 7.2269),
        }
        
        if city and city.lower() in city_coords:
            return city_coords[city.lower()]
        
        # Standaard: centrum van Duitsland (ongeveer Frankfurt)
        return (50.1109, 8.6821)
    
    def bulk_geocode_patients(self, patients):
        """
        Geocodeer meerdere patiënten in bulk
        Updates patient records met GPS coordinaten
        """
        geocoded_count = 0
        failed_count = 0
        
        for patient in patients:
            # Skip als al geocoded
            if patient.latitude and patient.longitude:
                continue
            
            logger.info(f"Geocoding patient: {patient.naam}")
            
            coordinates = self.geocode_address(
                patient.straat,
                patient.postcode,
                patient.plaats
            )
            
            if coordinates:
                patient.latitude, patient.longitude = coordinates
                patient.geocoding_status = 'success'
                patient.geocoding_notes = f"Geocoded op {timezone.now().strftime('%Y-%m-%d %H:%M')}"
                patient.save()
                geocoded_count += 1
                logger.info(f"✅ Geocoded {patient.naam}: {coordinates}")
            else:
                # Gebruik standaard coordinaten gebaseerd op stad
                default_coords = self.get_default_coordinates(patient.plaats)
                patient.latitude, patient.longitude = default_coords
                patient.geocoding_status = 'failed'
                patient.geocoding_notes = f"Adres '{patient.straat}, {patient.postcode} {patient.plaats}' niet gevonden. Standaard locatie voor {patient.plaats} gebruikt."
                patient.save()
                failed_count += 1
                logger.warning(f"⚠️ Used default coordinates for {patient.naam}: {default_coords}")
        
        logger.info(f"Bulk geocoding completed: {geocoded_count} geocoded, {failed_count} defaults used")
        return geocoded_count, failed_count


# Singleton instance
geocoding_service = GeocodingService()
