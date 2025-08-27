"""
Simpele route planner met OptaPlanner-style constraints
Verdeelt patiënten over voertuigen en maakt basis routes met hard/soft constraints
"""
import logging
from django.utils import timezone
from datetime import datetime, timedelta
import math

logger = logging.getLogger(__name__)


class SimpleRouteService:
    """
    Eenvoudige route planning service met OptaPlanner-style constraints
    """
    
    def __init__(self):
        self.default_travel_time_per_stop = 15  # minuten per stop
        self.default_service_time = 5  # minuten per patiënt ophalen/afzetten
        
        # OptaPlanner-style constraints
        self.constraints = {
            # HARD CONSTRAINTS (moeten altijd voldaan worden)
            'hard': {
                'max_vehicle_capacity': True,  # Voertuig mag niet overvol
                'max_travel_time': True,       # Maximale reistijd per voertuig
                'time_windows': True,          # Tijdvensters moeten gerespecteerd worden
                'vehicle_availability': True,  # Voertuig moet beschikbaar zijn
                'patient_requirements': True,  # Patiënt vereisten (rolstoel, etc.)
            },
            
            # SOFT CONSTRAINTS (proberen te optimaliseren)
            'soft': {
                'minimize_total_distance': True,    # Minimale totale afstand
                'minimize_total_time': True,        # Minimale totale tijd
                'balance_vehicle_load': True,       # Evenwichtige verdeling over voertuigen
                'prefer_same_vehicle': True,        # Patiënten bij voorkeur inzelfde voertuig
                'minimize_waiting_time': True,      # Minimale wachttijd voor patiënten
            }
        }
    
    def validate_hard_constraints(self, route, vehicle, patients):
        """
        Valideer hard constraints voor een route
        Returns: (is_valid, violations)
        """
        violations = []
        
        # 1. Vehicle capacity constraint
        if self.constraints['hard']['max_vehicle_capacity']:
            total_passengers = len(patients)
            if total_passengers > vehicle.aantal_zitplaatsen:
                violations.append(f"Voertuig {vehicle.kenteken} heeft capaciteit {vehicle.aantal_zitplaatsen} maar {total_passengers} patiënten toegewezen")
        
        # 2. Max travel time constraint
        if self.constraints['hard']['max_travel_time']:
            estimated_travel_time = self.calculate_route_travel_time(route)
            max_allowed_time = vehicle.maximale_rit_tijd * 60  # Convert to minutes
            if estimated_travel_time > max_allowed_time:
                violations.append(f"Route tijd ({estimated_travel_time} min) overschrijdt maximum ({max_allowed_time} min) voor voertuig {vehicle.kenteken}")
        
        # 3. Time windows constraint
        if self.constraints['hard']['time_windows']:
            time_violations = self.check_time_windows(route, patients)
            violations.extend(time_violations)
        
        # 4. Vehicle availability constraint
        if self.constraints['hard']['vehicle_availability']:
            if vehicle.status != 'beschikbaar':
                violations.append(f"Voertuig {vehicle.kenteken} is niet beschikbaar (status: {vehicle.status})")
        
        # 5. Patient requirements constraint
        if self.constraints['hard']['patient_requirements']:
            requirement_violations = self.check_patient_requirements(vehicle, patients)
            violations.extend(requirement_violations)
        
        is_valid = len(violations) == 0
        return is_valid, violations
    
    def calculate_soft_constraints_score(self, route, vehicle, patients):
        """
        Bereken soft constraints score (lager = beter)
        Returns: total_score, breakdown
        """
        score = 0
        breakdown = {}
        
        # 1. Minimize total distance
        if self.constraints['soft']['minimize_total_distance']:
            total_distance = self.calculate_route_distance(route)
            score += total_distance * 0.1  # Weight factor
            breakdown['distance'] = total_distance
        
        # 2. Minimize total time
        if self.constraints['soft']['minimize_total_time']:
            total_time = self.calculate_route_travel_time(route)
            score += total_time * 0.05  # Weight factor
            breakdown['time'] = total_time
        
        # 3. Balance vehicle load
        if self.constraints['soft']['balance_vehicle_load']:
            load_percentage = len(patients) / vehicle.aantal_zitplaatsen
            # Penalty voor te lage of te hoge belasting
            if load_percentage < 0.3:  # Onder 30% belasting
                score += (0.3 - load_percentage) * 100
            elif load_percentage > 0.9:  # Boven 90% belasting
                score += (load_percentage - 0.9) * 50
            breakdown['load_balance'] = load_percentage
        
        # 4. Minimize waiting time
        if self.constraints['soft']['minimize_waiting_time']:
            waiting_time = self.calculate_waiting_time(route, patients)
            score += waiting_time * 0.2
            breakdown['waiting_time'] = waiting_time
        
        breakdown['total_score'] = score
        return score, breakdown
    
    def check_time_windows(self, route, patients):
        """
        Check of alle patiënten binnen hun tijdvenster passen
        """
        violations = []
        
        for patient in patients:
            # Check pickup time window
            if hasattr(patient, 'ophaal_tijd') and patient.ophaal_tijd:
                pickup_time = patient.ophaal_tijd.time()
                
                # Vind geschatte aankomsttijd in route
                estimated_arrival = self.get_estimated_arrival_time(route, patient)
                
                if estimated_arrival:
                    # Tolerantie van 15 minuten
                    tolerance = timedelta(minutes=15)
                    time_diff = abs((estimated_arrival - pickup_time).total_seconds() / 60)
                    
                    if time_diff > tolerance.total_seconds() / 60:
                        violations.append(f"Patiënt {patient.naam}: geschatte aankomst {estimated_arrival} buiten tolerantie van pickup tijd {pickup_time}")
        
        return violations
    
    def check_patient_requirements(self, vehicle, patients):
        """
        Check of voertuig voldoet aan patiënt vereisten
        """
        violations = []
        
        # Check rolstoel capaciteit
        wheelchair_patients = [p for p in patients if p.rolstoel]
        if wheelchair_patients and vehicle.speciale_zitplaatsen < len(wheelchair_patients):
            violations.append(f"Voertuig {vehicle.kenteken} heeft {vehicle.speciale_zitplaatsen} rolstoel plaatsen maar {len(wheelchair_patients)} rolstoel patiënten")
        
        return violations
    
    def calculate_route_distance(self, route):
        """
        Bereken totale afstand van een route
        """
        total_distance = 0
        stops = route.get('stops', [])
        
        for i in range(len(stops) - 1):
            current_stop = stops[i]
            next_stop = stops[i + 1]
            
            distance = self.calculate_distance(
                current_stop['latitude'], current_stop['longitude'],
                next_stop['latitude'], next_stop['longitude']
            )
            total_distance += distance
        
        return total_distance
    
    def calculate_route_travel_time(self, route):
        """
        Bereken totale reistijd van een route
        """
        total_distance = self.calculate_route_distance(route)
        travel_time = self.calculate_travel_time(total_distance)
        
        # Voeg service tijd toe voor elke stop
        stops = route.get('stops', [])
        service_time = len(stops) * self.default_service_time
        
        return travel_time + service_time
    
    def calculate_waiting_time(self, route, patients):
        """
        Bereken totale wachttijd voor patiënten
        """
        total_waiting = 0
        
        for patient in patients:
            if hasattr(patient, 'ophaal_tijd') and patient.ophaal_tijd:
                pickup_time = patient.ophaal_tijd.time()
                estimated_arrival = self.get_estimated_arrival_time(route, patient)
                
                if estimated_arrival:
                    # Bereken wachttijd (positief = patiënt wacht, negatief = te laat)
                    time_diff = (estimated_arrival - pickup_time).total_seconds() / 60
                    if time_diff > 0:  # Patiënt moet wachten
                        total_waiting += time_diff
        
        return total_waiting
    
    def get_estimated_arrival_time(self, route, patient):
        """
        Haal geschatte aankomsttijd op voor een patiënt in een route
        """
        stops = route.get('stops', [])
        
        for stop in stops:
            if stop.get('patient_id') == patient.id:
                time_str = stop.get('estimated_time', '')
                try:
                    # Parse time string (HH:MM format)
                    hour, minute = map(int, time_str.split(':'))
                    return datetime.time(hour, minute)
                except:
                    return None
        
        return None
    
    def optimize_route_with_constraints(self, vehicles, patients, timeslot):
        """
        Optimaliseer route met OptaPlanner-style constraints
        """
        best_routes = []
        best_score = float('inf')
        
        # Probeer verschillende combinaties van voertuigen en patiënten
        for vehicle in vehicles:
            # Test verschillende groepen patiënten
            for i in range(1, min(len(patients) + 1, vehicle.aantal_zitplaatsen + 1)):
                patient_group = patients[:i]
                
                # Maak test route
                test_route = self.create_route_for_vehicle(vehicle, patient_group, timeslot, 'HALEN')
                
                # Valideer hard constraints
                is_valid, violations = self.validate_hard_constraints(test_route, vehicle, patient_group)
                
                if is_valid:
                    # Bereken soft constraints score
                    score, breakdown = self.calculate_soft_constraints_score(test_route, vehicle, patient_group)
                    
                    if score < best_score:
                        best_score = score
                        best_routes = [test_route]
                        logger.info(f"Betere route gevonden: score={score}, breakdown={breakdown}")
                else:
                    logger.warning(f"Route schendt hard constraints: {violations}")
        
        return best_routes
    
    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """
        Bereken afstand tussen twee GPS coordinaten (Haversine formule)
        Returns: afstand in kilometers
        """
        if not all([lat1, lon1, lat2, lon2]):
            return 10  # Default 10km als GPS ontbreekt
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371  # Earth radius in kilometers
        
        return c * r
    
    def calculate_travel_time(self, distance_km, speed_kmh=30):
        """
        Bereken reistijd gebaseerd op afstand en gemiddelde snelheid
        Returns: tijd in minuten
        """
        if distance_km <= 0:
            return 5  # Minimum 5 minuten voor stop
        
        # Basis reistijd
        travel_time = (distance_km / speed_kmh) * 60  # Convert to minutes
        
        # Voeg extra tijd toe voor stadsverkeer, stoplichten, etc.
        city_factor = 1.3  # 30% extra tijd voor stedelijke omgeving
        travel_time *= city_factor
        
        # Minimum 5 minuten, maximum 60 minuten tussen stops
        return max(5, min(60, travel_time))
    
    def optimize_route_order(self, patients, reha_center_coords=None):
        """
        Optimaliseer de volgorde van patiënten gebaseerd op GPS afstanden
        Gebruikt een eenvoudige nearest neighbor algoritme
        """
        # Haal depot coördinaten op als niet meegegeven
        if reha_center_coords is None:
            from planning.models import Location
            home_location = Location.get_home_location()
            if home_location and home_location.latitude and home_location.longitude:
                reha_center_coords = (home_location.latitude, home_location.longitude)
            else:
                reha_center_coords = (50.8, 7.0)  # Fallback naar Bonn
        if len(patients) <= 1:
            return patients
        
        # Start met reha center coordinaten
        current_coords = reha_center_coords
        optimized_order = []
        remaining_patients = list(patients)
        
        while remaining_patients:
            # Vind dichtstbijzijnde patiënt
            closest_patient = None
            closest_distance = float('inf')
            
            for patient in remaining_patients:
                patient_coords = (
                    patient.latitude or reha_center_coords[0],
                    patient.longitude or reha_center_coords[1]
                )
                
                distance = self.calculate_distance(
                    current_coords[0], current_coords[1],
                    patient_coords[0], patient_coords[1]
                )
                
                if distance < closest_distance:
                    closest_distance = distance
                    closest_patient = patient
            
            # Voeg dichtstbijzijnde patiënt toe aan route
            if closest_patient:
                optimized_order.append(closest_patient)
                remaining_patients.remove(closest_patient)
                current_coords = (
                    closest_patient.latitude or reha_center_coords[0],
                    closest_patient.longitude or reha_center_coords[1]
                )
        
        return optimized_order
    
    def group_patients_by_timeslot(self, patients):
        """
        Groepeer patiënten per tijdblok (HALEN en BRINGEN apart)
        """
        halen_groups = {}
        bringen_groups = {}
        
        for patient in patients:
            # HALEN tijdblok
            if patient.halen_tijdblok and patient.halen_tijdblok.actief:
                timeslot_id = patient.halen_tijdblok.id
                if timeslot_id not in halen_groups:
                    halen_groups[timeslot_id] = {
                        'timeslot': patient.halen_tijdblok,
                        'patients': [],
                        'type': 'HALEN'
                    }
                halen_groups[timeslot_id]['patients'].append(patient)
            
            # BRINGEN tijdblok
            if patient.bringen_tijdblok and patient.bringen_tijdblok.actief:
                timeslot_id = patient.bringen_tijdblok.id
                if timeslot_id not in bringen_groups:
                    bringen_groups[timeslot_id] = {
                        'timeslot': patient.bringen_tijdblok,
                        'patients': [],
                        'type': 'BRINGEN'
                    }
                bringen_groups[timeslot_id]['patients'].append(patient)
        
        return halen_groups, bringen_groups
    
    def distribute_patients_over_vehicles(self, patient_group, vehicles):
        """
        Verdeel patiënten van een tijdblok over beschikbare voertuigen
        Nu met OptaPlanner-style constraints
        """
        patients = patient_group['patients']
        timeslot = patient_group['timeslot']
        route_type = patient_group['type']
        
        if not patients or not vehicles:
            return []
        
        # Gebruik constraint-based optimalisatie
        optimized_routes = self.optimize_route_with_constraints(vehicles, patients, timeslot)
        
        if optimized_routes:
            return optimized_routes
        
        # Fallback naar originele methode als optimalisatie faalt
        logger.warning("Constraint optimalisatie faalde, gebruik fallback methode")
        return self.distribute_patients_fallback(patient_group, vehicles)
    
    def distribute_patients_fallback(self, patient_group, vehicles):
        """
        Fallback methode voor patiënt verdeling (originele logica)
        """
        patients = patient_group['patients']
        timeslot = patient_group['timeslot']
        route_type = patient_group['type']
        
        if not patients or not vehicles:
            return []
        
        # Sorteer voertuigen op capaciteit (grootste eerst)
        sorted_vehicles = sorted(vehicles, key=lambda v: v.aantal_zitplaatsen, reverse=True)
        
        routes = []
        remaining_patients = patients.copy()
        
        # Verdeel patiënten over voertuigen
        for vehicle in sorted_vehicles:
            if not remaining_patients:
                break
            
            # Bepaal hoeveel patiënten in dit voertuig passen
            vehicle_capacity = vehicle.aantal_zitplaatsen
            
            # Neem maximaal vehicle_capacity patiënten
            patients_for_vehicle = remaining_patients[:vehicle_capacity]
            
            if patients_for_vehicle:
                route = self.create_route_for_vehicle(
                    vehicle, patients_for_vehicle, timeslot, route_type
                )
                routes.append(route)
                
                # Verwijder toegewezen patiënten uit de lijst
                remaining_patients = remaining_patients[vehicle_capacity:]
        
        # Als er nog patiënten over zijn, probeer ze toe te voegen aan bestaande routes
        if remaining_patients and routes:
            logger.warning(f"Er zijn nog {len(remaining_patients)} patiënten over die niet toegewezen konden worden")
        
        return routes
    
    def create_route_for_vehicle(self, vehicle, patients, timeslot, route_type):
        """
        Maak een route voor een specifiek voertuig
        """
        # Bepaal start tijd gebaseerd op tijdblok
        if route_type == 'HALEN':
            start_time = timeslot.heen_start_tijd
            end_time = timeslot.heen_eind_tijd
        else:  # BRINGEN
            start_time = timeslot.terug_start_tijd  
            end_time = timeslot.terug_eind_tijd
        
        # Maak stops voor elke patiënt
        stops = []
        current_time = datetime.combine(timezone.now().date(), start_time)
        
        # Haal depot coördinaten op uit Django Admin
        from planning.models import Location
        home_location = Location.get_home_location()
        if home_location and home_location.latitude and home_location.longitude:
            reha_center_coords = (home_location.latitude, home_location.longitude)
        else:
            reha_center_coords = (50.8, 7.0)  # Fallback naar Bonn
        
        if route_type == 'HALEN':
            # Voor HALEN: start bij patiënten, eindig bij reha center
            # Optimaliseer van eerste patiënt naar reha center
            sorted_patients = self.optimize_route_order(patients)
        else:  # BRINGEN
            # Voor BRINGEN: start bij reha center, ga naar patiënten
            # Optimaliseer van reha center naar patiënten
            sorted_patients = self.optimize_route_order(patients)
        
        for i, patient in enumerate(sorted_patients):
            # Bepaal stop type
            if route_type == 'HALEN':
                stop_type = 'PICKUP'
                location_name = f"Ophalen: {patient.naam}"
            else:  # BRINGEN
                stop_type = 'DROPOFF'
                location_name = f"Afzetten: {patient.naam}"
            
            # Bouw adres samen (alleen niet-lege delen)
            address_parts = []
            if patient.straat:
                address_parts.append(patient.straat)
            if patient.postcode:
                address_parts.append(patient.postcode)
            if patient.plaats:
                address_parts.append(patient.plaats)
            
            address = ", ".join(address_parts) if address_parts else "Geen adres beschikbaar"
            
            # Check voor geocoding waarschuwingen
            geocoding_warning = None
            
            # Check voor lege adresgegevens
            if not patient.straat or not patient.postcode or not patient.plaats:
                geocoding_warning = "Onvolledig adres - voeg straat, postcode en plaats toe!"
            # Check geocoding status
            elif hasattr(patient, 'geocoding_status'):
                if patient.geocoding_status == 'failed':
                    geocoding_warning = "Adres niet gevonden - controleer locatie!"
                elif patient.geocoding_status == 'default':
                    geocoding_warning = "Standaard locatie gebruikt - verifieer adres"
                elif patient.geocoding_status == 'pending' or not patient.geocoding_status:
                    geocoding_warning = "Adres nog niet gecontroleerd - voer geocoding uit!"
            # Check voor missende GPS coordinaten
            elif not patient.latitude or not patient.longitude:
                geocoding_warning = "Geen GPS coördinaten - voer geocoding uit!"
            
            stops.append({
                'sequence': i + 1,
                'patient_id': patient.id,
                'patient_name': patient.naam,
                'location_name': location_name,
                'address': address,
                'phone': patient.telefoonnummer or 'Geen telefoon',
                'estimated_time': current_time.strftime('%H:%M'),
                'type': stop_type,
                'latitude': patient.latitude or 52.0,
                'longitude': patient.longitude or 4.0,
                'geocoding_warning': geocoding_warning,
                'wheelchair': patient.rolstoel
            })
            
            # Bereken reistijd naar volgende stop
            if i < len(sorted_patients) - 1:
                # Afstand naar volgende patiënt
                next_patient = sorted_patients[i + 1]
                current_coords = (patient.latitude or reha_center_coords[0], patient.longitude or reha_center_coords[1])
                next_coords = (next_patient.latitude or reha_center_coords[0], next_patient.longitude or reha_center_coords[1])
                
                distance = self.calculate_distance(current_coords[0], current_coords[1], next_coords[0], next_coords[1])
                travel_time = self.calculate_travel_time(distance)
            else:
                # Laatste stop - reistijd naar reha center (of default)
                current_coords = (patient.latitude or reha_center_coords[0], patient.longitude or reha_center_coords[1])
                distance = self.calculate_distance(current_coords[0], current_coords[1], reha_center_coords[0], reha_center_coords[1])
                travel_time = self.calculate_travel_time(distance)
            
            # Voeg service tijd toe (tijd om patiënt op te halen/af te zetten)
            total_time = travel_time + self.default_service_time
            current_time += timedelta(minutes=total_time)
        
        # Voeg reha center toe als laatste/eerste stop
        if route_type == 'HALEN':
            # Voor HALEN: eindig bij reha center
            stops.append({
                'sequence': len(stops) + 1,
                'patient_id': None,
                'patient_name': home_location.name if home_location else 'Reha Center',
                'location_name': 'Aankomst Reha Center',
                'address': home_location.address if home_location else 'Reha Center, Behandellocatie',
                'phone': 'Hoofdnummer',
                'estimated_time': current_time.strftime('%H:%M'),
                'type': 'DESTINATION',
                'latitude': reha_center_coords[0],
                'longitude': reha_center_coords[1]
            })
        else:  # BRINGEN
            # Voor BRINGEN: start bij reha center
            reha_stop = {
                'sequence': 0,
                'patient_id': None,
                'patient_name': home_location.name if home_location else 'Reha Center',
                'location_name': 'Vertrek Reha Center',
                'address': home_location.address if home_location else 'Reha Center, Behandellocatie',
                'phone': 'Hoofdnummer',
                'estimated_time': start_time.strftime('%H:%M'),
                'type': 'ORIGIN',
                'latitude': reha_center_coords[0],
                'longitude': reha_center_coords[1]
            }
            stops.insert(0, reha_stop)
            # Update sequence numbers
            for i, stop in enumerate(stops[1:], 1):
                stop['sequence'] = i
        
        # Bereken constraint scores
        is_valid, violations = self.validate_hard_constraints({
            'stops': stops,
            'vehicle': vehicle,
            'patients': patients
        }, vehicle, patients)
        
        score, breakdown = self.calculate_soft_constraints_score({
            'stops': stops,
            'vehicle': vehicle,
            'patients': patients
        }, vehicle, patients)
        
        return {
            'vehicle_name': vehicle.kenteken,
            'vehicle_referentie': vehicle.referentie,
            'vehicle_model': vehicle.merk_model,
            'vehicle_color': vehicle.kleur,
            'vehicle_capacity': vehicle.aantal_zitplaatsen,
            'timeslot_name': timeslot.naam,
            'route_type': route_type,
            'start_time': start_time.strftime('%H:%M'),
            'end_time': end_time.strftime('%H:%M'),
            'total_patients': len(patients),
            'total_stops': len(stops),
            'estimated_duration': len(stops) * self.default_travel_time_per_stop,
            'stops': stops,
            'constraints': {
                'hard_constraints_valid': is_valid,
                'hard_constraint_violations': violations,
                'soft_constraints_score': score,
                'soft_constraints_breakdown': breakdown
            }
        }
    
    def plan_simple_routes(self, vehicles, patients):
        """
        Hoofdfunctie: plan alle routes voor alle tijdblokken met OptaPlanner-style constraints
        """
        try:
            logger.info(f"Starting constraint-based route planning for {patients.count()} patients and {vehicles.count()} vehicles")
            
            # Groepeer patiënten per tijdblok
            halen_groups, bringen_groups = self.group_patients_by_timeslot(patients)
            
            all_routes = []
            constraint_summary = {
                'total_routes': 0,
                'valid_routes': 0,
                'invalid_routes': 0,
                'total_violations': 0,
                'average_score': 0
            }
            
            # Verdeel voertuigen over tijdblokken
            vehicle_list = list(vehicles)
            vehicle_index = 0
            
            # Plan HALEN routes
            for group in halen_groups.values():
                if vehicle_index >= len(vehicle_list):
                    vehicle_index = 0  # Reset naar begin als alle voertuigen gebruikt zijn
                
                # Gebruik 1 voertuig per tijdblok, maar wissel af
                available_vehicles = [vehicle_list[vehicle_index]]
                routes = self.distribute_patients_over_vehicles(group, available_vehicles)
                all_routes.extend(routes)
                vehicle_index += 1
            
            # Plan BRINGEN routes  
            for group in bringen_groups.values():
                if vehicle_index >= len(vehicle_list):
                    vehicle_index = 0  # Reset naar begin als alle voertuigen gebruikt zijn
                
                # Gebruik 1 voertuig per tijdblok, maar wissel af
                available_vehicles = [vehicle_list[vehicle_index]]
                routes = self.distribute_patients_over_vehicles(group, available_vehicles)
                all_routes.extend(routes)
                vehicle_index += 1
            
            # Analyseer constraint resultaten
            total_score = 0
            for route in all_routes:
                constraint_summary['total_routes'] += 1
                
                if route.get('constraints', {}).get('hard_constraints_valid', False):
                    constraint_summary['valid_routes'] += 1
                else:
                    constraint_summary['invalid_routes'] += 1
                    violations = route.get('constraints', {}).get('hard_constraint_violations', [])
                    constraint_summary['total_violations'] += len(violations)
                
                score = route.get('constraints', {}).get('soft_constraints_score', 0)
                total_score += score
            
            if constraint_summary['total_routes'] > 0:
                constraint_summary['average_score'] = total_score / constraint_summary['total_routes']
            
            logger.info(f"Constraint-based route planning completed: {len(all_routes)} routes generated")
            logger.info(f"Constraint summary: {constraint_summary}")
            
            return all_routes
            
        except Exception as e:
            logger.error(f"Error in constraint-based route planning: {e}")
            return []


# Singleton instance
simple_route_service = SimpleRouteService()
