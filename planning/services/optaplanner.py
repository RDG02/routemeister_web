import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class OptaPlannerService:
    """
    Service voor communicatie met OptaPlanner API
    Gebaseerd op bestaande PHP implementatie
    """
    
    def __init__(self):
        # Haal configuratie uit database, fallback naar settings
        from planning.models import Configuration
        
        self.base_url = Configuration.get_value('OPTAPLANNER_URL') or getattr(settings, 'OPTAPLANNER_URL', 'http://localhost:8080')
        self.enabled = Configuration.get_value('OPTAPLANNER_ENABLED', 'True').lower() == 'true' or getattr(settings, 'OPTAPLANNER_ENABLED', True)
        self.session = requests.Session()
        
        # Timeout settings uit database
        timeout = Configuration.get_value('OPTAPLANNER_TIMEOUT', '30')
        self.session.timeout = int(timeout)
    
    def is_enabled(self):
        """Check if OptaPlanner is enabled"""
        return self.enabled
    
    def clear_planner(self):
        """Reset the planner - equivalent to api/clear"""
        try:
            response = self.session.get(f"{self.base_url}/api/clear")
            logger.info(f"Clear planner response: {response.text}")
            return response.text
        except requests.RequestException as e:
            logger.error(f"Error clearing planner: {e}")
            return None
    
    def clear_vehicles(self):
        """Clear all vehicles - equivalent to api/clearvehicle"""
        try:
            response = self.session.post(f"{self.base_url}/api/clearvehicle")
            success = response.text.strip().lower() == 'cleared'
            logger.info(f"Clear vehicles response: {response.text} (success: {success})")
            return success
        except requests.RequestException as e:
            logger.error(f"Error clearing vehicles: {e}")
            return False
    
    def add_vehicle(self, vehicle):
        """
        Add a vehicle to the planner
        URL: api/vehicleadd/{name}/{people}/{specialseats}/{kmRate}/{maxDriveTimeInSeconds}
        """
        try:
            # Convert vehicle data to OptaPlanner format
            name = vehicle.kenteken.replace(' ', '_').replace('-', '_')
            people = vehicle.aantal_zitplaatsen
            specialseats = vehicle.speciale_zitplaatsen
            
            # Convert km_kosten_per_km to cents (multiply by 100)
            km_rate = int(float(vehicle.km_kosten_per_km) * 100)
            
            # Convert maximale_rit_tijd to seconds (if it's in hours)
            max_drive_time = int(vehicle.maximale_rit_tijd * 3600) if vehicle.maximale_rit_tijd < 100 else int(vehicle.maximale_rit_tijd)
            
            url = f"{self.base_url}/api/vehicleadd/{name}/{people}/{specialseats}/{km_rate}/{max_drive_time}"
            response = self.session.get(url)
            
            logger.info(f"Add vehicle {name}: {response.text}")
            return response.text
            
        except requests.RequestException as e:
            logger.error(f"Error adding vehicle {vehicle.kenteken}: {e}")
            return None
    
    def add_location(self, patient, location_type, preferred_vehicle='_'):
        """
        Add a location/stop to the planner
        URL: api/locationadd/{locationName}/{longitude}/{latitude}/{special}/{drv}/{preferredVehicle}/{pickup}
        
        Args:
            patient: Patient object
            location_type: 'pickup' or 'dropoff'
            preferred_vehicle: Vehicle name or '_' for any
        """
        try:
            # Create unique location name with proper encoding
            location_name = f"{patient.naam.replace(' ', '_').replace('-', '_').replace('.', '_')}_{location_type[0].upper()}"
            
            # Use patient coordinates or default (you might want to geocode addresses later)
            longitude = patient.longitude or 4.0  # Default to Netherlands center
            latitude = patient.latitude or 52.0
            
            # Determine special requirements
            special = 1 if patient.rolstoel else 0  # Use the rolstoel field
            drv = 0  # Assuming no DRV for now
            pickup = 1 if location_type == 'pickup' else 0
            
            url = f"{self.base_url}/api/locationadd/{location_name}/{longitude}/{latitude}/{special}/{drv}/{preferred_vehicle}/{pickup}"
            response = self.session.get(url)
            
            logger.info(f"Add location {location_name}: {response.text}")
            return response.text
            
        except requests.RequestException as e:
            logger.error(f"Error adding location for patient {patient.naam}: {e}")
            return None
    
    def get_route_result(self):
        """
        Get the optimized route result
        Returns: List of vehicles with their routes
        """
        try:
            response = self.session.get(f"{self.base_url}/api/route")
            result = response.json()
            
            logger.info(f"Route result received: {result.get('vehicleCount', 0)} vehicles")
            return result
            
        except requests.RequestException as e:
            logger.error(f"Error getting route result: {e}")
            return {"routes": [], "vehicleCount": 0}
        except ValueError as e:
            logger.error(f"Error parsing route result JSON: {e}")
            return {"routes": [], "vehicleCount": 0}
    
    def plan_routes(self, vehicles, patients):
        """
        Complete planning process
        
        Args:
            vehicles: QuerySet of Vehicle objects
            patients: QuerySet of Patient objects
            
        Returns:
            List of optimized routes or None if error
        """
        if not self.is_enabled():
            logger.warning("OptaPlanner is disabled")
            return None
        
        try:
            logger.info("Starting route planning process")
            
            # Step 1: Clear planner
            clear_result = self.clear_planner()
            if clear_result is None:
                return None
            
            # Step 2: Clear vehicles
            if not self.clear_vehicles():
                return None
            
            # Step 3: Add vehicles
            for vehicle in vehicles:
                if vehicle.status == 'beschikbaar':
                    self.add_vehicle(vehicle)
            
            # Step 4: Add patient locations (pickup and dropoff)
            for patient in patients:
                if patient.toegewezen_tijdblok and patient.status in ['nieuw', 'gepland']:
                    # Add pickup location
                    self.add_location(patient, 'pickup')
                    
                    # Add dropoff location (use destination or default)
                    self.add_location(patient, 'dropoff')
            
            # Step 5: Get optimized routes
            routes = self.get_route_result()
            
            logger.info(f"Route planning completed: {len(routes)} routes generated")
            return routes
            
        except Exception as e:
            logger.error(f"Error in route planning process: {e}")
            return None


# Singleton instance
optaplanner_service = OptaPlannerService()
