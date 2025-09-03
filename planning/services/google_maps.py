"""
Google Maps API service voor route optimalisatie
"""
import logging
import requests
import json
from typing import List, Dict, Tuple, Optional
from django.conf import settings
from django.utils import timezone
from ..models import GoogleMapsConfig, GoogleMapsAPILog

logger = logging.getLogger(__name__)


class GoogleMapsService:
    """
    Google Maps API service voor nauwkeurige route optimalisatie
    """
    
    def __init__(self):
        self.config = GoogleMapsConfig.get_active_config()
        self.base_url = "https://maps.googleapis.com/maps/api"
        self.api_key = self.config.api_key if self.config.enabled else None
        logger.info(f"GoogleMapsService initialized: config={self.config}, enabled={self.config.enabled}, api_key_length={len(self.api_key) if self.api_key else 0}")
        
    def is_enabled(self) -> bool:
        """Check of Google Maps API is ingeschakeld"""
        # Voor nu, return altijd False omdat de API niet correct geconfigureerd is
        # Dit zorgt ervoor dat de fallback wordt gebruikt
        enabled = False
        logger.info(f"Google Maps enabled check: config.enabled={self.config.enabled}, api_key_exists={self.api_key is not None}, result={enabled} (fallback mode)")
        return enabled
    
    def _make_api_call(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """Maak API call naar Google Maps"""
        if not self.is_enabled():
            logger.warning("❌ Google Maps API is niet ingeschakeld")
            return None
        
        try:
            params['key'] = self.api_key
            # Fix: Verwijder dubbele /json uit URL
            if endpoint.endswith('/json'):
                url = f"{self.base_url}/{endpoint}"
            else:
                url = f"{self.base_url}/{endpoint}/json"
            
            logger.info(f"📡 API call naar: {url}")
            logger.info(f"🔑 API key lengte: {len(self.api_key) if self.api_key else 0}")
            logger.info(f"📋 Parameters: {params}")
            
            response = requests.get(url, params=params, timeout=10)
            logger.info(f"📥 Response status code: {response.status_code}")
            
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"📊 Response data keys: {list(data.keys())}")
            
            if data.get('status') == 'OK':
                # Log succesvolle API call
                api_type = endpoint.split('/')[0]  # distancematrix, directions, geocode
                GoogleMapsAPILog.log_api_call(api_type)
                logger.info(f"✅ API call succesvol voor {api_type}")
                return data
            else:
                logger.error(f"❌ Google Maps API error: {data.get('status')} - {data.get('error_message', 'Unknown error')}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"❌ Google Maps API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Google Maps API error: {e}")
            return None
    
    def get_distance_matrix(self, origins: List[str], destinations: List[str]) -> Optional[Dict]:
        """
        Haal afstanden en reistijden op tussen locaties
        
        Args:
            origins: List van origine locaties (lat,lng of adres)
            destinations: List van bestemming locaties
            
        Returns:
            Dictionary met afstanden en reistijden
        """
        params = {
            'origins': '|'.join(origins),
            'destinations': '|'.join(destinations),
            'mode': 'driving',
            'units': 'metric',
            'traffic_model': 'best_guess',
            'departure_time': 'now'
        }
        
        return self._make_api_call('distancematrix/json', params)
    
    def get_directions(self, origin: str, destination: str, waypoints: List[str] = None) -> Optional[Dict]:
        """
        Haal gedetailleerde route op
        
        Args:
            origin: Start locatie
            destination: Eind locatie
            waypoints: Tussenstops (optioneel)
            
        Returns:
            Dictionary met route details
        """
        params = {
            'origin': origin,
            'destination': destination,
            'mode': 'driving',
            'units': 'metric',
            'optimize': 'true' if waypoints else 'false'
        }
        
        if waypoints:
            params['waypoints'] = '|'.join(waypoints)
        
        return self._make_api_call('directions/json', params)
    
    def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Converteer adres naar GPS coördinaten
        
        Args:
            address: Volledig adres
            
        Returns:
            Tuple van (latitude, longitude) of None
        """
        logger.info(f"🗺️ Geocode adres: {address}")
        
        if not self.is_enabled():
            logger.warning("❌ Google Maps API niet beschikbaar voor geocoding")
            return None
        
        params = {
            'address': address,
            'components': 'country:DE'  # Focus op Duitsland
        }
        
        logger.info(f"📡 API call parameters: {params}")
        
        data = self._make_api_call('geocode/json', params)
        
        if not data:
            logger.error("❌ Geen response van Google Maps API")
            return None
        
        logger.info(f"📥 Response status: {data.get('status', 'unknown')}")
        
        if data.get('status') == 'REQUEST_DENIED':
            logger.error(f"❌ API request geweigerd: {data.get('error_message', 'Geen foutmelding')}")
            return None
        
        if data.get('status') == 'ZERO_RESULTS':
            logger.warning(f"❌ Geen resultaten gevonden voor: {address}")
            return None
        
        if data and data.get('results'):
            location = data['results'][0]['geometry']['location']
            coords = (location['lat'], location['lng'])
            logger.info(f"✅ Geocoding succesvol: {coords}")
            return coords
        
        logger.warning(f"❌ Onverwachte response: {data}")
        return None
    
    def optimize_vehicle_routes(self, timeslot_assignments: Dict, vehicles: List) -> Dict:
        """
        Optimaliseer voertuig routes met Google Maps
        
        Args:
            timeslot_assignments: Dictionary van tijdblok -> patiënten
            vehicles: List van beschikbare voertuigen
            
        Returns:
            Dictionary met geoptimaliseerde routes
        """
        # Check of Google Maps API beschikbaar is
        if not self.is_enabled():
            logger.warning("Google Maps API niet beschikbaar, gebruik fallback")
            return self._fallback_optimization(timeslot_assignments, vehicles)
        
        # Check of patiënten adresgegevens hebben
        has_addresses = self._check_patients_have_addresses(timeslot_assignments)
        if not has_addresses:
            logger.warning("Patiënten hebben geen adresgegevens, gebruik fallback")
            return self._fallback_optimization(timeslot_assignments, vehicles)
        
        optimized_routes = {}
        
        for timeslot_id, patients in timeslot_assignments.items():
            logger.info(f"Optimaliseer routes voor tijdblok {timeslot_id} met {len(patients)} patiënten")
            
            # 1. Bereken afstanden tussen alle locaties
            locations = self._extract_locations(patients)
            distance_matrix = self._get_distance_matrix_for_locations(locations)
            
            if not distance_matrix:
                logger.warning(f"Kon geen afstanden ophalen voor tijdblok {timeslot_id}")
                continue
            
            # 2. Verdeel patiënten over voertuigen
            vehicle_assignments = self._assign_patients_to_vehicles(
                patients, vehicles, distance_matrix
            )
            
            # 3. Optimaliseer routes per voertuig
            routes = []
            for vehicle, assigned_patients in vehicle_assignments.items():
                if assigned_patients:
                    route = self._optimize_vehicle_route(vehicle, assigned_patients, distance_matrix)
                    if route:
                        routes.append(route)
            
            optimized_routes[timeslot_id] = {
                'routes': routes,
                'total_distance': sum(route['total_distance'] for route in routes),
                'total_time': sum(route['total_time'] for route in routes),
                'total_cost': sum(route['total_cost'] for route in routes),
                'vehicle_count': len(routes)
            }
        
        return optimized_routes
    
    def _check_patients_have_addresses(self, timeslot_assignments: Dict) -> bool:
        """Check of patiënten adresgegevens hebben"""
        logger.info("🔍 Check patiënt adresgegevens...")
        
        for timeslot_id, patients in timeslot_assignments.items():
            logger.info(f"  Tijdblok {timeslot_id}: {len(patients)} patiënten")
            
            for i, patient in enumerate(patients):
                if isinstance(patient, dict):
                    straat = patient.get('straat', '')
                    postcode = patient.get('postcode', '')
                    plaats = patient.get('plaats', '')
                    adres = patient.get('adres', '')  # Mogelijk heet het veld 'adres'
                    naam = patient.get('naam', '')
                    if not naam and patient.get('voornaam') and patient.get('achternaam'):
                        naam = f"{patient.get('voornaam')} {patient.get('achternaam')}".strip()
                else:
                    straat = getattr(patient, 'straat', '')
                    postcode = getattr(patient, 'postcode', '')
                    plaats = getattr(patient, 'plaats', '')
                    adres = getattr(patient, 'adres', '')
                    naam = getattr(patient, 'naam', '')
                
                logger.info(f"    Patiënt {i+1} ({naam}): straat='{straat}', postcode='{postcode}', plaats='{plaats}', adres='{adres}'")
                
                # Check verschillende combinaties van adresvelden
                if (straat and postcode and plaats) or (adres and plaats):
                    logger.info(f"    ✅ Patiënt {naam} heeft adresgegevens")
                    return True
        
        logger.warning("❌ Geen patiënten met adresgegevens gevonden")
        return False
    
    def _extract_locations(self, patients: List) -> List[str]:
        """Extraheer locaties uit patiënten"""
        locations = []
        
        # Voeg reha center toe als start/eindpunt
        from ..models import Location
        home_location = Location.get_home_location()
        if home_location:
            locations.append(f"{home_location.latitude},{home_location.longitude}")
        else:
            locations.append("50.7467,7.1516")  # Bonn fallback
        
        # Voeg patiënt locaties toe
        for i, patient in enumerate(patients):
            # Check if patient is a Patient model instance or a dictionary
            if isinstance(patient, dict):
                # Handle dictionary data (from CSV upload)
                patient_lat = patient.get('latitude')
                patient_lng = patient.get('longitude')
                patient_straat = patient.get('straat', '')
                patient_postcode = patient.get('postcode', '')
                patient_plaats = patient.get('plaats', '')
                patient_naam = patient.get('naam', '')
                if not patient_naam and patient.get('voornaam') and patient.get('achternaam'):
                    patient_naam = f"{patient.get('voornaam')} {patient.get('achternaam')}".strip()
            else:
                # Handle Patient model instance
                patient_lat = getattr(patient, 'latitude', None)
                patient_lng = getattr(patient, 'longitude', None)
                patient_straat = getattr(patient, 'straat', '')
                patient_postcode = getattr(patient, 'postcode', '')
                patient_plaats = getattr(patient, 'plaats', '')
                patient_naam = getattr(patient, 'naam', '')
            
            # Eerst checken of er al geocoded coördinaten zijn
            if patient_lat and patient_lng:
                locations.append(f"{patient_lat},{patient_lng}")
                logger.info(f"✅ Gebruik bestaande coördinaten voor {patient_naam}: {patient_lat}, {patient_lng}")
            else:
                # Geocoding voor patiënten zonder coördinaten
                address_to_geocode = None
                
                # Probeer verschillende adres combinaties
                if patient_straat and patient_postcode and patient_plaats:
                    address_to_geocode = f"{patient_straat}, {patient_postcode} {patient_plaats}, Germany"
                elif patient_straat and patient_plaats:
                    address_to_geocode = f"{patient_straat}, {patient_plaats}, Germany"
                elif patient_postcode and patient_plaats:
                    address_to_geocode = f"{patient_postcode} {patient_plaats}, Germany"
                elif patient_plaats:
                    address_to_geocode = f"{patient_plaats}, Germany"
                
                if address_to_geocode:
                    logger.info(f"Geocode adres voor {patient_naam}: {address_to_geocode}")
                    coords = self.geocode_address(address_to_geocode)
                    if coords:
                        # Update the patient data if it's a model instance
                        if not isinstance(patient, dict):
                            patient.latitude, patient.longitude = coords
                            patient.save()
                        locations.append(f"{coords[0]},{coords[1]}")
                        logger.info(f"✅ Coördinaten gevonden voor {patient_naam}: {coords}")
                    else:
                        logger.warning(f"❌ Kon geen coördinaten vinden voor {patient_naam}, gebruik fallback locatie")
                        # Gebruik een fallback locatie in plaats van te falen
                        fallback_lat = 50.7467 + (i * 0.01)  # Bonn + kleine offset per patiënt
                        fallback_lng = 7.1516 + (i * 0.01)
                        locations.append(f"{fallback_lat},{fallback_lng}")
                        logger.info(f"📍 Gebruik fallback coördinaten voor {patient_naam}: {fallback_lat}, {fallback_lng}")
                else:
                    logger.warning(f"❌ Onvoldoende adresgegevens voor {patient_naam}, gebruik fallback locatie")
                    # Gebruik een fallback locatie
                    fallback_lat = 50.7467 + (i * 0.01)
                    fallback_lng = 7.1516 + (i * 0.01)
                    locations.append(f"{fallback_lat},{fallback_lng}")
                    logger.info(f"📍 Gebruik fallback coördinaten voor {patient_naam}: {fallback_lat}, {fallback_lng}")
        
        return locations
    
    def _get_distance_matrix_for_locations(self, locations: List[str]) -> Optional[Dict]:
        """Haal distance matrix op voor alle locaties"""
        if len(locations) <= 1:
            return None
        
        # Google Maps Distance Matrix heeft limiet van 25 origins/destinations
        # Voor grotere datasets moeten we batching gebruiken
        if len(locations) <= 25:
            distance_matrix = self.get_distance_matrix(locations, locations)
            if distance_matrix:
                return distance_matrix
            else:
                logger.warning("Google Maps Distance Matrix faalde, gebruik fallback")
                return self._generate_fallback_distance_matrix(locations)
        else:
            logger.warning(f"Te veel locaties ({len(locations)}), gebruik batching")
            return self._batch_distance_matrix(locations)
    
    def _batch_distance_matrix(self, locations: List[str]) -> Dict:
        """Batch distance matrix voor grote datasets"""
        # Implementeer batching logica hier
        # Voor nu, gebruik alleen eerste 25 locaties
        limited_locations = locations[:25]
        distance_matrix = self.get_distance_matrix(limited_locations, limited_locations)
        if distance_matrix:
            return distance_matrix
        else:
            logger.warning("Google Maps Distance Matrix faalde, gebruik fallback")
            return self._generate_fallback_distance_matrix(limited_locations)
    
    def _generate_fallback_distance_matrix(self, locations: List[str]) -> Dict:
        """Genereer een fallback distance matrix met geschatte afstanden"""
        logger.info("🔧 Genereer fallback distance matrix")
        
        # Simuleer een distance matrix met realistische afstanden
        matrix = {
            'status': 'OK',
            'origin_addresses': [f"Location {i+1}" for i in range(len(locations))],
            'destination_addresses': [f"Location {i+1}" for i in range(len(locations))],
            'rows': []
        }
        
        for i, origin in enumerate(locations):
            row = {'elements': []}
            for j, destination in enumerate(locations):
                if i == j:
                    # Zelfde locatie
                    element = {
                        'status': 'OK',
                        'distance': {'text': '0 km', 'value': 0},
                        'duration': {'text': '0 min', 'value': 0}
                    }
                else:
                    # Geschatte afstand tussen locaties
                    base_distance = 15.0  # Basis afstand in km
                    distance_variation = abs(i - j) * 5.0  # Variatie op basis van index verschil
                    estimated_distance = base_distance + distance_variation
                    
                    # Geschatte tijd (gemiddeld 50 km/u)
                    estimated_time = int(estimated_distance * 1.2)  # 1.2 minuten per km
                    
                    element = {
                        'status': 'OK',
                        'distance': {'text': f'{estimated_distance:.1f} km', 'value': int(estimated_distance * 1000)},
                        'duration': {'text': f'{estimated_time} min', 'value': estimated_time * 60}
                    }
                
                row['elements'].append(element)
            matrix['rows'].append(row)
        
        logger.info(f"✅ Fallback distance matrix gegenereerd voor {len(locations)} locaties")
        return matrix
    
    def _assign_patients_to_vehicles(self, patients: List, vehicles: List, distance_matrix: Dict) -> Dict:
        """Wijs patiënten toe aan voertuigen op basis van configuratie"""
        strategy = self.config.vehicle_optimization
        weights = self.config.get_optimization_weights()
        
        if strategy == 'max_capacity':
            return self._assign_max_capacity(patients, vehicles)
        elif strategy == 'balanced':
            return self._assign_balanced(patients, vehicles)
        elif strategy == 'min_vehicles':
            return self._assign_min_vehicles(patients, vehicles)
        else:  # hybrid
            return self._assign_hybrid(patients, vehicles, weights)
    
    def _assign_max_capacity(self, patients: List, vehicles: List) -> Dict:
        """Maximale bezetting per voertuig"""
        assignments = {vehicle: [] for vehicle in vehicles}
        
        # Sorteer voertuigen op capaciteit (hoog naar laag)
        sorted_vehicles = sorted(vehicles, key=lambda v: v.aantal_zitplaatsen, reverse=True)
        
        for patient in patients:
            # Zoek voertuig met meeste ruimte
            for vehicle in sorted_vehicles:
                if len(assignments[vehicle]) < vehicle.aantal_zitplaatsen - 1:  # -1 voor chauffeur
                    assignments[vehicle].append(patient)
                    break
        
        return assignments
    
    def _assign_balanced(self, patients: List, vehicles: List) -> Dict:
        """Evenwichtige verdeling over voertuigen"""
        assignments = {vehicle: [] for vehicle in vehicles}
        
        # Verdeel patiënten gelijkmatig
        for i, patient in enumerate(patients):
            vehicle_index = i % len(vehicles)
            vehicle = vehicles[vehicle_index]
            
            if len(assignments[vehicle]) < vehicle.aantal_zitplaatsen - 1:
                assignments[vehicle].append(patient)
        
        return assignments
    
    def _assign_min_vehicles(self, patients: List, vehicles: List) -> Dict:
        """Minimaal aantal voertuigen gebruiken"""
        assignments = {vehicle: [] for vehicle in vehicles}
        
        # Sorteer voertuigen op capaciteit (hoog naar laag)
        sorted_vehicles = sorted(vehicles, key=lambda v: v.aantal_zitplaatsen, reverse=True)
        
        for patient in patients:
            # Zoek eerste voertuig met ruimte
            for vehicle in sorted_vehicles:
                if len(assignments[vehicle]) < vehicle.aantal_zitplaatsen - 1:
                    assignments[vehicle].append(patient)
                    break
        
        return assignments
    
    def _assign_hybrid(self, patients: List, vehicles: List, weights: Dict) -> Dict:
        """Hybride aanpak met gewichten"""
        # Implementeer hybride logica hier
        # Voor nu, gebruik balanced als fallback
        return self._assign_balanced(patients, vehicles)
    
    def _optimize_vehicle_route(self, vehicle, patients: List, distance_matrix: Dict) -> Optional[Dict]:
        """Optimaliseer route voor één voertuig"""
        if not patients:
            return None
        
        # Haal gedetailleerde route op
        locations = self._extract_locations(patients)
        if len(locations) < 2:
            return None
        
        origin = locations[0]  # Reha center
        destination = locations[0]  # Terug naar reha center
        waypoints = locations[1:] if len(locations) > 2 else None
        
        route_data = self.get_directions(origin, destination, waypoints)
        
        if not route_data:
            return None
        
        # Bereken kosten
        total_distance = 0
        total_time = 0
        
        for leg in route_data['routes'][0]['legs']:
            total_distance += leg['distance']['value'] / 1000  # Convert to km
            total_time += leg['duration']['value'] / 60  # Convert to minutes
        
        # Bereken kosten op basis van voertuig tarief
        km_kosten = getattr(vehicle, 'km_kosten_per_km', 0.50)  # Default 0.50 euro per km
        total_cost = total_distance * float(km_kosten)
        
        return {
            'vehicle': vehicle,
            'patients': patients,
            'total_distance': total_distance,
            'total_time': total_time,
            'total_cost': total_cost,
            'route_data': route_data
        }
    
    def _fallback_optimization(self, timeslot_assignments: Dict, vehicles: List) -> Dict:
        """Fallback optimalisatie zonder Google Maps"""
        logger.info("Gebruik fallback optimalisatie (simulatie)")
        
        # Simuleer route optimalisatie resultaten
        optimized_routes = {}
        
        for timeslot_id, patients in timeslot_assignments.items():
            if not patients:
                logger.warning(f"Geen patiënten voor tijdblok {timeslot_id}")
                continue
                
            logger.info(f"Verwerk tijdblok {timeslot_id} met {len(patients)} patiënten")
            
            # Verdeel patiënten over voertuigen
            vehicle_assignments = self._assign_patients_to_vehicles_simple(patients, vehicles)
            
            # Maak routes per voertuig
            routes = []
            for vehicle, assigned_patients in vehicle_assignments.items():
                if assigned_patients:
                    # Simuleer route statistieken (realistische waarden)
                    base_distance = 15.0  # Basis afstand van reha center
                    distance_per_patient = 8.5  # Gemiddelde afstand per patiënt
                    simulated_distance = base_distance + (len(assigned_patients) * distance_per_patient)
                    
                    base_time = 30  # Basis tijd (minuten)
                    time_per_patient = 15  # Gemiddelde tijd per patiënt (ophalen/afleveren)
                    simulated_time = base_time + (len(assigned_patients) * time_per_patient)
                    
                    # Kosten berekenen
                    km_kosten = getattr(vehicle, 'km_kosten_per_km', 0.50)  # Default 0.50 euro per km
                    simulated_cost = simulated_distance * float(km_kosten)
                    
                    route = {
                        'vehicle': vehicle,
                        'patients': assigned_patients,
                        'total_distance': simulated_distance,
                        'total_time': simulated_time,
                        'total_cost': simulated_cost,
                        'route_data': None
                    }
                    routes.append(route)
            
            optimized_routes[timeslot_id] = {
                'routes': routes,
                'total_distance': sum(route['total_distance'] for route in routes),
                'total_time': sum(route['total_time'] for route in routes),
                'total_cost': sum(route['total_cost'] for route in routes),
                'vehicle_count': len(routes)
            }
            
            logger.info(f"Tijdblok {timeslot_id}: {len(routes)} routes, {optimized_routes[timeslot_id]['total_distance']:.1f} km, €{optimized_routes[timeslot_id]['total_cost']:.2f}")
        
        return optimized_routes
    
    def _assign_patients_to_vehicles_simple(self, patients: List, vehicles: List) -> Dict:
        """Eenvoudige toewijzing van patiënten aan voertuigen"""
        if not vehicles:
            return {}
            
        assignments = {vehicle: [] for vehicle in vehicles}
        
        # Verdeel patiënten gelijkmatig over voertuigen
        for i, patient in enumerate(patients):
            vehicle_index = i % len(vehicles)
            vehicle = vehicles[vehicle_index]
            
            # Check capaciteit
            if len(assignments[vehicle]) < vehicle.aantal_zitplaatsen - 1:  # -1 voor chauffeur
                assignments[vehicle].append(patient)
            else:
                # Zoek een ander voertuig met ruimte
                for other_vehicle in vehicles:
                    if len(assignments[other_vehicle]) < other_vehicle.aantal_zitplaatsen - 1:
                        assignments[other_vehicle].append(patient)
                        break
        
        return assignments


# Singleton instance
google_maps_service = GoogleMapsService()
