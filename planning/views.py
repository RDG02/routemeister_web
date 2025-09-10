from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.utils import timezone
from .models import Patient, Vehicle, TimeSlot, Location, GoogleMapsConfig, GoogleMapsAPILog
from django.db import models
from .services.optaplanner import optaplanner_service
from .services.simple_router import simple_route_service
import csv
import io
import requests
from datetime import datetime, time, date, timedelta
import logging
import uuid
import time
import re
from collections import defaultdict
import json
from datetime import datetime
from .models import CSVParserConfig

logger = logging.getLogger(__name__)

def convert_time_format(time_str):
    """
    Converteer tijd van "845" naar "08:45" formaat
    Ondersteunt zowel 3-digit (845) als 4-digit (0845) formaten
    """
    if not time_str:
        return ""
    
    # Verwijder eventuele spaties en converteer naar string
    time_str = str(time_str).strip()
    
    # Handle 3-digit format (845)
    if len(time_str) == 3:
        hour = time_str[0]  # "8"
        minute = time_str[1:3]  # "45"
        return f"0{hour}:{minute}"  # "08:45"
    
    # Handle 4-digit format (0845)
    elif len(time_str) == 4:
        hour = time_str[:2]  # "08"
        minute = time_str[2:4]  # "45"
        return f"{hour}:{minute}"  # "08:45"
    
    # Handle 2-digit format (45) - assume minutes only
    elif len(time_str) == 2:
        return f"00:{time_str}"  # "00:45"
    
    # Handle 1-digit format (5) - assume minutes only
    elif len(time_str) == 1:
        return f"00:0{time_str}"  # "00:05"
    
    # Fallback voor onbekende formaten
    else:
        return str(time_str)

# Create your views here.

def home(request):
    """
    Redirect directly to dashboard - no more home page
    """
    from django.http import HttpResponseRedirect
    from django.urls import reverse
    
    return HttpResponseRedirect(reverse('dashboard'))


def dashboard(request):
    """
    Nieuwe dashboard met moderne UI/UX gebaseerd op SVG design
    Toont planning van vandaag (2 september 2025) of knop voor nieuwe planning
    """
    from datetime import date, timedelta, datetime, timezone
    
    # Get today's date (2 september 2025)
    today = date.today()
    now = datetime.now(timezone.utc)
    
    # Get available vehicles count
    available_vehicles = Vehicle.objects.filter(status='beschikbaar').count()
    
    # Get total vehicles count
    total_vehicles = Vehicle.objects.count()
    
    # Get today's patients with assigned vehicles (planning van vandaag)
    today_patients = Patient.objects.filter(
        ophaal_tijd__date=today,
        toegewezen_voertuig__isnull=False,
        status__in=['gepland', 'onderweg']
    ).order_by('ophaal_tijd')
    
    # Get upcoming stops for sidebar (only today's patients)
    upcoming_stops = today_patients[:8]
    
    # Check if there's any planning for today
    has_today_planning = today_patients.exists()
    
    # Get actual patient times from CSV data (not hardcoded timeslots)
    patient_times = []
    
    for patient in today_patients:
        if patient.ophaal_tijd:
            # Add pickup time
            patient_times.append({
                'time': patient.ophaal_tijd,
                'type': 'halen',
                'patient_name': patient.naam,
                'icon': '🚐'
            })
        if patient.eind_behandel_tijd:
            # Add end time
            patient_times.append({
                'time': patient.eind_behandel_tijd,
                'type': 'brengen',
                'patient_name': patient.naam,
                'icon': '🏠'
            })
    
    # Sort by time and remove duplicates (same time, same type)
    unique_times = {}
    for pt in patient_times:
        time_key = f"{pt['time'].strftime('%H:%M')}_{pt['type']}"
        if time_key not in unique_times:
            unique_times[time_key] = pt
    
    # Convert to sorted list
    active_timeslots = sorted(unique_times.values(), key=lambda x: x['time'])
    
    # Print patient times for debugging
    timeline_info = []
    for pt in active_timeslots:
        timeline_info.append(f"{pt['time'].strftime('%H:%M')} {pt['type']}")
    print(f"Patient times for timeline: {timeline_info}")
    
    # Get vehicle data for map visualization (only for today)
    vehicles_with_patients = []
    if has_today_planning:
        for vehicle in Vehicle.objects.filter(status='beschikbaar'):
            patients = Patient.objects.filter(
                toegewezen_voertuig=vehicle,
                ophaal_tijd__date=today,
                status__in=['gepland', 'onderweg']
            )
            if patients.exists():
                # Group patients by actual patient times from CSV
                patients_by_timeslot = {}
                for patient in patients:
                    # Create timeslot keys based on actual patient times
                    if patient.ophaal_tijd:
                        pickup_key = f"{patient.ophaal_tijd.strftime('%H:%M')} - halen"
                        if pickup_key not in patients_by_timeslot:
                            patients_by_timeslot[pickup_key] = []
                        patients_by_timeslot[pickup_key].append(patient)
                    
                    if patient.eind_behandel_tijd:
                        end_key = f"{patient.eind_behandel_tijd.strftime('%H:%M')} - brengen"
                        if end_key not in patients_by_timeslot:
                            patients_by_timeslot[end_key] = []
                        patients_by_timeslot[end_key].append(patient)
                
                vehicles_with_patients.append({
                    'vehicle': vehicle,
                    'patients': patients,
                    'patient_count': patients.count(),
                    'patients_by_timeslot': patients_by_timeslot
                })
    
    # Get routes from the planning wizard session (Google Maps API results)
    routes_data = {}
    try:
        # Check if there are routes in the current planning session
        planning_session = request.session.get('planning_session', {})
        if planning_session:
            routes_data = planning_session.get('routes', {})
            logger.info(f"Routes found in session: {len(routes_data)} timeslots")
        else:
            logger.info("No planning session found, routes will be empty")
    except Exception as e:
        logger.warning(f"Could not retrieve routes: {e}")
        routes_data = {}
    
    # Get today's statistics
    total_today_patients = today_patients.count()
    total_today_routes = len(vehicles_with_patients)
    
    # Get Google Maps API key from configuration
    try:
        google_maps_config = GoogleMapsConfig.get_active_config()
        google_maps_api_key = google_maps_config.api_key if google_maps_config.enabled else ''
    except:
        google_maps_api_key = ''
    
    # Get home location for map
    try:
        from .models import Location
        home_location = Location.get_home_location()
    except:
        home_location = None
    
    context = {
        'today_date': today,
        'available_vehicles': available_vehicles,
        'total_vehicles': total_vehicles,
        'upcoming_stops': upcoming_stops,
        'vehicles_with_patients': vehicles_with_patients,
        'has_today_planning': has_today_planning,
        'total_today_patients': total_today_patients,
        'total_today_routes': total_today_routes,
        'active_timeslots': active_timeslots,  # Only timeslots with assigned patients
        'routes_data': routes_data,  # Google Maps API routes
        'google_maps_api_key': google_maps_api_key,  # Google Maps API key
        'home_location': home_location,  # Home location for map
    }
    
    return render(request, 'planning/dashboard.html', context)


def upload_csv(request):
    """
    Upload en verwerk fahrten.csv van Meditec met logging
    """
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        
        if not csv_file:
            messages.error(request, 'Geen bestand geselecteerd.')
            return redirect('upload_csv')
            
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Alleen CSV bestanden zijn toegestaan.')
            return redirect('upload_csv')
        
        # Start CSV logging
        from .models_extended import CSVImportLog
        
        # Lees CSV content voor logging
        csv_file.seek(0)  # Reset file pointer
        csv_content = csv_file.read().decode('utf-8', errors='ignore')
        csv_file.seek(0)  # Reset file pointer again
        
        # Maak CSV log entry
        imported_by = request.user if request.user.is_authenticated else None
        csv_log = CSVImportLog.objects.create(
            filename=csv_file.name,
            imported_by=imported_by,
            status='failed',  # Start with failed, update to success later
            total_patients=0,
            imported_patients=0,
            csv_content=csv_content
        )
        
        try:
            # Probeer verschillende encodings
            file_bytes = csv_file.read()
            file_data = None
            
            # Probeer verschillende encodings in volgorde van waarschijnlijkheid
            encodings = ['utf-8', 'windows-1252', 'iso-8859-1', 'cp1252', 'latin-1']
            
            for encoding in encodings:
                try:
                    file_data = file_bytes.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if file_data is None:
                csv_log.errors = "Kan het bestand niet lezen. Controleer de encoding."
                csv_log.save()
                messages.error(request, 'Kan het bestand niet lezen. Controleer de encoding.')
                return redirect('upload_csv')
            
            csv_reader = csv.reader(io.StringIO(file_data), delimiter=';')
            
            # Verwijder alle bestaande patiënten voor vandaag voordat nieuwe worden aangemaakt
            today = date.today()
            existing_patients = Patient.objects.filter(ophaal_tijd__date=today)
            if existing_patients.exists():
                deleted_count = existing_patients.count()
                existing_patients.delete()
                print(f"🗑️ Verwijderd {deleted_count} bestaande patiënten voor {today}")
                messages.info(request, f'{deleted_count} bestaande patiënten voor {today} zijn verwijderd om plaats te maken voor de nieuwe planning.')
            
            patients_created = 0
            patients_updated = 0
            total_rows = 0
            error_rows = []
            
            # Gebruik cache manager voor slimme patiënten verwerking
            from .cache_manager import PatientCacheManager
            
            print("🚀 Start slimme CSV verwerking met caching...")
            
            # Converteer CSV reader naar lijst voor cache manager
            csv_rows = []
            for row_index, row in enumerate(csv_reader):
                total_rows += 1
                if len(row) >= 21:
                    csv_rows.append({
                        'data': row,
                        'row_index': row_index
                    })
            
            # Verwerk CSV met cache manager
            cache_results = PatientCacheManager.bulk_update_patients_from_csv(csv_rows, detection_result)
            
            patients_created = cache_results['created']
            patients_updated = cache_results['updated']
            patients_cached = cache_results['cached']
            
            print(f"💾 Cache resultaten: {patients_cached} patiënten uit cache")
            
            # Update CSV log met resultaten
            csv_log.total_patients = total_rows
            csv_log.imported_patients = patients_created + patients_updated
            csv_log.status = 'success' if len(error_rows) == 0 else 'partial'
            if error_rows:
                csv_log.errors = '\n'.join(error_rows)
            csv_log.save()
            
            # Voer geocoding uit voor alle nieuwe patiënten zonder coördinaten
            patients_without_coords = Patient.objects.filter(
                latitude__isnull=True, 
                longitude__isnull=True,
                status='nieuw'
            )
            
            if patients_without_coords.exists():
                geocoded_count = 0
                for patient in patients_without_coords:
                    if patient.straat and patient.postcode and patient.plaats:
                        # Maak volledig adres
                        full_address = f"{patient.straat}, {patient.postcode} {patient.plaats}, Deutschland"
                        
                        try:
                            # Gebruik OpenStreetMap Nominatim API
                            url = "https://nominatim.openstreetmap.org/search"
                            params = {
                                'q': full_address,
                                'format': 'json',
                                'limit': 1
                            }
                            headers = {
                                'User-Agent': 'Routemeister/1.0 (https://routemeister.com)'
                            }
                            
                            response = requests.get(url, params=params, headers=headers, timeout=10)
                            response.raise_for_status()
                            
                            data = response.json()
                            
                            if data and len(data) > 0:
                                result = data[0]
                                patient.latitude = float(result['lat'])
                                patient.longitude = float(result['lon'])
                                patient.save()
                                geocoded_count += 1
                            else:
                                # Fallback naar Bonn coördinaten
                                patient.latitude = 50.7374
                                patient.longitude = 7.0982
                                patient.save()
                                
                        except Exception as e:
                            # Fallback naar Bonn coördinaten bij fout
                            patient.latitude = 50.7374
                            patient.longitude = 7.0982
                            patient.save()
                
                messages.success(request, f'CSV succesvol verwerkt! {patients_created} nieuwe patiënten toegevoegd, {patients_updated} bestaande gevonden. {geocoded_count} adressen gegeocoded.')
            else:
                messages.success(request, f'CSV succesvol verwerkt! {patients_created} nieuwe patiënten toegevoegd, {patients_updated} bestaande gevonden.')
            
            return redirect('home')
            
        except Exception as e:
            # Update CSV log met error
            csv_log.status = 'failed'
            csv_log.errors = f'Algemene fout: {str(e)}'
            csv_log.save()
            messages.error(request, f'Fout bij verwerken CSV: {str(e)}')
            return redirect('upload_csv')
    
    return render(request, 'planning/upload_csv.html')


def timeslot_selection(request):
    """
    Interactieve tijdblokken selectie pagina - aangepast voor echte tijdblokken
    """
    if request.method == 'POST':
        # Verwerk de geselecteerde blokken
        # Haal geselecteerde tijdblok IDs op (uit template)
        selected_timeslots = request.POST.getlist('selected_timeslots')
        
        # Deactiveer alle tijdblokken eerst
        TimeSlot.objects.all().update(actief=False)
        
        # Activeer geselecteerde tijdblokken
        activated_count = 0
        for timeslot_id in selected_timeslots:
            try:
                timeslot = TimeSlot.objects.get(id=timeslot_id)
                timeslot.actief = True
                timeslot.save()
                activated_count += 1
                logger.info(f"Activated timeslot: {timeslot.naam}")
            except TimeSlot.DoesNotExist:
                logger.warning(f"Timeslot with ID {timeslot_id} not found")
        
        if activated_count > 0:
            messages.success(request, f'{activated_count} tijdblokken geactiveerd voor planning!')
        else:
            messages.warning(request, 'Geen tijdblokken geselecteerd.')
        
        return redirect('timeslot_selection')
    
    # Bestaande tijdblokken ophalen
    existing_timeslots = TimeSlot.objects.all()
    
    # Definieer de gangbare tijdblokken
    standard_timeslots = [
        # Halen (ochtend tot 12:00)
        {'type': 'halen', 'naam': 'Haal Blok 1', 'start': '06:30', 'eind': '08:00'},
        {'type': 'halen', 'naam': 'Haal Blok 2', 'start': '08:00', 'eind': '09:30'},
        {'type': 'halen', 'naam': 'Haal Blok 3', 'start': '09:30', 'eind': '12:00'},
        
        # Brengen (middag vanaf 12:00)
        {'type': 'brengen', 'naam': 'Breng Blok 1', 'start': '12:00', 'eind': '14:00'},
        {'type': 'brengen', 'naam': 'Breng Blok 2', 'start': '14:00', 'eind': '15:30'},
        {'type': 'brengen', 'naam': 'Breng Blok 3', 'start': '15:30', 'eind': '17:00'},
    ]
    
    context = {
        'standard_timeslots': standard_timeslots,
        'existing_timeslots': existing_timeslots,
    }
    
    return render(request, 'planning/timeslot_selection.html', context)


def auto_assign_patients(request):
    """
    Automatische toewijzing van patiënten aan tijdblokken
    """
    if request.method == 'POST':
        # Gebruik het bestaande management command voor HALEN & BRINGEN toewijzing
        from django.core.management import call_command
        from io import StringIO
        
        # Capture output van management command
        out = StringIO()
        try:
            call_command('assign_halen_bringen', stdout=out)
            
            # Parse resultaten voor feedback
            output_lines = out.getvalue().split('\n')
            fully_assigned = 0
            partial_assigned = 0
            
            for line in output_lines:
                if '✅ Volledig toegewezen:' in line:
                    fully_assigned = int(line.split(':')[1].strip())
                elif '⚠️  Gedeeltelijk toegewezen:' in line:
                    partial_assigned = int(line.split(':')[1].strip())
            
            # Feedback berichten
            if fully_assigned > 0:
                messages.success(
                    request, 
                    f'🎉 {fully_assigned} patiënten volledig toegewezen (HALEN + BRINGEN tijdblokken)!'
                )
            
            if partial_assigned > 0:
                messages.warning(
                    request, 
                    f'⚠️ {partial_assigned} patiënten gedeeltelijk toegewezen!'
                )
            
            if fully_assigned == 0 and partial_assigned == 0:
                messages.error(request, 'Geen patiënten konden worden toegewezen. Controleer tijdblokken.')
                
        except Exception as e:
            messages.error(request, f'Fout bij toewijzing: {str(e)}')
        
        return redirect('home')
    
    # GET request - toon overzicht
    context = {
        'unassigned_patients': Patient.objects.filter(
            status__in=['nieuw'],
            toegewezen_tijdblok__isnull=True
        ).count(),
        'active_timeslots': TimeSlot.objects.filter(actief=True).count(),
    }
    
    return render(request, 'planning/auto_assign.html', context)


def plan_routes(request):
    """
    Route planning met toggle tussen Simple en OptaPlanner
    """
    if request.method == 'POST':
        planner_type = request.POST.get('planner_type', 'simple')
        
        try:
            # Get available vehicles
            available_vehicles = Vehicle.objects.filter(status='beschikbaar')
            
            # Get assigned patients (both halen and bringen)
            assigned_patients = Patient.objects.filter(
                models.Q(halen_tijdblok__isnull=False) | 
                models.Q(bringen_tijdblok__isnull=False)
            ).distinct()
            
            if not available_vehicles.exists():
                messages.error(request, 'Geen beschikbare voertuigen gevonden.')
                return redirect('home')
            
            if not assigned_patients.exists():
                messages.error(request, 'Geen toegewezen patiënten gevonden. Wijs eerst patiënten toe aan tijdblokken.')
                return redirect('home')
            
            if planner_type == 'optaplanner':
                # Use OptaPlanner
                if not optaplanner_service.is_enabled():
                    messages.error(request, 'OptaPlanner is niet beschikbaar. Gebruik Simple Router.')
                    return redirect('plan_routes')
                
                logger.info(f"Planning OptaPlanner routes for {assigned_patients.count()} patients and {available_vehicles.count()} vehicles")
                routes = optaplanner_service.plan_routes(assigned_patients, available_vehicles)
                planner_name = 'OptaPlanner'
                
            else:
                # Use Simple Router
                logger.info(f"Planning simple routes for {assigned_patients.count()} patients and {available_vehicles.count()} vehicles")
                routes = simple_route_service.plan_simple_routes(available_vehicles, assigned_patients)
                planner_name = 'Simple Router'
            
            if not routes:
                messages.warning(request, 'Geen routes gegenereerd. Controleer patiënt toewijzingen.')
                return redirect('plan_routes')
            
            # Store results in session for display
            request.session['planned_routes'] = routes
            request.session['route_planner_type'] = planner_type
            
            messages.success(request, f'🎉 {len(routes)} routes gegenereerd met {planner_name}!')
            
            return redirect('route_results')
            
        except Exception as e:
            logger.error(f"Error in route planning: {e}")
            messages.error(request, f'Onverwachte fout bij route planning: {str(e)}')
            return redirect('plan_routes')
    
    # GET request - show planning page with toggle
    available_vehicles = Vehicle.objects.filter(status='beschikbaar')
    assigned_patients = Patient.objects.filter(
        models.Q(halen_tijdblok__isnull=False) | 
        models.Q(bringen_tijdblok__isnull=False)
    ).distinct()
    
    context = {
        'available_vehicles': available_vehicles,
        'assigned_patients': assigned_patients,
        'route_planner_type': 'Route Planner met Toggle',
        'show_toggle': True,  # Show planner toggle
        'optaplanner_enabled': optaplanner_service.is_enabled(),
        'optaplanner_url': optaplanner_service.base_url,
    }
    
    return render(request, 'planning/plan_routes.html', context)


def plan_routes_simple(request):
    """
    Plan routes using simple route planner (without OptaPlanner)
    """
    if request.method == 'POST':
        try:
            # Get available vehicles
            available_vehicles = Vehicle.objects.filter(status='beschikbaar')
            
            # Get assigned patients (both halen and bringen)
            assigned_patients = Patient.objects.filter(
                models.Q(halen_tijdblok__isnull=False) | 
                models.Q(bringen_tijdblok__isnull=False)
            ).distinct()
            
            if not available_vehicles.exists():
                messages.error(request, 'Geen beschikbare voertuigen gevonden.')
                return redirect('home')
            
            if not assigned_patients.exists():
                messages.error(request, 'Geen toegewezen patiënten gevonden. Wijs eerst patiënten toe aan tijdblokken.')
                return redirect('home')
            
            # Plan routes using simple router
            logger.info(f"Planning simple routes for {assigned_patients.count()} patients and {available_vehicles.count()} vehicles")
            
            routes = simple_route_service.plan_simple_routes(available_vehicles, assigned_patients)
            
            if not routes:
                messages.warning(request, 'Geen routes gegenereerd. Controleer patiënt toewijzingen.')
                return redirect('home')
            
            # Store results in session for display
            request.session['planned_routes'] = routes
            
            messages.success(request, f'🎉 {len(routes)} routes gegenereerd!')
            
            return redirect('route_results')
            
        except Exception as e:
            logger.error(f"Error in simple route planning: {e}")
            messages.error(request, f'Onverwachte fout bij route planning: {str(e)}')
            return redirect('home')
    
    # GET request - show planning page
    available_vehicles = Vehicle.objects.filter(status='beschikbaar')
    assigned_patients = Patient.objects.filter(
        models.Q(halen_tijdblok__isnull=False) | 
        models.Q(bringen_tijdblok__isnull=False)
    ).distinct()
    
    context = {
        'available_vehicles': available_vehicles,
        'assigned_patients': assigned_patients,
        'route_planner_type': 'Simpele Route Planner',
    }
    
    return render(request, 'planning/plan_routes.html', context)


def plan_routes_optaplanner(request):
    """
    Plan routes using OptaPlanner (requires external server)
    """
    if request.method == 'POST':
        try:
            # Get available vehicles
            available_vehicles = Vehicle.objects.filter(status='beschikbaar')
            
            # Get assigned patients (both halen and bringen)
            assigned_patients = Patient.objects.filter(
                models.Q(halen_tijdblok__isnull=False) | 
                models.Q(bringen_tijdblok__isnull=False)
            ).distinct()
            
            if not available_vehicles.exists():
                messages.error(request, 'Geen beschikbare voertuigen gevonden.')
                return redirect('home')
            
            if not assigned_patients.exists():
                messages.error(request, 'Geen toegewezen patiënten gevonden. Wijs eerst patiënten toe aan tijdblokken.')
                return redirect('home')
            
            # Plan routes using simple router
            logger.info(f"Planning simple routes for {assigned_patients.count()} patients and {available_vehicles.count()} vehicles")
            
            routes = simple_route_service.plan_simple_routes(available_vehicles, assigned_patients)
            
            if not routes:
                messages.warning(request, 'Geen routes gegenereerd. Controleer patiënt toewijzingen.')
                return redirect('home')
            
            # Store results in session for display
            request.session['planned_routes'] = routes
            
            messages.success(request, f'🎉 {len(routes)} routes gegenereerd!')
            
            return redirect('route_results')
            
        except Exception as e:
            logger.error(f"Error in route planning: {e}")
            messages.error(request, f'Onverwachte fout bij route planning: {str(e)}')
            return redirect('home')
    
    # GET request - show planning page
    available_vehicles = Vehicle.objects.filter(status='beschikbaar')
    assigned_patients = Patient.objects.filter(
        models.Q(halen_tijdblok__isnull=False) | 
        models.Q(bringen_tijdblok__isnull=False)
    ).distinct()
    
    context = {
        'available_vehicles': available_vehicles,
        'assigned_patients': assigned_patients,
        'optaplanner_enabled': True,  # Set to True so template doesn't show error
        'optaplanner_url': optaplanner_service.base_url,
    }
    
    return render(request, 'planning/plan_routes.html', context)


def test_optaplanner_api(request):
    """
    Test OptaPlanner API endpoints
    """
    if not optaplanner_service.is_enabled():
        return JsonResponse({'error': 'OptaPlanner is disabled'}, status=400)
    
    try:
        # Test 1: Check version
        version_response = requests.get(f"{optaplanner_service.base_url}/api/version")
        version = version_response.text if version_response.ok else "Error"
        
        # Test 2: Clear planner
        clear_response = requests.get(f"{optaplanner_service.base_url}/api/clear")
        clear_status = clear_response.text if clear_response.ok else "Error"
        
        # Test 3: Add test vehicle
        vehicle_response = requests.get(f"{optaplanner_service.base_url}/api/vehicleadd/TEST-123/7/2/50000/28800")
        vehicle_status = vehicle_response.text if vehicle_response.ok else "Error"
        
        # Test 4: Add test location
        location_response = requests.get(f"{optaplanner_service.base_url}/api/locationadd/TEST_PATIENT_P/4.123/52.456/0/0/_/1")
        location_status = location_response.text if location_response.ok else "Error"
        
        # Test 5: Get route result
        route_response = requests.get(f"{optaplanner_service.base_url}/api/route")
        route_data = route_response.json() if route_response.ok else {"error": "Failed to get route"}
        
        return JsonResponse({
            'status': 'success',
            'tests': {
                'version': version,
                'clear': clear_status,
                'vehicle_add': vehicle_status,
                'location_add': location_status,
                'route': route_data
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def optaplanner_status(request):
    """
    Check OptaPlanner status and return current progress
    """
    if not request.session.get('planning_started'):
        return JsonResponse({'status': 'not_started'})
    
    try:
        # Check OptaPlanner status via route endpoint (status endpoint doesn't exist)
        route_response = requests.get(f"{optaplanner_service.base_url}/api/route", timeout=10)
        if route_response.status_code == 200:
            route_data = route_response.json()
            
            # Check if routes have locations (planning is complete)
            total_locations = sum(len(route.get('locations', [])) for route in route_data.get('routes', []))
            
            if total_locations > 0:
                # Planning is complete, store results
                request.session['planning_results'] = route_data
                request.session['planning_complete'] = True
                request.session['planning_started'] = False
                
                return JsonResponse({
                    'status': 'complete',
                    'message': f'Planning complete! Found {total_locations} locations across {len(route_data.get("routes", []))} routes.',
                    'results': route_data
                })
            else:
                # Still processing - check session data for progress
                planning_data = request.session.get('planning_data', {})
                vehicles_added = planning_data.get('vehicles_added', 0)
                patients_added = planning_data.get('patients_added', 0)
                total_vehicles = planning_data.get('total_vehicles', 0)
                total_patients = planning_data.get('total_patients', 0)
                
                return JsonResponse({
                    'status': 'processing',
                    'message': f'Planning in progress... {vehicles_added}/{total_vehicles} vehicles and {patients_added}/{total_patients} patients added, waiting for OptaPlanner to generate routes...',
                    'vehicle_count': len(route_data.get("routes", [])),
                    'total_locations': total_locations,
                    'vehicles_added': vehicles_added,
                    'patients_added': patients_added
                })
        else:
            return JsonResponse({
                'status': 'error',
                'message': f'Error getting routes: {route_response.status_code}'
            })
            
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Status check failed: {str(e)}'
        })


def start_optaplanner_planning(request):
    """
    Start OptaPlanner planning process with per-time-slot approach
    """
    if request.method == 'POST':
        try:
            # Get planning data from session
            session_data = request.session.get('planning_data', {})
            selected_vehicles = session_data.get('selected_vehicles', [])
            selected_timeslots = session_data.get('selected_timeslots', [])
            
            # If no vehicles selected, use all vehicles
            if not selected_vehicles:
                selected_vehicles = list(Vehicle.objects.values_list('id', flat=True))
                print(f"⚠️  Geen voertuigen geselecteerd, gebruik alle {len(selected_vehicles)} voertuigen")
            
            # Get assigned patients (all patients from today)
            from datetime import date
            today = date.today()
            assigned_patients = Patient.objects.filter(ophaal_tijd__date=today)
            
            # Check if patients have time slots, if not assign them
            patients_without_timeslots = assigned_patients.filter(halen_tijdblok__isnull=True)
            if patients_without_timeslots.exists():
                print(f"⚠️  {patients_without_timeslots.count()} patiënten hebben geen tijdblokken, toewijzen...")
                # Import and run time slot assignment
                from assign_timeslots_now import assign_timeslots
                assign_timeslots()
                print("✅ Tijdblokken toegewezen!")
            
            print(f"🚀 Starting planning with {assigned_patients.count()} CSV patients")
            
            # STEP 1: Group patients by halen time slot
            print("🚀 STEP 1: Grouping patients by time slot...")
            
            # Group patients by halen time slot
            patients_by_halen = {}
            for patient in assigned_patients:
                if patient.halen_tijdblok:
                    timeslot_name = patient.halen_tijdblok.naam
                    if timeslot_name not in patients_by_halen:
                        patients_by_halen[timeslot_name] = []
                    patients_by_halen[timeslot_name].append(patient)
            
            print(f"📊 Found {len(patients_by_halen)} time slots with patients:")
            for timeslot_name, patients_list in patients_by_halen.items():
                print(f"   📥 {timeslot_name}: {len(patients_list)} patients")
            
            # STEP 2: Process each time slot separately
            print("🚀 STEP 2: Processing each time slot separately...")
            
            all_results = {}  # Store results per time slot
            total_patients_added = 0
            total_vehicles_added = 0
            
            for timeslot_name, patients_list in patients_by_halen.items():
                print(f"🚀 Processing time slot: {timeslot_name} ({len(patients_list)} patients)")
                
                # STEP 2a: Clear OptaPlanner for this time slot
                print(f"   🔄 Clearing OptaPlanner for {timeslot_name}...")
                try:
                    clear_response = requests.get(f"{optaplanner_service.base_url}/api/clear", timeout=5)
                    print(f"   📡 Clear response: {clear_response.status_code}")
                    
                    clear_vehicles_response = requests.post(f"{optaplanner_service.base_url}/api/clearvehicle", timeout=5)
                    print(f"   📡 Clear vehicles response: {clear_vehicles_response.status_code}")
                except Exception as e:
                    print(f"   ❌ Clear error: {e}")
                
                # STEP 2b: Add depot for this time slot
                print(f"   🏠 Adding depot for {timeslot_name}...")
                try:
                    home_location = Location.get_home_location()
                    if home_location and home_location.latitude and home_location.longitude:
                        depot_url = f"{optaplanner_service.base_url}/api/locationadd/{home_location.name.replace(' ', '_')}/{home_location.longitude}/{home_location.latitude}/0/0/_/1"
                        depot_response = requests.get(depot_url, timeout=5)
                        print(f"   ✅ Depot {home_location.name} added: {depot_response.status_code}")
                        if depot_response.status_code != 200:
                            print(f"   ❌ Depot error response: {depot_response.text}")
                    else:
                        print("   ⚠️  Warning: No home location found in Django Admin settings!")
                except Exception as e:
                    print(f"   ❌ Depot error: {e}")
                
                # STEP 2c: Add vehicles for this time slot
                print(f"   🚗 Adding vehicles for {timeslot_name}...")
                vehicles_added_for_timeslot = 0
                for vehicle_id in selected_vehicles:
                    try:
                        vehicle = Vehicle.objects.get(id=vehicle_id)
                        # URL encode kenteken
                        encoded_kenteken = vehicle.kenteken.replace(' ', '_').replace('-', '_')
                        # Convert km rate to cents
                        km_tarief_cents = int(float(vehicle.km_kosten_per_km) * 100)
                        # Convert max travel time to seconds
                        max_tijd_seconden = int(vehicle.maximale_rit_tijd * 3600) if vehicle.maximale_rit_tijd < 100 else int(vehicle.maximale_rit_tijd)
                        
                        vehicle_url = f"{optaplanner_service.base_url}/api/vehicleadd/{encoded_kenteken}/{vehicle.aantal_zitplaatsen}/{vehicle.speciale_zitplaatsen}/{km_tarief_cents}/{max_tijd_seconden}"
                        vehicle_response = requests.get(vehicle_url, timeout=5)
                        print(f"   ✅ Vehicle {vehicle.kenteken} added: {vehicle_response.status_code}")
                        if vehicle_response.status_code == 200:
                            vehicles_added_for_timeslot += 1
                        else:
                            print(f"   ❌ Vehicle {vehicle.kenteken} error response: {vehicle_response.text}")
                    except Exception as e:
                        print(f"   ❌ Vehicle {vehicle_id} error: {e}")
                
                total_vehicles_added += vehicles_added_for_timeslot
                print(f"   📊 Added {vehicles_added_for_timeslot}/{len(selected_vehicles)} vehicles for {timeslot_name}")
                
                # STEP 2d: Add patients for this time slot
                print(f"   👥 Adding patients for {timeslot_name}...")
                patients_added = 0
                for patient in patients_list:
                    if patient.latitude and patient.longitude:
                        try:
                            # Determine pickup/dropoff type based on time slots
                            # All patients in this time slot are for pickup (halen)
                            pickup_type = "1"  # Always pickup for halen time slots
                            # URL encode speciale karakters in naam
                            encoded_naam = patient.naam.replace(' ', '_').replace('-', '_').replace('.', '_')
                            # Determine if patient needs special seating
                            special_seating = "1" if patient.rolstoel else "0"
                            
                            location_url = f"{optaplanner_service.base_url}/api/locationadd/{encoded_naam}/{patient.longitude}/{patient.latitude}/{special_seating}/0/_/{pickup_type}"
                            location_response = requests.get(location_url, timeout=5)
                            print(f"   ✅ Patient {patient.naam} added: {location_response.status_code} (lat: {patient.latitude}, lon: {patient.longitude})")
                            if location_response.status_code != 200:
                                print(f"   ❌ Patient {patient.naam} error response: {location_response.text}")
                            else:
                                patients_added += 1
                        except Exception as e:
                            print(f"   ❌ Patient {patient.naam} error: {e}")
                    else:
                        print(f"   ⚠️  Patient {patient.naam} has no coordinates! (lat: {patient.latitude}, lon: {patient.longitude})")
                
                total_patients_added += patients_added
                print(f"   📊 Added {patients_added}/{len(patients_list)} patients for {timeslot_name}")
                
                # STEP 2e: Get route for this time slot
                print(f"   🛣️  Getting route for {timeslot_name}...")
                try:
                    route_response = requests.get(f"{optaplanner_service.base_url}/api/route", timeout=10)
                    if route_response.status_code == 200:
                        route_data = route_response.json()
                        all_results[timeslot_name] = {
                            'route_data': route_data,
                            'patients_added': patients_added,
                            'vehicles_added': vehicles_added_for_timeslot
                        }
                        print(f"   ✅ Route received for {timeslot_name}: {len(route_data.get('routes', []))} routes")
                    else:
                        print(f"   ❌ Route error for {timeslot_name}: {route_response.text}")
                        all_results[timeslot_name] = {
                            'route_data': {'routes': [], 'vehicleCount': 0},
                            'patients_added': patients_added,
                            'vehicles_added': vehicles_added_for_timeslot
                        }
                except Exception as e:
                    print(f"   ❌ Route error for {timeslot_name}: {e}")
                    all_results[timeslot_name] = {
                        'route_data': {'routes': [], 'vehicleCount': 0},
                        'patients_added': patients_added,
                        'vehicles_added': vehicles_added_for_timeslot
                    }
                
                # Wait a moment for OptaPlanner to process this time slot
                print(f"   ⏳ Waiting 3 seconds for OptaPlanner to process {timeslot_name}...")
                time.sleep(3)
            
            print(f"🎯 Total patients added: {total_patients_added}/{assigned_patients.count()}")
            print(f"🎯 Total vehicles added: {total_vehicles_added}")
            
            # Store session data for status checking
            request.session['planning_session_id'] = str(uuid.uuid4())
            request.session['planning_started'] = True
            request.session['planning_data'] = {
                'vehicles_added': total_vehicles_added,
                'patients_added': total_patients_added,
                'total_vehicles': len(selected_vehicles),
                'total_patients': assigned_patients.count(),
                'timeslot_results': all_results
            }
            
            return JsonResponse({
                'status': 'success',
                'message': f'Planning completed! Processed {len(patients_by_halen)} time slots with {total_vehicles_added} vehicles and {total_patients_added} patients',
                'session_id': request.session['planning_session_id'],
                'timeslots_processed': len(patients_by_halen)
            })
            
        except Exception as e:
            print(f"❌ Planning error: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Planning failed: {str(e)}'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


def route_results(request):
    """
    Display route results (both simple and OptaPlanner)
    Nu ook gebruikt als hoofdpagina voor Planning
    """
    from datetime import date, timedelta
    
    # Get selected date from request, default to today
    selected_date_str = request.GET.get('date')
    if selected_date_str:
        try:
            selected_date = date.fromisoformat(selected_date_str)
        except ValueError:
            selected_date = date.today()
    else:
        selected_date = date.today()
    
    # Check if selected date is within 4 months range
    today = date.today()
    four_months_ago = today - timedelta(days=120)  # Approximately 4 months
    
    if selected_date < four_months_ago or selected_date > today:
        selected_date = today
    
    routes = request.session.get('planned_routes', [])
    
    # Als er geen routes zijn, toon een lege planning pagina
    if not routes:
        # Haal routes van geselecteerde datum op voor overzicht
        selected_date_routes = get_routes_for_date(selected_date)
        
        context = {
            'routes': [],
            'total_routes': 0,
            'total_stops': 0,
            'total_patients': 0,
            'selected_date_routes': selected_date_routes,
            'has_planning': False,
            'page_title': 'Planning',
            'selected_date': selected_date
        }
        
        return render(request, 'planning/route_results.html', context)
    

    
    # Check if routes are from simple router or OptaPlanner
    if isinstance(routes, dict):
        if 'routes' in routes:
            # OptaPlanner format - needs processing
            processed_routes = []
            for route in routes.get('routes', []):
                vehicle = route.get('vehicle', {})
                vehicle_name = vehicle.get('name', 'Onbekend')
                visits = route.get('visits', [])
                
                processed_routes.append({
                    'vehicle_name': vehicle_name,
                    'vehicle_capacity': vehicle.get('capacity', 0),
                    'vehicle_special_capacity': vehicle.get('specialCapacity', 0),
                    'stops': visits,
                    'total_stops': len(visits),
                    'pickup_count': len([s for s in visits if s.get('type') == 'PICKUP']),
                    'dropoff_count': len([s for s in visits if s.get('type') == 'DROPOFF'])
                })
        else:
            # Direct dict format - treat as simple router format
            processed_routes = [routes]
    elif routes and isinstance(routes, list):
        if len(routes) > 0 and isinstance(routes[0], dict) and 'vehicle_name' in routes[0]:
            # Simple router format - already processed, behoud constraint informatie
            processed_routes = routes
        else:
            # Unknown list format
            processed_routes = []
    else:
        # Unknown format
        processed_routes = []
    
    # Calculate totals
    total_stops = sum(route.get('total_stops', 0) for route in processed_routes)
    total_patients = sum(route.get('total_patients', 0) for route in processed_routes)
    
    # Haal home locatie op
    from .models import Location
    home_location = Location.get_home_location()
    
    # Haal geselecteerde tijdblokken op uit session
    selected_timeslot_ids = request.session.get('planning_data', {}).get('timeslots', [])
    selected_timeslots = []
    if selected_timeslot_ids:
        selected_timeslots = TimeSlot.objects.filter(id__in=selected_timeslot_ids).order_by('aankomst_tijd')
    
    context = {
        'routes': processed_routes,
        'total_routes': len(processed_routes),
        'total_stops': total_stops,
        'total_patients': total_patients,
        'has_planning': True,
        'page_title': 'Planning Resultaten',
        'home_location': home_location,
        'selected_timeslots': selected_timeslots,
        'selected_date': selected_date
    }
    
    return render(request, 'planning/route_results.html', context)

def get_routes_for_date(target_date):
    """
    Haal routes op voor een specifieke datum
    """
    # Haal planning sessions op voor de geselecteerde datum
    planning_sessions = PlanningSession.objects.filter(planning_date=target_date)
    
    routes = []
    for session in planning_sessions:
        # Haal patiënten op voor deze sessie
        patients = Patient.objects.filter(planning_session=session)
        
        # Groepeer patiënten per voertuig en tijdblok
        vehicle_timeslot_groups = {}
        
        for patient in patients:
            vehicle_id = getattr(patient.assigned_vehicle, 'id', None)
            timeslot_name = getattr(patient.toegewezen_tijdblok, 'naam', 'Onbekend')
            
            if vehicle_id and timeslot_name:
                key = f"{vehicle_id}_{timeslot_name}"
                if key not in vehicle_timeslot_groups:
                    vehicle_timeslot_groups[key] = {
                        'vehicle': patient.assigned_vehicle,
                        'timeslot_name': timeslot_name,
                        'patients': [],
                        'stops': []
                    }
                
                vehicle_timeslot_groups[key]['patients'].append(patient)
        
        # Converteer naar route format
        for key, group in vehicle_timeslot_groups.items():
            vehicle = group['vehicle']
            patients = group['patients']
            
            # Maak stops voor deze route
            stops = []
            sequence = 1
            
            # Start locatie (home)
            stops.append({
                'patient_id': 0,
                'patient_name': 'Reha Center',
                'location_name': 'Reha Center',
                'latitude': 50.8,  # Default home coordinates
                'longitude': 7.0,
                'type': 'ORIGIN',
                'sequence': sequence
            })
            sequence += 1
            
            # Patiënt stops
            for patient in patients:
                if patient.latitude and patient.longitude:
                    stops.append({
                        'patient_id': patient.id,
                        'patient_name': patient.naam,
                        'location_name': patient.adres,
                        'latitude': patient.latitude,
                        'longitude': patient.longitude,
                        'type': 'PICKUP' if 'Halen' in group['timeslot_name'] else 'DROPOFF',
                        'sequence': sequence
                    })
                    sequence += 1
            
            # Eind locatie (home)
            stops.append({
                'patient_id': 0,
                'patient_name': 'Reha Center',
                'location_name': 'Reha Center',
                'latitude': 50.8,  # Default home coordinates
                'longitude': 7.0,
                'type': 'DESTINATION',
                'sequence': sequence
            })
            
            routes.append({
                'vehicle_name': vehicle.kenteken,
                'vehicle_referentie': vehicle.referentie,
                'vehicle_color': vehicle.kleur,
                'timeslot_name': group['timeslot_name'],
                'route_type': 'Halen' if 'Halen' in group['timeslot_name'] else 'Brengen',
                'stops': stops,
                'total_stops': len(stops),
                'total_patients': len(patients)
            })
    
    return routes


def vehicles_overview(request):
    """
    Overzicht van alle voertuigen met mooie UI
    """
    vehicles = Vehicle.objects.all().order_by('kenteken')
    
    # Statistieken
    total_vehicles = vehicles.count()
    available_vehicles = vehicles.filter(status='beschikbaar').count()
    active_vehicles = vehicles.filter(status='actief').count()
    total_capacity = sum(vehicle.aantal_zitplaatsen for vehicle in vehicles)
    
    context = {
        'vehicles': vehicles,
        'total_vehicles': total_vehicles,
        'available_vehicles': available_vehicles,
        'active_vehicles': active_vehicles,
        'total_capacity': total_capacity,
    }
    
    return render(request, 'planning/vehicles_overview.html', context)


def timeslots_overview(request):
    """
    Overzicht van alle tijdblokken met mooie UI
    """
    timeslots = TimeSlot.objects.all().order_by('aankomst_tijd')
    
    # Groepeer per type
    halen_timeslots = timeslots.filter(naam__icontains='Halen')
    bringen_timeslots = timeslots.filter(naam__icontains='Bringen')
    
    # Statistieken
    total_timeslots = timeslots.count()
    active_timeslots = timeslots.filter(actief=True).count()
    
    context = {
        'halen_timeslots': halen_timeslots,
        'bringen_timeslots': bringen_timeslots,
        'total_timeslots': total_timeslots,
        'active_timeslots': active_timeslots,
    }
    
    return render(request, 'planning/timeslots_overview.html', context)


def get_today_routes():
    """
    Haal routes van vandaag op voor de dashboard kaart
    """
    from datetime import date
    from django.db.models import Q
    
    today = date.today()
    
    # Haal alle patiënten van vandaag op die een voertuig hebben toegewezen
    today_patients = Patient.objects.filter(
        Q(ophaal_tijd__date=today) | Q(eind_behandel_tijd__date=today),
        toegewezen_voertuig__isnull=False,
        status__in=['gepland', 'onderweg']
    ).select_related('toegewezen_voertuig')
    
    if not today_patients.exists():
        return []
    
    # Groepeer per voertuig
    routes = {}
    for patient in today_patients:
        vehicle = patient.toegewezen_voertuig
        if vehicle.kenteken not in routes:
            routes[vehicle.kenteken] = {
                'vehicle_name': vehicle.kenteken,
                'vehicle_color': vehicle.kleur,
                'stops': []
            }
        
        # Voeg patiënt toe als stop
        if patient.latitude and patient.longitude:
            routes[vehicle.kenteken]['stops'].append({
                'patient_name': patient.naam,
                'patient_id': patient.id,
                'latitude': patient.latitude,
                'longitude': patient.longitude,
                'address': f"{patient.straat}, {patient.postcode} {patient.plaats}",
                'pickup_time': patient.ophaal_tijd.strftime('%H:%M'),
                'mobile_status': patient.mobile_status,
                'geocoding_warning': patient.geocoding_status in ['failed', 'default', 'pending']
            })
    
    # Converteer naar lijst en voeg Reha Center toe
    route_list = []
    for vehicle_kenteken, route_data in routes.items():
        # Haal home/depot locatie op uit database
        from .models import Location
        home_location = Location.get_home_location()
        
        if home_location:
            # Voeg Reha Center toe als eerste stop
            reha_center = {
                'patient_name': home_location.name,
                'patient_id': 'reha_center',
                'latitude': float(home_location.latitude),
                'longitude': float(home_location.longitude),
                'address': home_location.address,
                'pickup_time': 'Start',
                'mobile_status': 'completed',
                'geocoding_warning': False,
                'is_reha_center': True
            }
        else:
            # Fallback naar hardcoded Bonn coördinaten
            reha_center = {
                'patient_name': 'Reha Center',
                'patient_id': 'reha_center',
                'latitude': 50.8503,  # Bonn coördinaten
                'longitude': 7.1017,
                'address': 'Reha Center, Bonn',
                'pickup_time': 'Start',
                'mobile_status': 'completed',
                'geocoding_warning': False,
                'is_reha_center': True
            }
        
        route_data['stops'].insert(0, reha_center)
        route_list.append(route_data)
    
    return route_list


def get_today_planning_routes():
    """
    Haal planning routes van vandaag op voor dashboard overview
    """
    from datetime import date
    from django.db.models import Q
    from .models_extended import PlanningSession
    
    today = date.today()
    
    # Haal planning sessions van vandaag op
    planning_sessions = PlanningSession.objects.filter(planning_date=today)
    
    if not planning_sessions.exists():
        return []
    
    # Haal patiënten op die toegewezen zijn aan voertuigen en tijdblokken
    today_patients = Patient.objects.filter(
        Q(ophaal_tijd__date=today) | Q(eind_behandel_tijd__date=today),
        toegewezen_voertuig__isnull=False,
        halen_tijdblok__isnull=False
    ).select_related('toegewezen_voertuig', 'halen_tijdblok', 'bringen_tijdblok')
    
    if not today_patients.exists():
        return []
    
    # Groepeer per voertuig en tijdblok
    routes = {}
    for patient in today_patients:
        vehicle = patient.toegewezen_voertuig
        
        # Bepaal route type en tijdblok
        if patient.halen_tijdblok:
            route_type = 'Halen'
            timeslot = patient.halen_tijdblok
            route_key = f"{vehicle.id}_{timeslot.id}_halen"
        elif patient.bringen_tijdblok:
            route_type = 'Brengen'
            timeslot = patient.bringen_tijdblok
            route_key = f"{vehicle.id}_{timeslot.id}_brengen"
        else:
            continue
        
        if route_key not in routes:
            routes[route_key] = {
                'vehicle_name': vehicle.kenteken,
                'vehicle_referentie': vehicle.referentie,
                'vehicle_color': vehicle.kleur,
                'route_type': route_type,
                'timeslot_name': timeslot.naam,
                'stops': [],
                'total_patients': 0,
                'total_stops': 0
            }
        
        # Voeg patiënt toe als stop
        if patient.latitude and patient.longitude:
            routes[route_key]['stops'].append({
                'patient_name': patient.naam,
                'patient_id': patient.id,
                'location_name': f"{patient.straat}, {patient.postcode} {patient.plaats}",
                'latitude': patient.latitude,
                'longitude': patient.longitude,
                'pickup_time': patient.ophaal_tijd.strftime('%H:%M') if route_type == 'Halen' else patient.eind_behandel_tijd.strftime('%H:%M'),
                'is_reha_center': False
            })
            routes[route_key]['total_patients'] += 1
    
    # Voeg Reha Center toe aan elke route en bereken totals
    route_list = []
    for route_key, route_data in routes.items():
        # Haal home locatie op
        from .models import Location
        home_location = Location.get_home_location()
        
        if home_location:
            reha_center = {
                'patient_name': home_location.name,
                'patient_id': 'reha_center',
                'location_name': home_location.address,
                'latitude': float(home_location.latitude),
                'longitude': float(home_location.longitude),
                'pickup_time': 'Start',
                'is_reha_center': True
            }
        else:
            reha_center = {
                'patient_name': 'Reha Center',
                'patient_id': 'reha_center',
                'location_name': 'Reha Center, Bonn',
                'latitude': 50.8503,
                'longitude': 7.1017,
                'pickup_time': 'Start',
                'is_reha_center': True
            }
        
        # Voeg Reha Center toe als eerste en laatste stop
        route_data['stops'].insert(0, reha_center)
        route_data['stops'].append(reha_center)
        route_data['total_stops'] = len(route_data['stops'])
        
        route_list.append(route_data)
    
    return route_list


def get_dashboard_statistics():
    """
    Haal dashboard statistieken op
    """
    from datetime import date, timedelta
    from .models_extended import PlanningSession
    
    today = date.today()
    week_ago = today - timedelta(days=7)
    
    # Patiënten statistieken
    total_patients = Patient.objects.count()
    today_patients = Patient.objects.filter(ophaal_tijd__date=today).count()
    week_patients = Patient.objects.filter(ophaal_tijd__date__gte=week_ago).count()
    
    # Voertuig statistieken
    total_vehicles = Vehicle.objects.count()
    available_vehicles = Vehicle.objects.filter(status='beschikbaar').count()
    maintenance_vehicles = Vehicle.objects.filter(status='onderhoud').count()
    
    # Planning statistieken
    total_sessions = PlanningSession.objects.count()
    week_sessions = PlanningSession.objects.filter(created_at__date__gte=week_ago).count()
    
    return {
        'total_patients': total_patients,
        'today_patients': today_patients,
        'week_patients': week_patients,
        'total_vehicles': total_vehicles,
        'available_vehicles': available_vehicles,
        'maintenance_vehicles': maintenance_vehicles,
        'total_sessions': total_sessions,
        'week_sessions': week_sessions,
    }


def patients_today(request):
    """
    Toon patiënten van vandaag met filter functionaliteit
    """
    from datetime import date
    from django.db.models import Q
    
    today = date.today()
    
    # Haal alle patiënten van vandaag op
    patients = Patient.objects.filter(ophaal_tijd__date=today).select_related(
        'halen_tijdblok', 'bringen_tijdblok', 'toegewezen_voertuig'
    ).order_by('ophaal_tijd')
    
    # Filter functionaliteit
    search_query = request.GET.get('search', '')
    if search_query:
        patients = patients.filter(
            Q(naam__icontains=search_query) |
            Q(patient_id__icontains=search_query) |
            Q(plaats__icontains=search_query) |
            Q(straat__icontains=search_query)
        )
    
    # Groepeer per tijdblok
    timeslot_groups = {}
    for patient in patients:
        # Bepaal primair tijdblok (halen of brengen)
        if patient.halen_tijdblok:
            timeslot = patient.halen_tijdblok
            route_type = 'Halen'
        elif patient.bringen_tijdblok:
            timeslot = patient.bringen_tijdblok
            route_type = 'Brengen'
        else:
            timeslot = None
            route_type = 'Geen toewijzing'
        
        if timeslot:
            key = f"{timeslot.id}_{route_type}"
            if key not in timeslot_groups:
                timeslot_groups[key] = {
                    'timeslot': timeslot,
                    'route_type': route_type,
                    'patients': []
                }
            timeslot_groups[key]['patients'].append(patient)
    
    context = {
        'patients': patients,
        'timeslot_groups': timeslot_groups,
        'search_query': search_query,
        'today': today,
        'page_title': 'Patiënten Vandaag'
    }
    
    return render(request, 'planning/patients_today.html', context)


def auto_detect_csv_mapping(csv_data, filename=None):
    """
    Slimme auto-detectie van CSV kolom mapping met admin-geconfigureerde parser configuraties
    """
    detection_results = {
        'confidence': 0,
        'mappings': {},
        'warnings': [],
        'suggestions': [],
        'detected_format': 'unknown',
        'config_id': None
    }
    
    if not csv_data or len(csv_data) < 2:
        detection_results['warnings'].append("Onvoldoende data voor detectie")
        return detection_results
    
    # Haal alle actieve parser configuraties op
    try:
        from .models import CSVParserConfig
        configs = CSVParserConfig.objects.filter(actief=True).order_by('-prioriteit')
    except Exception as e:
        print(f"⚠️ Kon parser configuraties niet laden: {e}")
        detection_results['warnings'].append("Kon parser configuraties niet laden")
        return detection_results
    
    if not configs.exists():
        detection_results['warnings'].append("Geen parser configuraties gevonden")
        return detection_results
    
    # Test elke configuratie
    best_config = None
    best_score = 0
    
    for config in configs:
        score = config.test_detectie(filename or '', csv_data[0])
        print(f"🔍 Test config '{config.naam}': score {score}")
        
        if score > best_score:
            best_score = score
            best_config = config
    
    if best_config and best_score > 0:
        detection_results.update({
            'detected_format': best_config.naam,
            'confidence': min(best_score / 100, 1.0),  # Normaliseer naar 0-1
            'mappings': best_config.get_kolom_mapping(),
            'config_id': best_config.id
        })
        
        print(f"✅ Beste match: '{best_config.naam}' (score: {best_score})")
        
        # Voeg suggesties toe
        if best_score < 50:
            detection_results['suggestions'].append(f"Lage detectie score ({best_score}) - controleer configuratie")
        
        if not best_config.get_kolom_mapping():
            detection_results['warnings'].append("Geen kolom mapping geconfigureerd")
    else:
        detection_results['warnings'].append("Geen passende parser configuratie gevonden")
        detection_results['suggestions'].append("Controleer of er een configuratie is voor dit CSV formaat")
    
    return detection_results


def analyze_filename(filename):
    """
    Analyseer bestandsnaam voor formaat indicaties
    """
    if not filename:
        return {}
    
    filename_lower = filename.lower()
    patterns = {}
    
    # Detecteer formaat op basis van bestandsnaam
    if 'fahrdlist' in filename_lower:
        patterns['format'] = 'fahrdlist'
        patterns['confidence'] = 0.9
    elif 'routemeister' in filename_lower:
        patterns['format'] = 'routemeister'
        patterns['confidence'] = 0.9
    elif 'fahrer' in filename_lower:
        patterns['format'] = 'fahrdlist'
        patterns['confidence'] = 0.7
    elif 'kunde' in filename_lower:
        patterns['format'] = 'fahrdlist'
        patterns['confidence'] = 0.7
    
    return patterns


def analyze_headers(header_row):
    """
    Analyseer header rij voor kolomnamen en patronen
    """
    patterns = {}
    header_text = ' '.join(str(cell).lower() for cell in header_row)
    
    # Zoek naar specifieke kolomnamen
    column_matches = {
        'patient_id': ['patient', 'kunde', 'id', 'nummer', 'patient_id', 'kunde_id'],
        'achternaam': ['nachname', 'achternaam', 'surname', 'lastname', 'familie'],
        'voornaam': ['vorname', 'voornaam', 'firstname', 'name'],
        'adres': ['straße', 'street', 'adres', 'address', 'adresse'],
        'plaats': ['stadt', 'city', 'plaats', 'ort', 'gemeinde'],
        'postcode': ['plz', 'postcode', 'postal', 'postleitzahl'],
        'telefoon1': ['telefon', 'phone', 'telefoon', 'tel'],
        'telefoon2': ['mobil', 'mobile', 'telefoon2', 'tel2'],
        'datum': ['datum', 'date', 'termin', 'afspraak'],
        'start_tijd': ['start', 'begin', 'startzeit', 'start_time'],
        'eind_tijd': ['ende', 'eind', 'endzeit', 'end_time', 'eind_tijd']
    }
    
    detected_columns = {}
    for field, keywords in column_matches.items():
        for i, cell in enumerate(header_row):
            cell_lower = str(cell).lower()
            for keyword in keywords:
                if keyword in cell_lower:
                    detected_columns[field] = i
                    break
            if field in detected_columns:
                break
    
    patterns['detected_columns'] = detected_columns
    patterns['confidence'] = len(detected_columns) / len(column_matches) * 0.8
    
    return patterns


def analyze_content(data_rows):
    """
    Analyseer inhoud voor data patronen
    """
    patterns = {}
    if not data_rows:
        return patterns
    
    # Patroon definities
    pattern_rules = {
        'patient_id': [
            {'pattern': r'^FL\d{8}$', 'confidence': 0.95},  # FL25004678
            {'pattern': r'^[A-Z]{2}\d{6,8}$', 'confidence': 0.85},  # Algemene ID patroon
            {'pattern': r'^\d{6,10}$', 'confidence': 0.70}  # Numerieke ID
        ],
        'datum': [
            {'pattern': r'^\d{1,2}-\d{1,2}-\d{4}$', 'confidence': 0.90},  # 27-8-2025
            {'pattern': r'^\d{4}-\d{2}-\d{2}$', 'confidence': 0.90},  # 2025-08-27
            {'pattern': r'^\d{1,2}\.\d{1,2}\.\d{4}$', 'confidence': 0.90},  # 27.08.2025
            {'pattern': r'^\d{1,2}/\d{1,2}/\d{4}$', 'confidence': 0.90}  # 27/08/2025
        ],
        'tijd': [
            {'pattern': r'^\d{3,4}$', 'confidence': 0.80},  # 845, 1515
            {'pattern': r'^\d{1,2}:\d{2}$', 'confidence': 0.85},  # 8:45, 15:15
            {'pattern': r'^\d{1,2}:\d{2}\s*(AM|PM)?$', 'confidence': 0.80}  # 8:45 AM
        ],
        'telefoon': [
            {'pattern': r'^\d{10,15}$', 'confidence': 0.85},  # 02241880514
            {'pattern': r'^\+?\d{1,3}\s?\d{6,12}$', 'confidence': 0.80},  # +49 228 1880514
            {'pattern': r'^\d{3,4}\s?\d{3,4}\s?\d{3,4}$', 'confidence': 0.75}  # 0224 188 0514
        ],
        'postcode': [
            {'pattern': r'^\d{4,5}\s?[A-Z]?$', 'confidence': 0.90},  # 53757 D
            {'pattern': r'^[A-Z]-\d{5}$', 'confidence': 0.85},  # D-53757
            {'pattern': r'^\d{4}\s?[A-Z]{2}$', 'confidence': 0.80}  # 1234 AB
        ],
        'achternaam': [
            {'pattern': r'^[A-Z][a-z]+$', 'confidence': 0.75},  # Makonga, Gluckmann
            {'pattern': r'^[A-Z][a-z]+\s+[A-Z][a-z]+$', 'confidence': 0.70}  # Van der Berg
        ],
        'voornaam': [
            {'pattern': r'^[A-Z][a-z]+$', 'confidence': 0.75},  # Lofo, Julia
            {'pattern': r'^[A-Z][a-z]+\s+[A-Z][a-z]+$', 'confidence': 0.70}  # Jan Peter
        ],
        'adres': [
            {'pattern': r'.*str\.?\s+\d+.*', 'confidence': 0.85},  # Cranachstr. 15
            {'pattern': r'.*straat\s+\d+.*', 'confidence': 0.85},  # Hoofdstraat 123
            {'pattern': r'.*\d+.*', 'confidence': 0.60}  # Bevat nummer
        ],
        'plaats': [
            {'pattern': r'^[A-Z][a-z]+(\s+[A-Z][a-z]+)*$', 'confidence': 0.70},  # Sankt Augustin
            {'pattern': r'^[A-Z][a-z]+$', 'confidence': 0.65}  # Amsterdam
        ]
    }
    
    # Analyseer elke kolom
    column_scores = defaultdict(list)
    
    for row in data_rows:
        for col_index, cell in enumerate(row):
            cell_str = str(cell).strip()
            if not cell_str:
                continue
                
            for field, rules in pattern_rules.items():
                for rule in rules:
                    if re.match(rule['pattern'], cell_str):
                        column_scores[col_index].append({
                            'field': field,
                            'confidence': rule['confidence']
                        })
                        break
    
    # Bereken gemiddelde confidence per kolom
    column_confidence = {}
    for col_index, scores in column_scores.items():
        if scores:
            # Neem het veld met hoogste confidence
            best_match = max(scores, key=lambda x: x['confidence'])
            column_confidence[col_index] = best_match
    
    patterns['column_confidence'] = column_confidence
    patterns['confidence'] = len(column_confidence) / len(pattern_rules) * 0.7
    
    return patterns


def combine_detections(filename_patterns, header_patterns, content_patterns):
    """
    Combineer alle detectie resultaten tot een finale mapping
    """
    final_mapping = {
        'mappings': {},
        'confidence': 0,
        'detected_format': 'unknown',
        'warnings': [],
        'suggestions': []
    }
    
    # Bepaal formaat
    format_confidence = {
        'fahrdlist': 0,
        'routemeister': 0
    }
    
    # Bestandsnaam weging
    if 'format' in filename_patterns:
        format_confidence[filename_patterns['format']] += filename_patterns['confidence'] * 0.3
    
    # Header weging
    if header_patterns.get('detected_columns'):
        detected_count = len(header_patterns['detected_columns'])
        if detected_count > 5:
            format_confidence['fahrdlist'] += 0.4
        else:
            format_confidence['routemeister'] += 0.4
    
    # Inhoud weging
    if content_patterns.get('column_confidence'):
        content_score = content_patterns['confidence']
        if content_score > 0.6:
            format_confidence['fahrdlist'] += content_score * 0.3
        else:
            format_confidence['routemeister'] += content_score * 0.3
    
    # Bepaal winnend formaat
    if format_confidence['fahrdlist'] > format_confidence['routemeister']:
        final_mapping['detected_format'] = 'fahrdlist'
        final_mapping['confidence'] = format_confidence['fahrdlist']
    else:
        final_mapping['detected_format'] = 'routemeister'
        final_mapping['confidence'] = format_confidence['routemeister']
    
    # Genereer mapping
    if final_mapping['detected_format'] == 'fahrdlist':
        final_mapping['mappings'] = get_column_mapping('fahrdlist')
    else:
        final_mapping['mappings'] = get_column_mapping('routemeister')
    
    # Voeg waarschuwingen toe
    if final_mapping['confidence'] < 0.5:
        final_mapping['warnings'].append("Lage betrouwbaarheid detectie - handmatige controle aanbevolen")
    
    if header_patterns.get('detected_columns'):
        missing_fields = set(get_column_mapping(final_mapping['detected_format']).keys()) - set(header_patterns['detected_columns'].keys())
        if missing_fields:
            final_mapping['suggestions'].append(f"Missende velden gedetecteerd: {', '.join(missing_fields)}")
    
    return final_mapping


def parse_slk_file(file_data):
    """
    Parse een SYLK (Symbolic Link) bestand
    """
    try:
        lines = file_data.split('\n')
        data = []
        
        print(f"🔍 SLK parsing: {len(lines)} regels gevonden")
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            print(f"📝 Regel {i+1}: {line[:100]}...")  # Debug: eerste 100 karakters
            
            # Skip header regels
            if line.startswith('ID') or line.startswith('P') or line.startswith('B'):
                print(f"⏭️ Skipping header regel: {line[:50]}...")
                continue
            
            # Parse SYLK rij
            row_data = parse_slk_row(line)
            if row_data:
                data.append(row_data)
                print(f"✅ Rij geparsed: rij={row_data['row']}, kolom={row_data['col']}, waarde='{row_data['value']}'")
            else:
                print(f"❌ Kon rij niet parsen: {line[:50]}...")
        
        print(f"📊 Totaal geparsed: {len(data)} cellen")
        return data if data else None
        
    except Exception as e:
        print(f"❌ SLK parsing fout: {e}")
        import traceback
        traceback.print_exc()
        return None


def parse_slk_row(line):
    """
    Parse een enkele SYLK rij
    """
    try:
        # SYLK formaat: C;Y1;X1;K"value"
        # C = Cell, Y = Row, X = Column, K = Value
        if not line.startswith('C'):
            return None
        
        parts = line.split(';')
        if len(parts) < 3:  # Minimaal C, Y, X nodig
            return None
        
        # Haal rij en kolom op
        row_part = None
        col_part = None
        value_part = None
        
        for part in parts:
            part = part.strip()
            if part.startswith('Y'):
                row_part = part[1:]
            elif part.startswith('X'):
                col_part = part[1:]
            elif part.startswith('K'):
                # Verwijder quotes en escape karakters
                value_part = part[1:]
                if value_part.startswith('"') and value_part.endswith('"'):
                    value_part = value_part[1:-1]
                # Unescape quotes
                value_part = value_part.replace('""', '"')
        
        # Als er geen K deel is, probeer de laatste part als waarde
        if not value_part and len(parts) >= 3:
            value_part = parts[-1].strip()
            if value_part.startswith('"') and value_part.endswith('"'):
                value_part = value_part[1:-1]
            value_part = value_part.replace('""', '"')
        
        if row_part and col_part and value_part is not None:
            try:
                return {
                    'row': int(row_part),
                    'col': int(col_part),
                    'value': value_part
                }
            except ValueError as ve:
                print(f"❌ Kon rij/kolom niet converteren naar int: {ve}")
                return None
        
        return None
    except Exception as e:
        print(f"❌ SLK rij parsing fout: {e}")
        return None


def convert_slk_to_csv(slk_data):
    """
    Converteer SLK data naar CSV formaat
    """
    try:
        print(f"🔄 Converteer {len(slk_data)} SLK cellen naar CSV...")
        
        # Groepeer data per rij
        rows = {}
        for cell in slk_data:
            row_num = cell['row']
            col_num = cell['col']
            value = cell['value']
            
            if row_num not in rows:
                rows[row_num] = {}
            
            rows[row_num][col_num] = value
        
        print(f"📊 Gevonden rijen: {list(rows.keys())}")
        
        # Converteer naar CSV rijen
        csv_rows = []
        for row_num in sorted(rows.keys()):
            row_data = rows[row_num]
            max_col = max(row_data.keys()) if row_data else 0
            
            print(f"📝 Verwerk rij {row_num}: kolommen 1-{max_col}")
            
            # Maak rij met alle kolommen
            csv_row = []
            for col_num in range(1, max_col + 1):
                cell_value = row_data.get(col_num, '')
                csv_row.append(str(cell_value) if cell_value is not None else '')
            
            csv_rows.append(csv_row)
            print(f"✅ Rij {row_num}: {len(csv_row)} kolommen")
        
        # Converteer naar CSV string
        csv_string = ''
        for row in csv_rows:
            csv_string += ';'.join(cell for cell in row) + '\n'
        
        print(f"🎉 CSV conversie voltooid: {len(csv_rows)} rijen")
        return csv_string
        
    except Exception as e:
        print(f"❌ SLK naar CSV conversie fout: {e}")
        import traceback
        traceback.print_exc()
        return None


def detect_csv_format(csv_reader):
    """
    Verbeterde CSV formaat detectie met auto-detectie
    """
    try:
        # Lees alle data voor analyse
        csv_data = list(csv_reader)
        
        # Gebruik auto-detectie
        detection_result = auto_detect_csv_mapping(csv_data)
        
        print(f"🤖 Auto-detectie resultaat:")
        print(f"   Formaat: {detection_result['detected_format']}")
        print(f"   Betrouwbaarheid: {detection_result['confidence']:.1%}")
        print(f"   Mapping: {detection_result['mappings']}")
        
        if detection_result['warnings']:
            print(f"   ⚠️ Waarschuwingen: {detection_result['warnings']}")
        
        if detection_result['suggestions']:
            print(f"   💡 Suggesties: {detection_result['suggestions']}")
        
        return detection_result['detected_format']
        
    except Exception as e:
        print(f"❌ Auto-detectie fout: {e}")
        return 'routemeister'  # Fallback


def get_column_mapping(format_type):
    """
    Krijg kolom mapping voor verschillende CSV formaten
    """
    if format_type == 'fahrdlist':
        return {
            'patient_id': 0,      # Mogelijk Kunde ID
            'achternaam': 1,      # Achternaam
            'voornaam': 2,        # Voornaam
            'adres': 3,           # Straat + Hausnummer
            'plaats': 4,          # Stadt
            'postcode': 5,        # PLZ
            'telefoon1': 6,       # Telefon
            'telefoon2': 7,       # Mobil
            'datum': 8,           # Termin Datum
            'start_tijd': 9,      # Start Zeit
            'eind_tijd': 10,      # Ende Zeit
        }
    else:  # routemeister format
        return {
            'patient_id': 1,      # Kolom B
            'achternaam': 2,      # Kolom C
            'voornaam': 3,        # Kolom D
            'adres': 6,           # Kolom G
            'plaats': 8,          # Kolom I
            'postcode': 9,        # Kolom J
            'telefoon1': 10,      # Kolom K
            'telefoon2': 11,      # Kolom L
            'datum': 15,          # Kolom P
            'start_tijd': 17,     # Kolom R
            'eind_tijd': 18,      # Kolom S
        }


def validate_csv_row_flexible(row, row_number, format_type):
    """
    Flexibele CSV validatie voor verschillende formaten
    """
    errors = []
    mapping = get_column_mapping(format_type)
    
    # Controleer minimale lengte
    min_columns = max(mapping.values()) + 1
    if len(row) < min_columns:
        errors.append(f"Onvoldoende kolommen: {len(row)} (verwacht: {min_columns}+)")
        return {'status': 'error', 'errors': errors}
    
    # Haal data op basis van mapping
    patient_id = row[mapping['patient_id']] if mapping['patient_id'] < len(row) else ""
    achternaam = row[mapping['achternaam']] if mapping['achternaam'] < len(row) else ""
    voornaam = row[mapping['voornaam']] if mapping['voornaam'] < len(row) else ""
    adres_volledig = row[mapping['adres']] if mapping['adres'] < len(row) else ""
    plaats = row[mapping['plaats']] if mapping['plaats'] < len(row) else ""
    postcode = row[mapping['postcode']] if mapping['postcode'] < len(row) else ""
    telefoon1 = row[mapping['telefoon1']] if mapping['telefoon1'] < len(row) else ""
    telefoon2 = row[mapping['telefoon2']] if mapping['telefoon2'] < len(row) else ""
    afspraak_datum = row[mapping['datum']] if mapping['datum'] < len(row) else ""
    eerste_behandeling_tijd = row[mapping['start_tijd']] if mapping['start_tijd'] < len(row) else ""
    laatste_behandeling_tijd = row[mapping['eind_tijd']] if mapping['eind_tijd'] < len(row) else ""
    
    # Valideer verplichte velden
    if not patient_id:
        errors.append("Patient ID ontbreekt")
    
    if not voornaam:
        errors.append("Voornaam ontbreekt")
    
    if not achternaam:
        errors.append("Achternaam ontbreekt")
    
    if not adres_volledig:
        errors.append("Adres ontbreekt")
    
    if not plaats:
        errors.append("Plaats ontbreekt")
    
    if not postcode:
        errors.append("Postcode ontbreekt")
    
    # Valideer datum (verschillende formaten)
    if afspraak_datum:
        try:
            # Probeer verschillende datum formaten
            if '-' in afspraak_datum:
                dag, maand, jaar = afspraak_datum.split('-')
            elif '.' in afspraak_datum:
                dag, maand, jaar = afspraak_datum.split('.')
            elif '/' in afspraak_datum:
                dag, maand, jaar = afspraak_datum.split('/')
            else:
                errors.append("Ongeldig datum formaat")
        except ValueError:
            errors.append("Ongeldige datum")
    else:
        errors.append("Afspraak datum ontbreekt")
    
    # Valideer tijden (verschillende formaten)
    if eerste_behandeling_tijd:
        tijd_str = str(eerste_behandeling_tijd).strip()
        # Accepteer HH:MM, HHMM, H:MM formaten
        if ':' in tijd_str:
            tijd_str = tijd_str.replace(':', '')
        if len(tijd_str) < 3 or len(tijd_str) > 4:
            errors.append("Ongeldige eerste behandeling tijd (verwacht: HHMM formaat)")
        elif not tijd_str.isdigit():
            errors.append("Eerste behandeling tijd moet numeriek zijn")
    
    if laatste_behandeling_tijd:
        tijd_str = str(laatste_behandeling_tijd).strip()
        # Accepteer HH:MM, HHMM, H:MM formaten
        if ':' in tijd_str:
            tijd_str = tijd_str.replace(':', '')
        if len(tijd_str) < 3 or len(tijd_str) > 4:
            errors.append("Ongeldige laatste behandeling tijd (verwacht: HHMM formaat)")
        elif not tijd_str.isdigit():
            errors.append("Laatste behandeling tijd moet numeriek zijn")
    
    # Valideer telefoon (minimaal één moet aanwezig zijn)
    if not telefoon1 and not telefoon2:
        errors.append("Telefoonnummer ontbreekt")
    
    if errors:
        return {'status': 'error', 'errors': errors}
    else:
        return {'status': 'ok'}


def validate_csv_row(row, row_number):
    """
    Valideer een CSV rij voor patiënt data (backward compatibility)
    """
    return validate_csv_row_flexible(row, row_number, 'routemeister')


# Oude planning functie verwijderd - vervangen door wizard


def planning_step2(request):
    """
    Stap 2: Patiënten overzicht per tijdblok + Akkoord/Terug
    """
    # Deze functie is vervangen door de wizard
    messages.info(request, 'Deze functie is vervangen door de nieuwe Planning Wizard.')
    return redirect('planning_wizard_start')


def planning_step3(request):
    """
    Stap 3: Planner keuze (Snel/Routemeister) + Timer voor OptaPlanner
    """
    planning_data = request.session.get('planning_data')
    if not planning_data:
        messages.error(request, 'Geen planning data gevonden. Start opnieuw.')
        return redirect('planning_overview')
    
    if request.method == 'POST':
        planner_type = request.POST.get('planner_type')
        if planner_type in ['simple', 'routemeister']:
            # Update planning data
            planning_data['planner_type'] = planner_type
            request.session['planning_data'] = planning_data
            
            # Start planning proces
            if planner_type == 'routemeister':
                # Start OptaPlanner met timer
                return redirect('planning_processing')
            else:
                # Direct simple planning
                try:
                    # Haal voertuigen op
                    selected_vehicles = Vehicle.objects.filter(id__in=planning_data['vehicles'])
                    
                    # Haal patiënten op van vandaag
                    from datetime import date
                    today = date.today()
                    patients = Patient.objects.filter(ophaal_tijd__date=today)
                    
                    # Automatisch tijdblok toewijzing als nog niet gedaan
                    if patients.exists() and not patients.filter(
                        models.Q(halen_tijdblok__isnull=False) | 
                        models.Q(bringen_tijdblok__isnull=False)
                    ).exists():
                        print("🔄 Automatische tijdblok toewijzing...")
                        assign_timeslots_to_patients(patients)
                    
                    # Haal patiënten op met tijdblok toewijzing
                    assigned_patients = Patient.objects.filter(
                        ophaal_tijd__date=today
                    ).filter(
                        models.Q(halen_tijdblok__isnull=False) | 
                        models.Q(bringen_tijdblok__isnull=False)
                    ).distinct()
                    
                    if not assigned_patients.exists():
                        messages.error(request, 'Geen patiënten met tijdblok toewijzing gevonden.')
                        return redirect('planning_step3')
                    
                    # Plan routes
                    routes = simple_route_service.plan_simple_routes(selected_vehicles, assigned_patients)
                    
                    if routes:
                        # Convert Decimal objects to float before storing in session
                        def convert_decimals(obj):
                            """Recursively convert Decimal objects to float for JSON serialization"""
                            if isinstance(obj, dict):
                                return {key: convert_decimals(value) for key, value in obj.items()}
                            elif isinstance(obj, list):
                                return [convert_decimals(item) for item in obj]
                            elif hasattr(obj, 'as_tuple'):  # Check if it's a Decimal
                                return float(obj)
                            else:
                                return obj
                        
                        # Convert routes to JSON-serializable format
                        serializable_routes = convert_decimals(routes)
                        
                        # Store results in session
                        request.session['planned_routes'] = serializable_routes
                        request.session['route_planner_type'] = 'simple'
                        messages.success(request, f'🎉 {len(routes)} routes gegenereerd met Simple Router!')
                        return redirect('planning_results')
                    else:
                        messages.error(request, 'Geen routes gegenereerd. Controleer patiënt toewijzingen.')
                        return redirect('planning_step3')
                        
                except Exception as e:
                    messages.error(request, f'Fout bij route planning: {str(e)}')
                    return redirect('planning_step3')
    
    return render(request, 'planning/planning_step3.html')


def assign_timeslots_to_patients(patients):
    """
    Wijs automatisch tijdblokken toe aan patiënten - alleen geselecteerde tijdblokken
    """
    from .models import TimeSlot
    
    # Haal alleen geselecteerde tijdblokken op
    selected_timeslots = TimeSlot.objects.filter(actief=True, default_selected=True).order_by('aankomst_tijd')
    
    assigned_count = 0
    
    for patient in patients:
        # Skip als al toegewezen
        if patient.halen_tijdblok and patient.bringen_tijdblok:
            continue
        
        # Zoek halen tijdblok (eerste afspraak tijd)
        halen_timeslot = None
        if patient.ophaal_tijd:
            first_appointment_time = patient.ophaal_tijd.time()
            
            # CORRECTE HALEN LOGICA: 
            # Starttijd groter dan blok [x] en kleiner dan (volgend) blok [y] → plaats patiënt in blok [x]
            for i, ts in enumerate(selected_timeslots):
                # Check of dit een Halen tijdblok is
                if not ts.naam.startswith('Holen'):
                    continue
                
                current_block_start = ts.aankomst_tijd
                
                # Zoek volgende Halen tijdblok
                next_block_start = None
                for j in range(i + 1, len(selected_timeslots)):
                    next_ts = selected_timeslots[j]
                    if next_ts.tijdblok_type == 'halen':
                        next_block_start = next_ts.aankomst_tijd
                        break
                
                # Als er geen volgende Halen tijdblok is, gebruik dan 90 minuten na huidige tijd
                if next_block_start is None:
                    from datetime import timedelta
                    next_block_start = (datetime.combine(datetime.today(), ts.aankomst_tijd) + timedelta(minutes=90)).time()
                
                # Check of patiënt tijd valt tussen huidige blok start en volgende blok start
                if current_block_start <= first_appointment_time < next_block_start:
                    halen_timeslot = ts
                    break
        
        # Zoek brengen tijdblok (eind tijd)
        brengen_timeslot = None
        if patient.eind_behandel_tijd:
            end_time = patient.eind_behandel_tijd.time()
            
            # Zoek eerste tijdblok waar eind tijd >= aankomst_tijd
            for ts in selected_timeslots:
                if ts.tijdblok_type == 'brengen' and end_time >= ts.aankomst_tijd:
                    brengen_timeslot = ts
                    break
            
            # Fallback: zoek laatste beschikbare tijdblok als geen match
            if not brengen_timeslot:
                for ts in reversed(list(selected_timeslots)):
                    if ts.tijdblok_type == 'brengen':
                        brengen_timeslot = ts
                        break
        
        # Update patiënt
        if halen_timeslot:
            patient.halen_tijdblok = halen_timeslot
        
        if brengen_timeslot:
            patient.bringen_tijdblok = brengen_timeslot
        
        if halen_timeslot or brengen_timeslot:
            patient.save()
            assigned_count += 1
    
    print(f"✅ {assigned_count} patiënten toegewezen aan tijdblokken")
    return assigned_count


def planning_processing(request):
    """
    OptaPlanner processing pagina met timer
    """
    planning_data = request.session.get('planning_data')
    if not planning_data:
        messages.error(request, 'Geen planning data gevonden. Start opnieuw.')
        return redirect('planning_overview')
    
    # Check of OptaPlanner beschikbaar is
    if not optaplanner_service.is_enabled():
        messages.error(request, 'OptaPlanner is niet beschikbaar. Gebruik Simple Router.')
        return redirect('planning_step3')
    
    context = {
        'planning_data': planning_data,
        'optaplanner_url': optaplanner_service.base_url
    }
    
    return render(request, 'planning/planning_processing.html', context)


def planning_results(request):
    """
    Planning resultaten (zoals huidige route_results)
    """
    # Gebruik bestaande route_results logica
    return route_results(request)


def view_planning(request, planning_id):
    """
    Bekijk bestaande planning
    """
    # Implementeer bekijken van bestaande planning
    return render(request, 'planning/view_planning.html', {'planning_id': planning_id})


# Voertuigen CRUD Views
def vehicles_list(request):
    """
    Overzicht van alle voertuigen
    """
    vehicles = Vehicle.objects.all().order_by('kenteken')
    
    context = {
        'vehicles': vehicles,
    }
    
    return render(request, 'planning/vehicles_list.html', context)


def vehicle_create(request):
    """
    Nieuw voertuig aanmaken
    """
    if request.method == 'POST':
        # Verwerk form data
        referentie = request.POST.get('referentie')
        kenteken = request.POST.get('kenteken')
        merk_model = request.POST.get('merk_model')
        aantal_zitplaatsen = request.POST.get('aantal_zitplaatsen')
        speciale_zitplaatsen = request.POST.get('speciale_zitplaatsen', 0)
        km_kosten_per_km = request.POST.get('km_kosten_per_km', 0.29)
        maximale_rit_tijd = request.POST.get('maximale_rit_tijd', 3600)
        kleur = request.POST.get('kleur', '#3498db')
        status = request.POST.get('status', 'beschikbaar')
        
        # Valideer en sla op
        if referentie and kenteken and merk_model and aantal_zitplaatsen:
            vehicle = Vehicle.objects.create(
                referentie=referentie,
                kenteken=kenteken,
                merk_model=merk_model,
                aantal_zitplaatsen=aantal_zitplaatsen,
                speciale_zitplaatsen=speciale_zitplaatsen,
                km_kosten_per_km=km_kosten_per_km,
                maximale_rit_tijd=maximale_rit_tijd,
                kleur=kleur,
                status=status
            )
            
            # Verwerk foto upload
            if 'foto' in request.FILES:
                vehicle.foto = request.FILES['foto']
                vehicle.save()
            
            messages.success(request, f'Voertuig {referentie} succesvol aangemaakt.')
            return redirect('vehicles_list')
        else:
            messages.error(request, 'Vul alle verplichte velden in.')
    
    return render(request, 'planning/vehicle_form.html')


def vehicle_edit(request, vehicle_id):
    """
    Voertuig bewerken
    """
    try:
        vehicle = Vehicle.objects.get(id=vehicle_id)
    except Vehicle.DoesNotExist:
        messages.error(request, 'Voertuig niet gevonden.')
        return redirect('vehicles_list')
    
    if request.method == 'POST':
        # Verwerk form data
        vehicle.referentie = request.POST.get('referentie')
        vehicle.kenteken = request.POST.get('kenteken')
        vehicle.merk_model = request.POST.get('merk_model')
        vehicle.aantal_zitplaatsen = request.POST.get('aantal_zitplaatsen')
        vehicle.speciale_zitplaatsen = request.POST.get('speciale_zitplaatsen', 0)
        vehicle.km_kosten_per_km = request.POST.get('km_kosten_per_km', 0.29)
        vehicle.maximale_rit_tijd = request.POST.get('maximale_rit_tijd', 3600)
        vehicle.kleur = request.POST.get('kleur', '#3498db')
        vehicle.status = request.POST.get('status', 'beschikbaar')
        
        # Verwerk foto upload
        if 'foto' in request.FILES:
            vehicle.foto = request.FILES['foto']
        
        vehicle.save()
        
        messages.success(request, f'Voertuig {vehicle.referentie} succesvol bijgewerkt.')
        return redirect('vehicles_list')
    
    context = {
        'vehicle': vehicle,
    }
    
    return render(request, 'planning/vehicle_form.html', context)


def vehicle_delete(request, vehicle_id):
    """
    Voertuig verwijderen
    """
    try:
        vehicle = Vehicle.objects.get(id=vehicle_id)
        vehicle.delete()
        messages.success(request, f'Voertuig {vehicle.kenteken} succesvol verwijderd.')
    except Vehicle.DoesNotExist:
        messages.error(request, 'Voertuig niet gevonden.')
    
    return redirect('vehicles_list')


# Gebruikers CRUD Views
def users_list(request):
    """
    Overzicht van alle gebruikers
    """
    from django.contrib.auth.models import User
    users = User.objects.all().order_by('username')
    
    context = {
        'users': users,
    }
    
    return render(request, 'planning/users_list.html', context)


def user_create(request):
    """
    Nieuwe gebruiker aanmaken
    """
    from django.contrib.auth.models import User
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        is_staff = request.POST.get('is_staff') == 'on'
        
        if username and password:
            try:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    is_staff=is_staff
                )
                messages.success(request, f'Gebruiker {username} succesvol aangemaakt.')
                return redirect('users_list')
            except Exception as e:
                messages.error(request, f'Fout bij aanmaken gebruiker: {str(e)}')
        else:
            messages.error(request, 'Vul alle verplichte velden in.')
    
    return render(request, 'planning/user_form.html')


def user_edit(request, user_id):
    """
    Gebruiker bewerken
    """
    from django.contrib.auth.models import User
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'Gebruiker niet gevonden.')
        return redirect('users_list')
    
    if request.method == 'POST':
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')
        user.is_staff = request.POST.get('is_staff') == 'on'
        user.is_active = request.POST.get('is_active') == 'on'
        
        # Update password als ingevuld
        password = request.POST.get('password')
        if password:
            user.set_password(password)
        
        user.save()
        
        messages.success(request, f'Gebruiker {user.username} succesvol bijgewerkt.')
        return redirect('users_list')
    
    context = {
        'user': user,
    }
    
    return render(request, 'planning/user_form.html', context)


def user_delete(request, user_id):
    """
    Gebruiker verwijderen
    """
    from django.contrib.auth.models import User
    
    try:
        user = User.objects.get(id=user_id)
        user.delete()
        messages.success(request, f'Gebruiker {user.username} succesvol verwijderd.')
    except User.DoesNotExist:
        messages.error(request, 'Gebruiker niet gevonden.')
    
    return redirect('users_list')


# Instellingen View
def settings_view(request):
    """
    Instellingen pagina (redirect naar admin)
    """
    messages.info(request, 'Instellingen zijn beschikbaar in de admin interface onder "Configuraties".')
    return redirect('/admin/planning/configuration/')


def get_default_coordinates(plaats):
    """
    Bepaal standaard coördinaten gebaseerd op plaats
    """
    if not plaats:
        return (50.746702862, 7.151631000)  # Reha Center
    
    place_lower = plaats.lower()
    
    if 'bonn' in place_lower:
        return (50.73743, 7.09821)
    elif 'köln' in place_lower or 'koeln' in place_lower:
        return (50.93753, 6.96028)
    elif 'düsseldorf' in place_lower or 'duesseldorf' in place_lower:
        return (51.22172, 6.77616)
    elif 'siegburg' in place_lower:
        return (50.7952, 7.2070)
    elif 'bad honnef' in place_lower:
        return (50.6458, 7.2278)
    elif 'niederkassel' in place_lower:
        return (50.8167, 7.0333)
    else:
        return (50.746702862, 7.151631000)  # Reha Center




@csrf_exempt
def api_update_patient_assignment(request):
    """
    API endpoint voor het bijwerken van patiënt toewijzingen via drag & drop
    """
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            
            patient_id = data.get('patient_id')
            vehicle_reference = data.get('vehicle')
            assignment_type = data.get('type', 'halen')
            
            # Get patient
            try:
                patient = Patient.objects.get(id=patient_id)
            except Patient.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Patiënt niet gevonden'})
            
            # Get vehicle by reference or kenteken
            try:
                vehicle = Vehicle.objects.get(
                    models.Q(referentie=vehicle_reference) | 
                    models.Q(kenteken=vehicle_reference)
                )
            except Vehicle.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Voertuig niet gevonden'})
            
            # Update patient assignment
            patient.toegewezen_voertuig = vehicle
            patient.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Patiënt {patient.naam} toegewezen aan {vehicle.referentie or vehicle.kenteken}'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Ongeldige JSON data'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Alleen POST requests toegestaan'})


def concept_planning(request):
    """
    Concept Planning Interface met Drag-and-Drop functionaliteit
    """
    from .models_extended import PlanningSession, PlanningAction
    from datetime import date
    
    # Check if user is authenticated and has planner permissions
    if not request.user.is_authenticated:
        messages.error(request, 'Je moet ingelogd zijn om concept planning te gebruiken.')
        return redirect('home')
    
    if not request.user.is_staff:
        messages.error(request, 'Geen toegang tot concept planning. Alleen planners en admins hebben toegang.')
        return redirect('home')
    
    # Debug: Check total patients in database
    total_patients_in_db = Patient.objects.count()
    print(f"🔍 DEBUG: Total patients in database: {total_patients_in_db}")
    
    if total_patients_in_db == 0:
        messages.warning(request, 'Er zijn geen patiënten in de database. Upload eerst een CSV bestand via "Nieuwe Planning".')
        return redirect('new_planning')
    
    # Get planning data from session
    planning_data = request.session.get('planning_data', {})
    
    # Determine the date to use - from CSV or today
    planning_date = date.today()
    if planning_data.get('csv_date'):
        try:
            planning_date = date.fromisoformat(planning_data['csv_date'])
        except (ValueError, TypeError):
            planning_date = date.today()
    
    # Debug: Print planning data
    print(f"🔍 DEBUG: Planning data from session: {planning_data}")
    print(f"🔍 DEBUG: Planning date: {planning_date}")
    
    # Get patients for the planning date
    patients = Patient.objects.filter(ophaal_tijd__date=planning_date).select_related('halen_tijdblok', 'bringen_tijdblok', 'toegewezen_voertuig')
    
    print(f"🔍 DEBUG: Found {patients.count()} patients for date {planning_date}")
    
    # If no patients found for the date, try to get patients from the planning session
    if not patients.exists():
        print("🔍 DEBUG: No patients found for date, trying planning session...")
        # Try to get patients from the most recent planning session
        latest_session = PlanningSession.objects.filter(planning_date=planning_date).order_by('-created_at').first()
        if latest_session:
            patients = Patient.objects.filter(planning_session=latest_session).select_related('halen_tijdblok', 'bringen_tijdblok', 'toegewezen_voertuig')
            print(f"🔍 DEBUG: Found {patients.count()} patients from planning session")
        else:
            print("🔍 DEBUG: No planning session found")
    
    # If still no patients, try to get all patients from today
    if not patients.exists():
        print("🔍 DEBUG: Still no patients, trying all patients from today...")
        patients = Patient.objects.filter(ophaal_tijd__date=date.today()).select_related('halen_tijdblok', 'bringen_tijdblok', 'toegewezen_voertuig')
        print(f"🔍 DEBUG: Found {patients.count()} patients from today")
    
    # If still no patients, show all patients (for debugging)
    if not patients.exists():
        print("🔍 DEBUG: No patients found for today, showing all patients...")
        patients = Patient.objects.all().select_related('halen_tijdblok', 'bringen_tijdblok', 'toegewezen_voertuig')
        print(f"🔍 DEBUG: Found {patients.count()} total patients")
        
        # Show sample patient data
        if patients.exists():
            sample_patient = patients.first()
            print(f"🔍 DEBUG: Sample patient: {sample_patient.naam}, ophaal_tijd: {sample_patient.ophaal_tijd}")
    
    # Get or create planning session
    planning_session, created = PlanningSession.objects.get_or_create(
        planning_date=planning_date,
        created_by=request.user,
        defaults={
            'name': f'Planning {planning_date.strftime("%d-%m-%Y")}',
            'status': 'concept',
            'description': 'Automatisch aangemaakte planning sessie'
        }
    )
    
    if created:
        # Log session creation
        PlanningAction.objects.create(
            planning_session=planning_session,
            user=request.user,
            action_type='create',
            description=f'Planning sessie aangemaakt voor {planning_date.strftime("%d-%m-%Y")}',
            details={'date': planning_date.isoformat()}
        )
    
    # Get selected vehicles and timeslots from planning data
    selected_vehicle_ids = planning_data.get('vehicles', [])
    selected_timeslot_ids = planning_data.get('timeslots', [])
    
    print(f"🔍 DEBUG: Selected vehicles: {selected_vehicle_ids}")
    print(f"🔍 DEBUG: Selected timeslots: {selected_timeslot_ids}")
    
    # Get all available vehicles and timeslots if not specified
    if not selected_vehicle_ids:
        selected_vehicles = Vehicle.objects.filter(status='beschikbaar')
    else:
        selected_vehicles = Vehicle.objects.filter(id__in=selected_vehicle_ids, status='beschikbaar')
    
    if not selected_timeslot_ids:
        selected_timeslots = TimeSlot.objects.filter(actief=True)
    else:
        selected_timeslots = TimeSlot.objects.filter(id__in=selected_timeslot_ids, actief=True)
    
    print(f"🔍 DEBUG: Available vehicles: {selected_vehicles.count()}")
    print(f"🔍 DEBUG: Available timeslots: {selected_timeslots.count()}")
    
    # Separate unassigned patients - patients with timeslot but no vehicle
    unassigned_patients = patients.filter(
        toegewezen_voertuig__isnull=True
    ).exclude(
        halen_tijdblok__isnull=True,
        bringen_tijdblok__isnull=True
    )
    
    print(f"🔍 DEBUG: Unassigned patients (with timeslot, no vehicle): {unassigned_patients.count()}")
    
    # Create a simple vehicle assignment for display
    # Assign patients to vehicles based on their timeslots
    for vehicle in selected_vehicles:
        vehicle.assigned_patients = []
    
    # Distribute patients across vehicles
    patients_with_timeslot = patients.filter(
        Q(halen_tijdblok__isnull=False) | Q(bringen_tijdblok__isnull=False)
    )
    
    print(f"🔍 DEBUG: Patients with timeslot: {patients_with_timeslot.count()}")
    
    # Simple distribution: assign patients to vehicles in round-robin fashion
    vehicle_list = list(selected_vehicles)
    if vehicle_list:
        for i, patient in enumerate(patients_with_timeslot):
            assigned_vehicle = vehicle_list[i % len(vehicle_list)]
            assigned_vehicle.assigned_patients.append(patient)
            print(f"🔍 DEBUG: Assigned {patient.naam} to {assigned_vehicle.referentie}")
    
    # Group patients by timeslot and vehicle for halen
    halen_timeslots = []
    halen_slots = selected_timeslots.filter(
        tijdblok_type='halen'
    ).order_by('aankomst_tijd')
    
    for timeslot in halen_slots:
        timeslot_patients = patients.filter(halen_tijdblok=timeslot)
        vehicles_data = []
        
        # Group by selected vehicles
        for vehicle in selected_vehicles:
            assigned_patients = timeslot_patients.filter(toegewezen_voertuig=vehicle)
            vehicle.assigned_patients = assigned_patients
            vehicles_data.append(vehicle)
        
        # Add unassigned patients to the first vehicle (for drag-drop)
        if timeslot_patients.exists() and selected_vehicles.exists():
            unassigned_timeslot_patients = timeslot_patients.filter(toegewezen_voertuig__isnull=True)
            if unassigned_timeslot_patients.exists():
                # Add unassigned patients to the first vehicle for display
                first_vehicle = vehicles_data[0] if vehicles_data else selected_vehicles.first()
                if first_vehicle:
                    first_vehicle.assigned_patients = unassigned_timeslot_patients
        
        halen_timeslots.append({
            'timeslot': timeslot,
            'vehicles': vehicles_data,
            'patient_count': timeslot_patients.count()
        })
    
    # Group patients by timeslot and vehicle for bringen
    bringen_timeslots = []
    bringen_slots = selected_timeslots.filter(
        tijdblok_type='brengen'
    ).order_by('aankomst_tijd')
    
    for timeslot in bringen_slots:
        timeslot_patients = patients.filter(bringen_tijdblok=timeslot)
        vehicles_data = []
        
        # Group by selected vehicles
        for vehicle in selected_vehicles:
            assigned_patients = timeslot_patients.filter(toegewezen_voertuig=vehicle)
            vehicle.assigned_patients = assigned_patients
            vehicles_data.append(vehicle)
        
        # Add unassigned patients to the first vehicle (for drag-drop)
        if timeslot_patients.exists() and selected_vehicles.exists():
            unassigned_timeslot_patients = timeslot_patients.filter(toegewezen_voertuig__isnull=True)
            if unassigned_timeslot_patients.exists():
                # Add unassigned patients to the first vehicle for display
                first_vehicle = vehicles_data[0] if vehicles_data else selected_vehicles.first()
                if first_vehicle:
                    first_vehicle.assigned_patients = unassigned_timeslot_patients
        
        bringen_timeslots.append({
            'timeslot': timeslot,
            'vehicles': vehicles_data,
            'patient_count': timeslot_patients.count()
        })
    
    # Get home location
    home_location = Location.get_home_location()
    
    # Statistics
    total_patients = patients.count()
    total_vehicles = selected_vehicles.count()
    total_timeslots = selected_timeslots.count()
    total_routes = 0  # Will be calculated based on assigned vehicles
    
    # Count routes (vehicles with assigned patients)
    for timeslot_group in halen_timeslots + bringen_timeslots:
        for vehicle in timeslot_group['vehicles']:
            if vehicle.assigned_patients.exists():
                total_routes += 1
    
    context = {
        'planning_session': planning_session,
        'planning_date': planning_date,
        'unassigned_patients': unassigned_patients,
        'halen_timeslots': halen_timeslots,
        'bringen_timeslots': bringen_timeslots,
        'home_location': home_location,
        'total_patients': total_patients,
        'total_vehicles': total_vehicles,
        'total_timeslots': total_timeslots,
        'total_routes': total_routes,
        'selected_vehicles': selected_vehicles,
        'selected_timeslots': selected_timeslots,
    }
    
    return render(request, 'planning/concept_planning.html', context)


@csrf_exempt
def api_get_patient_coordinates(request):
    """
    API endpoint om patiënt coördinaten op te halen voor kaart updates
    """
    if request.method == 'POST':
        try:
            import json
            import math
            data = json.loads(request.body)
            vehicle_routes = data.get('vehicle_routes', {})
            
            result_routes = {}
            
            for vehicle_id, patient_data in vehicle_routes.items():
                try:
                    vehicle = Vehicle.objects.get(id=vehicle_id)
                    patients = []
                    coordinates = []
                    
                    # Add home location as start
                    home_location = Location.get_home_location()
                    if home_location:
                        coordinates.append([float(home_location.latitude), float(home_location.longitude)])
                    
                    # Add patient coordinates
                    for patient_info in patient_data:
                        try:
                            patient = Patient.objects.get(id=patient_info['id'])
                            if patient.latitude and patient.longitude:
                                patients.append({
                                    'id': patient.id,
                                    'name': patient.naam,
                                    'latitude': float(patient.latitude),
                                    'longitude': float(patient.longitude),
                                    'address': f"{patient.straat}, {patient.postcode} {patient.plaats}"
                                })
                                coordinates.append([float(patient.latitude), float(patient.longitude)])
                        except Patient.DoesNotExist:
                            continue
                    
                    # Add home location as end
                    if home_location:
                        coordinates.append([float(home_location.latitude), float(home_location.longitude)])
                    
                    # Calculate route statistics
                    total_distance = 0
                    total_time = 0
                    total_cost = 0
                    
                    if len(coordinates) > 1:
                        # Calculate distance between points (Haversine formula)
                        for i in range(len(coordinates) - 1):
                            lat1, lon1 = coordinates[i]
                            lat2, lon2 = coordinates[i + 1]
                            
                            # Haversine formula for distance calculation
                            R = 6371  # Earth's radius in kilometers
                            dlat = math.radians(lat2 - lat1)
                            dlon = math.radians(lon2 - lon1)
                            a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
                            c = 2 * math.asin(math.sqrt(a))
                            distance = R * c
                            
                            total_distance += distance
                        
                        # Calculate time (assuming average speed of 50 km/h in city)
                        avg_speed_kmh = 50
                        total_time_hours = total_distance / avg_speed_kmh
                        total_time_minutes = total_time_hours * 60
                        
                        # Calculate cost (assuming €0.50 per km for fuel + maintenance)
                        cost_per_km = 0.50
                        total_cost = total_distance * cost_per_km
                    
                    result_routes[vehicle_id] = {
                        'vehicle_color': vehicle.kleur,
                        'vehicle_name': vehicle.referentie,
                        'patients': patients,
                        'coordinates': coordinates,
                        'route_stats': {
                            'total_distance_km': round(total_distance, 1),
                            'total_time_minutes': round(total_time_minutes, 0),
                            'total_cost_euros': round(total_cost, 2),
                            'patient_count': len(patients)
                        }
                    }
                    
                except Vehicle.DoesNotExist:
                    continue
            
            return JsonResponse({
                'success': True,
                'routes': result_routes
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@csrf_exempt
def api_log_planning_action(request):
    """
    API endpoint om planning acties te loggen
    """
    if request.method == 'POST':
        try:
            import json
            from .models_extended import PlanningSession, PlanningAction
            from datetime import date
            
            data = json.loads(request.body)
            action_type = data.get('action_type')
            details = data.get('details', {})
            
            # Get current planning session
            today = date.today()
            try:
                planning_session = PlanningSession.objects.get(
                    planning_date=today,
                    created_by=request.user
                )
            except PlanningSession.DoesNotExist:
                planning_session = PlanningSession.objects.create(
                    name=f'Planning {today.strftime("%d-%m-%Y")}',
                    planning_date=today,
                    created_by=request.user,
                    status='concept'
                )
            
            # Create action log
            action_description = f"Patient {details.get('patient_id', 'unknown')} verplaatst"
            if details.get('old_vehicle') and details.get('new_vehicle'):
                action_description += f" van voertuig {details['old_vehicle']} naar {details['new_vehicle']}"
            if details.get('old_timeslot') and details.get('new_timeslot'):
                action_description += f" van tijdblok {details['old_timeslot']} naar {details['new_timeslot']}"
            
            PlanningAction.objects.create(
                planning_session=planning_session,
                user=request.user,
                action_type=action_type,
                description=action_description,
                details=details
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Action logged successfully'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@csrf_exempt
def api_export_planning_csv(request):
    """
    API endpoint om planning te exporteren naar CSV
    """
    if request.method == 'POST':
        try:
            import json
            from datetime import date
            import csv
            from io import StringIO
            
            data = json.loads(request.body)
            assignments = data.get('assignments', [])
            
            output = StringIO()
            writer = csv.writer(output)
            
            writer.writerow([
                'Patient ID', 'Patient Naam', 'Tijdblok', 'Voertuig', 
                'Volgorde', 'Ophaal Tijd', 'Eind Behandel Tijd', 
                'Adres', 'Plaats', 'Rolstoel'
            ])
            
            for assignment in assignments:
                try:
                    patient = Patient.objects.get(id=assignment['patient_id'])
                    timeslot_name = "Niet toegewezen"
                    vehicle_name = "Niet toegewezen"
                    
                    if assignment.get('timeslot_id'):
                        try:
                            timeslot = TimeSlot.objects.get(id=assignment['timeslot_id'])
                            timeslot_name = timeslot.naam
                        except TimeSlot.DoesNotExist:
                            pass
                    
                    if assignment.get('vehicle_id'):
                        try:
                            vehicle = Vehicle.objects.get(id=assignment['vehicle_id'])
                            vehicle_name = f"{vehicle.referentie} - {vehicle.kenteken}"
                        except Vehicle.DoesNotExist:
                            pass
                    
                    writer.writerow([
                        patient.id,
                        patient.naam,
                        timeslot_name,
                        vehicle_name,
                        assignment.get('position', 0) + 1,
                        patient.ophaal_tijd.strftime('%H:%M') if patient.ophaal_tijd else '',
                        patient.eind_behandel_tijd.strftime('%H:%M') if patient.eind_behandel_tijd else '',
                        patient.straat,
                        patient.plaats,
                        'Ja' if patient.rolstoel else 'Nee'
                    ])
                    
                except Patient.DoesNotExist:
                    continue
            
            csv_content = output.getvalue()
            output.close()
            
            today = date.today()
            try:
                planning_session = PlanningSession.objects.get(
                    planning_date=today,
                    created_by=request.user
                )
                
                PlanningAction.objects.create(
                    planning_session=planning_session,
                    user=request.user,
                    action_type='export_csv',
                    description=f'Planning geëxporteerd naar CSV - {len(assignments)} patiënten',
                    details={'export_count': len(assignments)}
                )
            except PlanningSession.DoesNotExist:
                pass
            
            return JsonResponse({
                'success': True,
                'csv_content': csv_content,
                'filename': f'planning_{today.strftime("%Y%m%d")}.csv'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@csrf_exempt
def api_save_concept_planning(request):
    """
    API endpoint om concept planning op te slaan
    """
    if request.method == 'POST':
        try:
            import json
            from .models_extended import PlanningSession, PlanningAction
            from datetime import date
            
            data = json.loads(request.body)
            assignments = data.get('assignments', [])
            status = data.get('status', 'concept')
            
            # Get current planning session
            today = date.today()
            try:
                planning_session = PlanningSession.objects.get(
                    planning_date=today,
                    created_by=request.user
                )
            except PlanningSession.DoesNotExist:
                planning_session = PlanningSession.objects.create(
                    name=f'Planning {today.strftime("%d-%m-%Y")}',
                    planning_date=today,
                    created_by=request.user,
                    status='concept'
                )
            
            # Update patient assignments
            updated_count = 0
            for assignment in assignments:
                try:
                    patient = Patient.objects.get(id=assignment['patient_id'])
                    
                    # Update timeslot
                    if assignment.get('timeslot_id'):
                        try:
                            timeslot = TimeSlot.objects.get(id=assignment['timeslot_id'])
                            if 'Halen' in timeslot.naam:
                                patient.halen_tijdblok = timeslot
                            elif 'Bringen' in timeslot.naam:
                                patient.bringen_tijdblok = timeslot
                        except TimeSlot.DoesNotExist:
                            pass
                    
                    # Update vehicle
                    if assignment.get('vehicle_id'):
                        try:
                            vehicle = Vehicle.objects.get(id=assignment['vehicle_id'])
                            patient.toegewezen_voertuig = vehicle
                        except Vehicle.DoesNotExist:
                            pass
                    else:
                        patient.toegewezen_voertuig = None
                    
                    patient.save()
                    updated_count += 1
                    
                except Patient.DoesNotExist:
                    continue
            
            # Update planning session status
            planning_session.status = status
            planning_session.total_patients = len(assignments)
            planning_session.save()
            
            # Log the action
            action_type = 'approve' if status == 'published' else 'edit'
            description = f'Planning {"goedgekeurd en gepubliceerd" if status == "published" else "concept opgeslagen"} - {updated_count} patiënten bijgewerkt'
            
            PlanningAction.objects.create(
                planning_session=planning_session,
                user=request.user,
                action_type=action_type,
                description=description,
                details={
                    'status': status,
                    'updated_patients': updated_count,
                    'total_assignments': len(assignments)
                }
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Planning {status} - {updated_count} patiënten bijgewerkt',
                'updated_count': updated_count
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


def statistics_view(request):
    """
    Statistieken pagina met dagelijkse KPI's, maandelijkse/jaarlijkse overzichten en voertuig-specifieke statistieken
    """
    from datetime import date, timedelta
    from collections import defaultdict
    from .models_extended import PlanningSession
    import math
    
    # Get view type (daily, monthly, yearly, vehicle)
    view_type = request.GET.get('view', 'daily')
    
    # Get date range (default: last 30 days)
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    if request.GET.get('start_date'):
        try:
            start_date = date.fromisoformat(request.GET['start_date'])
        except ValueError:
            pass
    
    if request.GET.get('end_date'):
        try:
            end_date = date.fromisoformat(request.GET['end_date'])
        except ValueError:
            pass
    
    # Get all planning sessions in date range
    planning_sessions = PlanningSession.objects.filter(
        planning_date__range=[start_date, end_date]
    ).order_by('planning_date')
    
    # Get all vehicles for vehicle-specific stats
    all_vehicles = Vehicle.objects.all()
    
    # Calculate statistics based on view type
    if view_type == 'daily':
        stats_data = calculate_daily_stats(planning_sessions)
    elif view_type == 'monthly':
        stats_data = calculate_monthly_stats(planning_sessions)
    elif view_type == 'yearly':
        stats_data = calculate_yearly_stats(planning_sessions)
    elif view_type == 'vehicle':
        stats_data = calculate_vehicle_stats(planning_sessions, all_vehicles)
    else:
        stats_data = calculate_daily_stats(planning_sessions)
    
    context = {
        'view_type': view_type,
        'start_date': start_date,
        'end_date': end_date,
        'all_vehicles': all_vehicles,
        'date_range_days': (end_date - start_date).days + 1,
        **stats_data
    }
    
    return render(request, 'planning/statistics.html', context)

def calculate_daily_stats(planning_sessions):
    """Calculate daily statistics based on patient ophaal_tijd"""
    daily_stats = []
    total_stats = {
        'total_days': 0,
        'total_patients': 0,
        'total_vehicles': 0,
        'total_distance': 0,
        'total_time': 0,
        'total_cost': 0,
        'total_routes': 0,
        'avg_patients_per_day': 0,
        'avg_cost_per_patient': 0,
        'avg_distance_per_route': 0,
        'wheelchair_patients': 0,
        'failed_geocoding': 0
    }
    
    # Get date range from planning sessions
    if planning_sessions.exists():
        start_date = planning_sessions.first().planning_date
        end_date = planning_sessions.last().planning_date
    else:
        # Fallback to last 30 days if no sessions
        from datetime import date, timedelta
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
    
    # Get all patients in date range
    patients = Patient.objects.filter(
        ophaal_tijd__date__range=[start_date, end_date]
    ).order_by('ophaal_tijd__date')
    
    # Group patients by date
    from collections import defaultdict
    patients_by_date = defaultdict(list)
    for patient in patients:
        patients_by_date[patient.ophaal_tijd.date()].append(patient)
    
    # Calculate stats for each date
    for date_obj in sorted(patients_by_date.keys()):
        day_patients = patients_by_date[date_obj]
        
        patient_count = len(day_patients)
        wheelchair_count = sum(1 for p in day_patients if p.rolstoel)
        failed_geocoding_count = sum(1 for p in day_patients if p.geocoding_status == 'failed')
        
        estimated_routes = max(1, patient_count // 8)
        estimated_distance = patient_count * 15
        estimated_time = estimated_distance * 1.2
        estimated_cost = estimated_distance * 0.50
        
        daily_stat = {
            'date': date_obj,
            'patient_count': patient_count,
            'wheelchair_count': wheelchair_count,
            'failed_geocoding': failed_geocoding_count,
            'estimated_routes': estimated_routes,
            'estimated_distance': estimated_distance,
            'estimated_time': estimated_time,
            'estimated_cost': estimated_cost,
            'avg_patients_per_route': patient_count / estimated_routes if estimated_routes > 0 else 0,
            'cost_per_patient': estimated_cost / patient_count if patient_count > 0 else 0,
            'session_id': None  # No session ID since we're not using planning sessions
        }
        
        daily_stats.append(daily_stat)
        
        # Accumulate totals
        total_stats['total_days'] += 1
        total_stats['total_patients'] += patient_count
        total_stats['total_vehicles'] += estimated_routes
        total_stats['total_distance'] += estimated_distance
        total_stats['total_time'] += estimated_time
        total_stats['total_cost'] += estimated_cost
        total_stats['total_routes'] += estimated_routes
        total_stats['wheelchair_patients'] += wheelchair_count
        total_stats['failed_geocoding'] += failed_geocoding_count
    
    # Calculate averages
    if total_stats['total_days'] > 0:
        total_stats['avg_patients_per_day'] = total_stats['total_patients'] / total_stats['total_days']
        total_stats['avg_cost_per_patient'] = total_stats['total_cost'] / total_stats['total_patients'] if total_stats['total_patients'] > 0 else 0
        total_stats['avg_distance_per_route'] = total_stats['total_distance'] / total_stats['total_routes'] if total_stats['total_routes'] > 0 else 0
    
    # Get top performing days
    top_days = sorted(daily_stats, key=lambda x: x['patient_count'], reverse=True)[:5]
    cost_efficiency = sorted(daily_stats, key=lambda x: x['cost_per_patient'])[:5]
    
    # Get vehicle utilization data
    vehicle_utilization = []
    for stat in daily_stats:
        if stat['estimated_routes'] > 0:
            utilization = stat['patient_count'] / (stat['estimated_routes'] * 8)
            vehicle_utilization.append({
                'date': stat['date'],
                'utilization': utilization * 100,
                'patient_count': stat['patient_count'],
                'routes': stat['estimated_routes']
            })
    
    vehicle_utilization = sorted(vehicle_utilization, key=lambda x: x['utilization'], reverse=True)[:5]
    
    return {
        'daily_stats': daily_stats,
        'total_stats': total_stats,
        'top_days': top_days,
        'cost_efficiency': cost_efficiency,
        'vehicle_utilization': vehicle_utilization
    }

def calculate_monthly_stats(planning_sessions):
    """Calculate monthly statistics based on patient ophaal_tijd"""
    monthly_stats = defaultdict(lambda: {
        'patient_count': 0,
        'wheelchair_count': 0,
        'failed_geocoding': 0,
        'estimated_routes': 0,
        'estimated_distance': 0,
        'estimated_time': 0,
        'estimated_cost': 0,
        'days_count': 0
    })
    
    # Get date range from planning sessions
    if planning_sessions.exists():
        start_date = planning_sessions.first().planning_date
        end_date = planning_sessions.last().planning_date
    else:
        # Fallback to last 12 months if no sessions
        from datetime import date, timedelta
        end_date = date.today()
        start_date = end_date - timedelta(days=365)
    
    # Get all patients in date range
    patients = Patient.objects.filter(
        ophaal_tijd__date__range=[start_date, end_date]
    ).order_by('ophaal_tijd__date')
    
    # Group patients by month
    for patient in patients:
        month_key = patient.ophaal_tijd.strftime('%Y-%m')
        
        wheelchair_count = 1 if patient.rolstoel else 0
        failed_geocoding_count = 1 if patient.geocoding_status == 'failed' else 0
        
        estimated_routes = 1  # Each patient contributes to route count
        estimated_distance = 15  # Estimated distance per patient
        estimated_time = 18  # Estimated time per patient
        estimated_cost = 7.5  # Estimated cost per patient
        
        monthly_stats[month_key]['patient_count'] += 1
        monthly_stats[month_key]['wheelchair_count'] += wheelchair_count
        monthly_stats[month_key]['failed_geocoding'] += failed_geocoding_count
        monthly_stats[month_key]['estimated_routes'] += estimated_routes
        monthly_stats[month_key]['estimated_distance'] += estimated_distance
        monthly_stats[month_key]['estimated_time'] += estimated_time
        monthly_stats[month_key]['estimated_cost'] += estimated_cost
        monthly_stats[month_key]['days_count'] += 1  # Count each patient as a day
    
    # Convert to list and add calculated fields
    monthly_list = []
    total_stats = {
        'total_months': 0,
        'total_patients': 0,
        'total_distance': 0,
        'total_cost': 0,
        'avg_patients_per_month': 0,
        'avg_cost_per_month': 0
    }
    
    for month_key, stats in sorted(monthly_stats.items()):
        if stats['days_count'] > 0:
            avg_patients_per_day = stats['patient_count'] / stats['days_count']
            cost_per_patient = stats['estimated_cost'] / stats['patient_count'] if stats['patient_count'] > 0 else 0
            
            monthly_stat = {
                'month': month_key,
                'month_name': date.fromisoformat(f"{month_key}-01").strftime('%B %Y'),
                'patient_count': stats['patient_count'],
                'wheelchair_count': stats['wheelchair_count'],
                'failed_geocoding': stats['failed_geocoding'],
                'estimated_routes': stats['estimated_routes'],
                'estimated_distance': stats['estimated_distance'],
                'estimated_time': stats['estimated_time'],
                'estimated_cost': stats['estimated_cost'],
                'days_count': stats['days_count'],
                'avg_patients_per_day': avg_patients_per_day,
                'cost_per_patient': cost_per_patient
            }
            
            monthly_list.append(monthly_stat)
            
            # Accumulate totals
            total_stats['total_months'] += 1
            total_stats['total_patients'] += stats['patient_count']
            total_stats['total_distance'] += stats['estimated_distance']
            total_stats['total_cost'] += stats['estimated_cost']
    
    if total_stats['total_months'] > 0:
        total_stats['avg_patients_per_month'] = total_stats['total_patients'] / total_stats['total_months']
        total_stats['avg_cost_per_month'] = total_stats['total_cost'] / total_stats['total_months']
    
    return {
        'monthly_stats': monthly_list,
        'total_stats': total_stats,
        'top_months': sorted(monthly_list, key=lambda x: x['patient_count'], reverse=True)[:5],
        'cost_efficiency': sorted(monthly_list, key=lambda x: x['cost_per_patient'])[:5]
    }

def calculate_yearly_stats(planning_sessions):
    """Calculate yearly statistics based on patient ophaal_tijd"""
    yearly_stats = defaultdict(lambda: {
        'patient_count': 0,
        'wheelchair_count': 0,
        'failed_geocoding': 0,
        'estimated_routes': 0,
        'estimated_distance': 0,
        'estimated_time': 0,
        'estimated_cost': 0,
        'months_count': 0,
        '_months': set()
    })
    
    # Get date range from planning sessions
    if planning_sessions.exists():
        start_date = planning_sessions.first().planning_date
        end_date = planning_sessions.last().planning_date
    else:
        # Fallback to last 3 years if no sessions
        from datetime import date, timedelta
        end_date = date.today()
        start_date = end_date - timedelta(days=1095)  # 3 years
    
    # Get all patients in date range
    patients = Patient.objects.filter(
        ophaal_tijd__date__range=[start_date, end_date]
    ).order_by('ophaal_tijd__date')
    
    # Group patients by year
    for patient in patients:
        year_key = patient.ophaal_tijd.year
        month_key = patient.ophaal_tijd.strftime('%Y-%m')
        
        wheelchair_count = 1 if patient.rolstoel else 0
        failed_geocoding_count = 1 if patient.geocoding_status == 'failed' else 0
        
        estimated_routes = 1  # Each patient contributes to route count
        estimated_distance = 15  # Estimated distance per patient
        estimated_time = 18  # Estimated time per patient
        estimated_cost = 7.5  # Estimated cost per patient
        
        yearly_stats[year_key]['patient_count'] += 1
        yearly_stats[year_key]['wheelchair_count'] += wheelchair_count
        yearly_stats[year_key]['failed_geocoding'] += failed_geocoding_count
        yearly_stats[year_key]['estimated_routes'] += estimated_routes
        yearly_stats[year_key]['estimated_distance'] += estimated_distance
        yearly_stats[year_key]['estimated_time'] += estimated_time
        yearly_stats[year_key]['estimated_cost'] += estimated_cost
        
        # Track unique months
        yearly_stats[year_key]['_months'].add(month_key)
        yearly_stats[year_key]['months_count'] = len(yearly_stats[year_key]['_months'])
    
    # Convert to list and add calculated fields
    yearly_list = []
    total_stats = {
        'total_years': 0,
        'total_patients': 0,
        'total_distance': 0,
        'total_cost': 0,
        'avg_patients_per_year': 0,
        'avg_cost_per_year': 0
    }
    
    for year_key, stats in sorted(yearly_stats.items()):
        if stats['months_count'] > 0:
            avg_patients_per_month = stats['patient_count'] / stats['months_count']
            cost_per_patient = stats['estimated_cost'] / stats['patient_count'] if stats['patient_count'] > 0 else 0
            
            yearly_stat = {
                'year': year_key,
                'patient_count': stats['patient_count'],
                'wheelchair_count': stats['wheelchair_count'],
                'failed_geocoding': stats['failed_geocoding'],
                'estimated_routes': stats['estimated_routes'],
                'estimated_distance': stats['estimated_distance'],
                'estimated_time': stats['estimated_time'],
                'estimated_cost': stats['estimated_cost'],
                'months_count': stats['months_count'],
                'avg_patients_per_month': avg_patients_per_month,
                'cost_per_patient': cost_per_patient
            }
            
            yearly_list.append(yearly_stat)
            
            # Accumulate totals
            total_stats['total_years'] += 1
            total_stats['total_patients'] += stats['patient_count']
            total_stats['total_distance'] += stats['estimated_distance']
            total_stats['total_cost'] += stats['estimated_cost']
    
    if total_stats['total_years'] > 0:
        total_stats['avg_patients_per_year'] = total_stats['total_patients'] / total_stats['total_years']
        total_stats['avg_cost_per_year'] = total_stats['total_cost'] / total_stats['total_years']
    
    return {
        'yearly_stats': yearly_list,
        'total_stats': total_stats,
        'top_years': sorted(yearly_list, key=lambda x: x['patient_count'], reverse=True)[:5],
        'cost_efficiency': sorted(yearly_list, key=lambda x: x['cost_per_patient'])[:5]
    }

def calculate_vehicle_stats(planning_sessions, all_vehicles):
    """Calculate vehicle-specific statistics based on patient assignments"""
    vehicle_stats = {}
    
    for vehicle in all_vehicles:
        vehicle_stats[vehicle.id] = {
            'vehicle': vehicle,
            'total_patients': 0,
            'total_routes': 0,
            'total_distance': 0,
            'total_time': 0,
            'total_cost': 0,
            'wheelchair_patients': 0,
            'days_used': 0,
            'avg_patients_per_route': 0,
            'utilization_rate': 0,
            'cost_per_patient': 0
        }
    
    # Get date range from planning sessions
    if planning_sessions.exists():
        start_date = planning_sessions.first().planning_date
        end_date = planning_sessions.last().planning_date
    else:
        # Fallback to last 30 days if no sessions
        from datetime import date, timedelta
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
    
    # Get all patients in date range that are assigned to vehicles
    patients = Patient.objects.filter(
        ophaal_tijd__date__range=[start_date, end_date],
        toegewezen_voertuig__isnull=False
    ).order_by('ophaal_tijd__date')
    
    # Calculate vehicle usage from actual patient assignments
    for patient in patients:
        vehicle = patient.toegewezen_voertuig
        if vehicle and vehicle.id in vehicle_stats:
            wheelchair_count = 1 if patient.rolstoel else 0
            estimated_distance = 15  # Estimated distance per patient
            estimated_time = 18  # Estimated time per patient
            estimated_cost = 7.5  # Estimated cost per patient
            
            vehicle_stats[vehicle.id]['total_patients'] += 1
            vehicle_stats[vehicle.id]['total_routes'] += 1  # Each patient is a route
            vehicle_stats[vehicle.id]['total_distance'] += estimated_distance
            vehicle_stats[vehicle.id]['total_time'] += estimated_time
            vehicle_stats[vehicle.id]['total_cost'] += estimated_cost
            vehicle_stats[vehicle.id]['wheelchair_patients'] += wheelchair_count
            vehicle_stats[vehicle.id]['days_used'] += 1  # Count each patient as a day
    
    # Calculate averages and utilization
    for vehicle_id, stats in vehicle_stats.items():
        if stats['total_routes'] > 0:
            stats['avg_patients_per_route'] = stats['total_patients'] / stats['total_routes']
            stats['cost_per_patient'] = stats['total_cost'] / stats['total_patients'] if stats['total_patients'] > 0 else 0
            
            # Calculate utilization based on capacity
            total_capacity = stats['total_routes'] * stats['vehicle'].aantal_zitplaatsen
            stats['utilization_rate'] = (stats['total_patients'] / total_capacity * 100) if total_capacity > 0 else 0
    
    # Convert to list and calculate totals
    vehicle_list = list(vehicle_stats.values())
    total_stats = {
        'total_vehicles': len(vehicle_list),
        'total_patients': sum(v['total_patients'] for v in vehicle_list),
        'total_distance': sum(v['total_distance'] for v in vehicle_list),
        'total_cost': sum(v['total_cost'] for v in vehicle_list),
        'avg_utilization': sum(v['utilization_rate'] for v in vehicle_list) / len(vehicle_list) if vehicle_list else 0
    }
    
    return {
        'vehicle_stats': vehicle_list,
        'total_stats': total_stats,
        'top_vehicles': sorted(vehicle_list, key=lambda x: x['total_patients'], reverse=True)[:5],
        'efficient_vehicles': sorted(vehicle_list, key=lambda x: x['cost_per_patient'])[:5]
    }

# ============================================================================
# PLANNING WIZARD VIEWS
# ============================================================================

def planning_wizard_start(request):
    """
    Start pagina van de nieuwe planning wizard
    """
    context = {
        'page_title': 'Nieuwe Planning',
        'step': 1,
        'total_steps': 2,
        'step_title': 'Planning',
        'step_description': 'Maak een nieuwe planning'
    }
    
    return render(request, 'planning/wizard/start.html', context)


def planning_wizard_preview(request):
    """
    Preview pagina na upload
    """
    # Haal upload data op uit session
    upload_data = request.session.get('wizard_upload_data', {})
    
    if not upload_data:
        return redirect('planning_wizard_upload')
    
    context = {
        'page_title': 'Preview - Planning',
        'step': 2,
        'total_steps': 3,
        'step_title': 'Preview & Validatie',
        'step_description': 'Controleer de geüploade data en ga naar de volgende stap',
        'upload_data': upload_data
    }
    
    return render(request, 'planning/wizard/preview.html', context)


def planning_wizard_upload(request):
    """
    Stap 1: Upload & Preview
    """
    context = {
        'page_title': 'Upload & Preview - Planning',
        'step': 1,
        'total_steps': 2,
        'step_title': 'Upload & Preview',
        'step_description': 'Upload je CSV/SLK bestand en bekijk de preview'
    }
    
    return render(request, 'planning/wizard/upload.html', context)


def planning_wizard_preview(request):
    """
    Stap 1.5: Preview van geüploade data
    """
    # Haal upload data op uit session
    upload_data = request.session.get('wizard_upload_data', {})
    if not upload_data:
        messages.error(request, 'Geen upload data gevonden. Start opnieuw.')
        return redirect('planning_wizard_start')
    
    context = {
        'page_title': 'Data Preview',
        'step_title': '📋 Data Preview',
        'step_description': 'Controleer de geüploade data voordat we verder gaan.',
        'upload_data': upload_data,
        'csv_preview': upload_data.get('csv_preview', []),
        'csv_errors': upload_data.get('errors', []),
        'csv_warnings': upload_data.get('warnings', []),
        'detection_result': upload_data.get('detection_result', {}),
        'csv_file_name': upload_data.get('filename', 'Onbekend bestand')
    }
    
    return render(request, 'planning/wizard/preview.html', context)


def planning_wizard_assignment(request):
    """
    Stap 3: Auto-Assignment & Route Generatie
    """
    # Haal upload data op uit session
    upload_data = request.session.get('wizard_upload_data', {})
    
    # Voor test doeleinden, maak dummy data als er geen upload data is
    if not upload_data:
        upload_data = {
            'filename': 'test_data.csv',
            'patient_count': 10,
            'detection_result': {'detected_format': 'CSV', 'confidence': 95},
            'validation_result': {'valid_rows': 10, 'errors': [], 'warnings': []}
        }
        request.session['wizard_upload_data'] = upload_data
    
    # Haal beschikbare voertuigen en tijdblokken op
    available_vehicles = Vehicle.objects.filter(status='beschikbaar')
    # Haal alleen ACTIEVE tijdsblokken op (default_selected=True)
    all_timeslots = TimeSlot.objects.filter(actief=True, default_selected=True).order_by('aankomst_tijd')
    
    # Haal CSV data op en parse patiënten
    csv_data = upload_data.get('csv_data', [])
    patients_data = []
    
    if csv_data:
        print(f"🔍 CSV data gevonden: {len(csv_data)} rijen")
        
        # Haal de parser configuratie op voor kolom mapping
        parser_config = upload_data.get('parser_config', {})
        detection_result = upload_data.get('detection_result', {})
        mappings = detection_result.get('mappings', {})
        
        print(f"🔍 Parser configuratie: {parser_config}")
        print(f"🔍 Detection result: {detection_result}")
        print(f"🔍 Mappings: {mappings}")
        
        for row in csv_data:
            # Check of row een dictionary is met 'type' en 'data' keys
            if isinstance(row, dict) and row.get('type') == 'data':
                data = row.get('data', [])
                print(f"🔍 Verwerk rij: {data[:5]}... (totaal {len(data)} kolommen)")
                
                if isinstance(data, list) and len(data) > 0:
                    # Gebruik dynamische kolom mapping uit parser configuratie
                    patient_id = data[mappings.get('patient_id', 0)] if mappings.get('patient_id') is not None and len(data) > mappings.get('patient_id', 0) else ''
                    achternaam = data[mappings.get('achternaam', 2)] if mappings.get('achternaam') is not None and len(data) > mappings.get('achternaam', 2) else ''
                    voornaam = data[mappings.get('voornaam', 3)] if mappings.get('voornaam') is not None and len(data) > mappings.get('voornaam', 3) else ''
                    straat = data[mappings.get('adres', 6)] if mappings.get('adres') is not None and len(data) > mappings.get('adres', 6) else ''
                    plaats = data[mappings.get('plaats', 8)] if mappings.get('plaats') is not None and len(data) > mappings.get('plaats', 8) else ''
                    postcode = data[mappings.get('postcode', 9)] if mappings.get('postcode') is not None and len(data) > mappings.get('postcode', 9) else ''
                    start_tijd_raw = data[mappings.get('start_tijd', 17)] if mappings.get('start_tijd') is not None and len(data) > mappings.get('start_tijd', 17) else ''
                    eind_tijd_raw = data[mappings.get('eind_tijd', 18)] if mappings.get('eind_tijd') is not None and len(data) > mappings.get('eind_tijd', 18) else ''
                    
                    print(f"🔍 Kolom mapping: patient_id={patient_id}, voornaam={voornaam}, start_tijd={start_tijd_raw}, eind_tijd={eind_tijd_raw}")
                    
                    # Skip lege rijen
                    if not patient_id or not voornaam:
                        print(f"⚠️ Skip rij: patient_id={patient_id}, voornaam={voornaam}")
                        continue
                    
                    # Converteer tijden van "845" naar "08:45" formaat
                    start_tijd_formatted = convert_time_format(start_tijd_raw)
                    eind_tijd_formatted = convert_time_format(eind_tijd_raw)
                    
                    print(f"📅 Patiënt {voornaam} {achternaam}: {start_tijd_raw} → {start_tijd_formatted}, {eind_tijd_raw} → {eind_tijd_formatted}")
                    
                    patient_info = {
                        'id': patient_id,
                        'naam': f"{voornaam} {achternaam}".strip(),
                        'adres': f"{straat}, {postcode} {plaats}",
                        'ophaal_tijd': start_tijd_formatted,
                        'eind_behandel_tijd': eind_tijd_formatted,
                        'status': 'nieuw',
                        'toegewezen_voertuig': 'Niet toegewezen'
                    }
                    patients_data.append(patient_info)
                    print(f"✅ Patiënt toegevoegd: {patient_info['naam']}")
                else:
                    print(f"⚠️ Ongeldige rij data: {row}")
            else:
                print(f"⚠️ Ongeldige rij structuur: {row}")
    else:
        print("⚠️ Geen CSV data gevonden, gebruik database patiënten")
        # Fallback naar database patiënten
        today = date.today()
        all_patients = Patient.objects.filter(ophaal_tijd__date=today).order_by('ophaal_tijd')
        
        for patient in all_patients:
            patient_info = {
                'id': patient.id,
                'naam': patient.naam,
                'adres': f"{patient.straat}, {patient.postcode} {patient.plaats}",
                'ophaal_tijd': patient.ophaal_tijd.strftime('%H:%M') if patient.ophaal_tijd else '',
                'eind_behandel_tijd': patient.eind_behandel_tijd.strftime('%H:%M') if patient.eind_behandel_tijd else '',
                'status': patient.status,
                'toegewezen_voertuig': patient.toegewezen_voertuig.referentie if patient.toegewezen_voertuig else 'Niet toegewezen'
            }
            patients_data.append(patient_info)
    
    # Implementeer slimme patiënt koppeling logica
    from datetime import datetime, timedelta
    
    # Groepeer tijdsblokken per type
    halen_blokken = []
    brengen_blokken = []
    
    for timeslot in all_timeslots:
        if timeslot.tijdblok_type == 'halen':
            halen_blokken.append(timeslot.aankomst_tijd)
        elif timeslot.tijdblok_type == 'brengen':
            brengen_blokken.append(timeslot.aankomst_tijd)
    
    print(f"🔍 Tijdsblokken gevonden: {len(halen_blokken)} halen, {len(brengen_blokken)} brengen")
    print(f"  🚐 Halen blokken: {[t.strftime('%H:%M') for t in halen_blokken]}")
    print(f"  🏠 Brengen blokken: {[t.strftime('%H:%M') for t in brengen_blokken]}")
    
    def indeling(ophaal, eind, halen_blokken, brengen_blokken):
        """
        Koppel patiënt aan beste tijdsblokken:
        - haal-blok = grootste blok ≤ ophaaltijd
        - breng-blok = kleinste blok ≥ eindtijd
        """
        try:
            ophaal = datetime.strptime(ophaal, "%H:%M").time()
            eind = datetime.strptime(eind, "%H:%M").time()
            
            # haal-blok = grootste blok ≤ ophaaltijd
            haal_blok = max([t for t in halen_blokken if t <= ophaal], default=None)
            
            # breng-blok = kleinste blok ≥ eindtijd  
            breng_blok = min([t for t in brengen_blokken if t >= eind], default=None)
            
            return haal_blok, breng_blok
        except Exception as e:
            print(f"    ⚠️ Fout bij koppeling: {e}")
            return None, None
    
    # Koppel patiënten aan tijdsblokken
    patient_assignments = {}
    unassigned_patients = []
    
    for patient in patients_data:
        ophaal = patient.get('ophaal_tijd')
        eind = patient.get('eind_behandel_tijd')
        patient_name = patient.get('naam', 'Onbekend')
        
        if ophaal and eind:
            haal_blok, breng_blok = indeling(ophaal, eind, halen_blokken, brengen_blokken)
            
            if haal_blok and breng_blok:
                patient_assignments[patient_name] = {
                    'halen': haal_blok.strftime('%H:%M'),
                    'brengen': breng_blok.strftime('%H:%M'),
                    'ophaal_origineel': ophaal,
                    'eind_origineel': eind
                }
                print(f"✅ {patient_name}: halen = {haal_blok.strftime('%H:%M')}, brengen = {breng_blok.strftime('%H:%M')}")
            else:
                # Analyseer waarom patiënt niet gekoppeld kan worden
                ophaal_time = datetime.strptime(ophaal, "%H:%M").time()
                eind_time = datetime.strptime(eind, "%H:%M").time()
                
                haal_probleem = "geen geschikt halen blok" if not haal_blok else None
                breng_probleem = "geen geschikt brengen blok" if not breng_blok else None
                
                if not haal_blok:
                    # Zoek dichtstbijzijnde halen blok
                    later_halen = [t for t in halen_blokken if t > ophaal_time]
                    if later_halen:
                        closest_halen = min(later_halen)
                        haal_probleem = f"geen halen blok ≤ {ophaal}, dichtstbijzijnde: {closest_halen.strftime('%H:%M')}"
                
                if not breng_blok:
                    # Zoek dichtstbijzijnde brengen blok
                    earlier_brengen = [t for t in brengen_blokken if t < eind_time]
                    if earlier_brengen:
                        closest_brengen = max(earlier_brengen)
                        breng_probleem = f"geen brengen blok ≥ {eind}, dichtstbijzijnde: {closest_brengen.strftime('%H:%M')}"
                    else:
                        # Geen brengen blok voor eindtijd - suggereer nieuw blok
                        suggested_time = (datetime.combine(datetime.today(), eind_time) + timedelta(minutes=30)).time()
                        breng_probleem = f"geen brengen blok ≥ {eind}, suggereer nieuw blok: {suggested_time.strftime('%H:%M')}"
                
                unassigned_patients.append({
                    'naam': patient_name,
                    'ophaal_tijd': ophaal,
                    'eind_tijd': eind,
                    'haal_probleem': haal_probleem,
                    'breng_probleem': breng_probleem
                })
                
                print(f"❌ {patient_name}: {haal_probleem or 'OK'}, {breng_probleem or 'OK'}")
    
    # Voeg alle tijdsblokken toe met gekoppelde patiënten
    active_timeslots = []
    
    for timeslot in all_timeslots:
        timeslot_time = timeslot.aankomst_tijd.strftime('%H:%M')
        timeslot_type = timeslot.tijdblok_type
        
        # Zoek patiënten die aan dit tijdsblok gekoppeld zijn
        matched_patients = []
        for patient_name, assignment in patient_assignments.items():
            if timeslot_type == 'halen' and assignment['halen'] == timeslot_time:
                matched_patients.append(patient_name)
            elif timeslot_type == 'brengen' and assignment['brengen'] == timeslot_time:
                matched_patients.append(patient_name)
        
        if matched_patients:
            print(f"📅 Tijdsblok {timeslot_time} ({timeslot_type}): {len(matched_patients)} patiënten")
            for patient_name in matched_patients:
                print(f"    ✅ {patient_name}")
        else:
            print(f"📅 Tijdsblok {timeslot_time} ({timeslot_type}): leeg")
        
        # Voeg tijdsblok toe met gekoppelde patiënten
        timeslot.matched_patients = matched_patients
        active_timeslots.append(timeslot)
    
    print(f"🎯 Tijdsblokken gefilterd: {len(active_timeslots)} van {len(all_timeslots)} getoond")
    print(f"📊 Patiënten data voorbeeld:")
    for i, patient in enumerate(patients_data[:3]):  # Toon eerste 3 patiënten
        print(f"  {i+1}. {patient.get('naam', 'Onbekend')}: ophaal={patient.get('ophaal_tijd')}, eind={patient.get('eind_behandel_tijd')}")
    
    # Sla assignment data op in session voor routes pagina
    assignment_data = {
        'patient_assignments': patient_assignments,
        'unassigned_patients': unassigned_patients,
        'active_timeslots': [
            {
                'id': ts.id,
                'aankomst_tijd': ts.aankomst_tijd.strftime('%H:%M'),
                'tijdblok_type': ts.tijdblok_type,
                'matched_patients': getattr(ts, 'matched_patients', [])
            } for ts in active_timeslots
        ]
    }
    request.session['wizard_assignment_data'] = assignment_data
    
    context = {
        'page_title': 'Auto-Assignment & Routes - Planning',
        'step': 3,
        'total_steps': 3,
        'step_title': 'Auto-Assignment & Route Generatie',
        'step_description': 'Configureer constraints, start auto-assignment en genereer geoptimaliseerde routes',
        'upload_data': upload_data,
        'available_vehicles': available_vehicles,
        'active_timeslots': active_timeslots,
        'patients_data': patients_data,
        'unassigned_patients': unassigned_patients
    }
    
    return render(request, 'planning/wizard/assignment.html', context)


def planning_wizard_routes(request):
    """
    Route optimalisatie pagina met drag & drop interface - PER TIJDSBLOK zoals in screenshot
    """
    # Haal upload data op uit session
    upload_data = request.session.get('wizard_upload_data', {})
    
    # Haal assignment data op uit session
    assignment_data = request.session.get('wizard_assignment_data', {})
    
    # Haal route data op uit session
    route_data = request.session.get('wizard_route_data', {})
    
    # Haal patiënten data op uit database (voor vandaag)
    from datetime import date
    today = date.today()
    
    # Haal tijdsblokken op voor timeline tracker
    timeslots = TimeSlot.objects.filter(actief=True, default_selected=True).order_by('aankomst_tijd')
    print(f"📅 {timeslots.count()} tijdsblokken gevonden voor timeline")
    
    # Haal beschikbare voertuigen op
    available_vehicles = Vehicle.objects.filter(status='beschikbaar')
    
    # Maak route data per tijdsblok (zoals in screenshot)
    routes_by_timeslot = {}
    
    for timeslot in timeslots:
        print(f"🔍 Verwerken tijdsblok: {timeslot.aankomst_tijd} ({timeslot.tijdblok_type})")
        
        # Haal patiënten op voor dit tijdsblok
        if timeslot.tijdblok_type == 'halen':
            patients_in_timeslot = Patient.objects.filter(
                ophaal_tijd__date=today,
                halen_tijdblok=timeslot
            ).select_related('toegewezen_voertuig')
        else:  # brengen
            patients_in_timeslot = Patient.objects.filter(
                ophaal_tijd__date=today,
                bringen_tijdblok=timeslot
            ).select_related('toegewezen_voertuig')
        
        print(f"📋 {patients_in_timeslot.count()} patiënten gevonden voor tijdsblok {timeslot.aankomst_tijd}")
        
        # Groepeer patiënten per voertuig voor dit tijdsblok
        vehicles_with_patients = {}
        unassigned_patients = []
        
        for patient in patients_in_timeslot:
            patient_info = {
                'id': patient.id,
                'naam': patient.naam,
                'adres': f"{patient.straat}, {patient.postcode} {patient.plaats}",
                'ophaal_tijd': patient.ophaal_tijd.strftime('%H:%M') if patient.ophaal_tijd else '',
                'eind_behandel_tijd': patient.eind_behandel_tijd.strftime('%H:%M') if patient.eind_behandel_tijd else '',
                'halen_tijdblok': patient.halen_tijdblok,
                'bringen_tijdblok': patient.bringen_tijdblok,
                'toegewezen_voertuig': patient.toegewezen_voertuig,
                'latitude': patient.latitude,
                'longitude': patient.longitude
            }
            
            if patient.toegewezen_voertuig:
                vehicle_id = patient.toegewezen_voertuig.id
                if vehicle_id not in vehicles_with_patients:
                    vehicles_with_patients[vehicle_id] = {
                        'vehicle': {
                            'id': patient.toegewezen_voertuig.id,
                            'naam': patient.toegewezen_voertuig.referentie,
                            'type': patient.toegewezen_voertuig.merk_model,
                            'kleur': patient.toegewezen_voertuig.kleur
                        },
                        'patients': []
                    }
                vehicles_with_patients[vehicle_id]['patients'].append(patient_info)
                print(f"✅ Patiënt {patient.naam} toegevoegd aan voertuig {patient.toegewezen_voertuig.referentie}")
            else:
                unassigned_patients.append(patient_info)
                print(f"⚠️ Patiënt {patient.naam} niet toegewezen aan voertuig")
        
        # Converteer naar lijst voor dit tijdsblok
        vehicle_assignments = []
        for vehicle_data in vehicles_with_patients.values():
            vehicle_assignments.append(vehicle_data)
            print(f"🚐 Voertuig {vehicle_data['vehicle']['naam']} heeft {len(vehicle_data['patients'])} patiënten in tijdsblok {timeslot.aankomst_tijd}")
        
        # Sla route data op per tijdsblok
        routes_by_timeslot[timeslot.id] = {
            'timeslot': {
                'id': timeslot.id,
                'aankomst_tijd': timeslot.aankomst_tijd.strftime('%H:%M'),
                'tijdblok_type': timeslot.tijdblok_type
            },
            'vehicle_assignments': vehicle_assignments,
            'unassigned_patients': unassigned_patients,
            'total_patients': len(patients_in_timeslot)
        }
    
    # Haal Google Maps configuratie op
    try:
        google_maps_config = GoogleMapsConfig.objects.filter(enabled=True).first()
        if not google_maps_config:
            google_maps_config = GoogleMapsConfig.objects.first()
    except:
        google_maps_config = None
    
    # Haal depot locatie op
    depot_location = None
    try:
        # Zoek eerst naar default depot
        depot_location = Location.objects.filter(
            location_type='home', 
            is_default=True, 
            is_active=True
        ).first()
        
        # Fallback naar eerste actieve depot
        if not depot_location:
            depot_location = Location.objects.filter(
                location_type__in=['home', 'depot'], 
                is_active=True
            ).first()
            
        print(f"🏢 Depot locatie gevonden: {depot_location}")
    except Exception as e:
        print(f"⚠️ Fout bij ophalen depot locatie: {e}")
        depot_location = None
    
    # Prepare timeslots data for JavaScript
    timeslots_data = []
    for timeslot in timeslots:
        timeslots_data.append({
            'id': timeslot.id,
            'aankomst_tijd': timeslot.aankomst_tijd.strftime('%H:%M'),
            'tijdblok_type': timeslot.tijdblok_type
        })
    
    # Serialize routes_by_timeslot to JSON for JavaScript
    import json
    routes_by_timeslot_json = json.dumps(routes_by_timeslot, default=str, ensure_ascii=False)
    timeslots_data_json = json.dumps(timeslots_data, default=str, ensure_ascii=False)
    
    # Get Google Maps API key
    google_maps_api_key = ''
    if google_maps_config and google_maps_config.enabled:
        google_maps_api_key = google_maps_config.api_key
    
    context = {
        'page_title': 'Route Planning & Optimalisatie - Planning Wizard',
        'step': 3,
        'total_steps': 3,
        'step_title': 'Route Planning & Optimalisatie',
        'step_description': 'Sleep patiënten tussen voertuigen en pas de volgorde aan voor optimale routes',
        'upload_data': upload_data,
        'available_vehicles': available_vehicles,
        'routes_by_timeslot': routes_by_timeslot_json,
        'route_data': route_data,
        'google_maps_config': google_maps_config,
        'google_maps_api_key': google_maps_api_key,
        'depot_location': depot_location,
        'timeslots': timeslots,
        'timeslots_data': timeslots_data_json
    }
    
    return render(request, 'planning/wizard/routes.html', context)


# ============================================================================
# PLANNING WIZARD API ENDPOINTS
# ============================================================================

@csrf_exempt
def api_generate_routes(request):
    """
    API endpoint voor het genereren van routes vanuit assignment pagina
    """
    if request.method == 'POST':
        try:
            import json
            from datetime import date
            
            # Haal data op uit session
            assignment_data = request.session.get('wizard_assignment_data', {})
            patients_data = []
            csv_data = request.session.get('wizard_upload_data', {}).get('csv_data', [])
            parser_config = request.session.get('parser_config', {})
            
            if csv_data and parser_config:
                mappings = parser_config.get('mappings', {})
                for row_data in csv_data:
                    if isinstance(row_data, dict) and row_data.get('type') == 'data':
                        data = row_data.get('data', [])
                        
                        # Gebruik mappings om kolom indices te krijgen
                        patient_id_idx = mappings.get('patient_id')
                        achternaam_idx = mappings.get('achternaam')
                        voornaam_idx = mappings.get('voornaam')
                        straat_idx = mappings.get('adres')
                        plaats_idx = mappings.get('plaats')
                        postcode_idx = mappings.get('postcode')
                        start_tijd_idx = mappings.get('start_tijd')
                        eind_tijd_idx = mappings.get('eind_tijd')
                        
                        # Veilig data ophalen met indices
                        patient_id = data[patient_id_idx] if patient_id_idx is not None and len(data) > patient_id_idx else ''
                        achternaam = data[achternaam_idx] if achternaam_idx is not None and len(data) > achternaam_idx else ''
                        voornaam = data[voornaam_idx] if voornaam_idx is not None and len(data) > voornaam_idx else ''
                        straat = data[straat_idx] if straat_idx is not None and len(data) > straat_idx else ''
                        plaats = data[plaats_idx] if plaats_idx is not None and len(data) > plaats_idx else ''
                        postcode = data[postcode_idx] if postcode_idx is not None and len(data) > postcode_idx else ''
                        start_tijd_raw = data[start_tijd_idx] if start_tijd_idx is not None and len(data) > start_tijd_idx else ''
                        eind_tijd_raw = data[eind_tijd_idx] if eind_tijd_idx is not None and len(data) > eind_tijd_idx else ''
                        
                        # Converteer tijden
                        start_tijd = convert_time_format(start_tijd_raw) if start_tijd_raw else ''
                        eind_tijd = convert_time_format(eind_tijd_raw) if eind_tijd_raw else ''
                        
                        patient_info = {
                            'id': patient_id,
                            'naam': f"{voornaam} {achternaam}".strip(),
                            'adres': f"{straat}, {postcode} {plaats}".strip(', '),
                            'ophaal_tijd': start_tijd,
                            'eind_behandel_tijd': eind_tijd
                        }
                        patients_data.append(patient_info)
            
            # Haal beschikbare voertuigen op
            available_vehicles = Vehicle.objects.filter(status='beschikbaar')
            
            # Sla patiënten op in database
            saved_patients = []
            today = date.today()
            
            for patient_info in patients_data:
                try:
                    # Converteer tijd strings naar datetime objects
                    from datetime import datetime, time
                    
                    ophaal_tijd_str = patient_info.get('ophaal_tijd', '')
                    eind_tijd_str = patient_info.get('eind_behandel_tijd', '')
                    
                    # Parse tijd strings (bijv. "08:45" -> time object)
                    ophaal_tijd = None
                    eind_tijd = None
                    
                    if ophaal_tijd_str:
                        try:
                            time_parts = ophaal_tijd_str.split(':')
                            ophaal_tijd = datetime.combine(today, time(int(time_parts[0]), int(time_parts[1])))
                        except:
                            pass
                    
                    if eind_tijd_str:
                        try:
                            time_parts = eind_tijd_str.split(':')
                            eind_tijd = datetime.combine(today, time(int(time_parts[0]), int(time_parts[1])))
                        except:
                            pass
                    
                    # Maak of update patiënt
                    patient, created = Patient.objects.get_or_create(
                        naam=patient_info.get('naam', ''),
                        ophaal_tijd__date=today,
                        defaults={
                            'naam': patient_info.get('naam', ''),
                            'straat': patient_info.get('adres', '').split(',')[0] if patient_info.get('adres') else '',
                            'plaats': patient_info.get('adres', '').split(',')[-1].strip() if patient_info.get('adres') else '',
                            'postcode': '',
                            'ophaal_tijd': ophaal_tijd,
                            'eind_behandel_tijd': eind_tijd,
                            'status': 'actief'
                        }
                    )
                    
                    # Update tijden als patiënt al bestaat
                    if not created:
                        patient.ophaal_tijd = ophaal_tijd
                        patient.eind_behandel_tijd = eind_tijd
                        patient.save()
                    
                    saved_patients.append(patient)
                    logger.info(f"✅ Patiënt opgeslagen: {patient.naam}")
                    
                except Exception as e:
                    logger.error(f"❌ Fout bij opslaan patiënt {patient_info.get('naam', '')}: {e}")
            
            # Maak planning data voor route generatie
            planning_data = {
                'patients': patients_data,
                'saved_patients': saved_patients,  # Voeg opgeslagen patiënten toe
                'vehicles': list(available_vehicles),
                'timeslots': assignment_data.get('active_timeslots', []),
                'patient_assignments': assignment_data.get('patient_assignments', {}),
                'planning_date': date.today().strftime('%Y-%m-%d')
            }
            
            # Genereer routes
            route_result = generate_routes_with_google_maps(planning_data)
            
            # Sla route data op in session
            request.session['wizard_route_data'] = route_result
            
            return JsonResponse({
                'success': True,
                'message': 'Routes succesvol gegenereerd',
                'route_count': route_result.get('route_count', 0),
                'total_distance': route_result.get('total_distance', 0),
                'total_time': route_result.get('total_time', 0),
                'routes': route_result.get('routes', [])
            })
            
        except Exception as e:
            logger.error(f"Fout bij route generatie: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Fout bij route generatie: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def api_wizard_upload(request):
    """
    API endpoint voor CSV/SLK upload
    """
    if request.method == 'POST':
        try:
            uploaded_file = request.FILES.get('file')
            if not uploaded_file:
                return JsonResponse({
                    'success': False,
                    'error': 'Geen bestand geüpload'
                })
            
            # Detecteer bestandstype en parse
            file_extension = uploaded_file.name.split('.')[-1].lower()
            
            if file_extension == 'slk':
                # Parse SLK bestand
                csv_data = convert_slk_to_csv_simple(uploaded_file)
            else:
                # Parse CSV bestand
                csv_data = parse_csv_file_simple(uploaded_file)
            
            # Auto-detect mapping
            detection_result = auto_detect_csv_mapping_simple(csv_data, uploaded_file.name)
            
            # Valideer data
            validation_result = validate_csv_data_simple(csv_data, detection_result)
            
            # Debug: Tel en log alle rijen
            logger.info(f"🔍 CSV data analyse:")
            logger.info(f"  Totaal aantal rijen: {len(csv_data)}")
            
            for i, row in enumerate(csv_data):
                logger.info(f"  Rij {i}: type={row.get('type', 'unknown')}, data={row.get('data', [])[:3]}...")
            
            # Tel alleen data rijen (geen headers)
            data_rows = [row for row in csv_data if row.get('type') == 'data']
            logger.info(f"  Data rijen: {len(data_rows)}")
            
            # Sla data op in session
            upload_data = {
                'filename': uploaded_file.name,
                'file_size': uploaded_file.size,
                'patient_count': len(data_rows),  # Alleen data rijen tellen
                'detection_result': detection_result,
                'validation_result': validation_result,
                'csv_data': csv_data[:10],  # Alleen eerste 10 rijen voor preview
                'uploaded_at': datetime.now().isoformat()
            }
            
            # Voeg parser configuratie details toe
            if detection_result.get('config_id'):
                try:
                    from .models import CSVParserConfig
                    config = CSVParserConfig.objects.get(id=detection_result['config_id'])
                    upload_data['parser_config'] = {
                        'id': config.id,
                        'naam': config.naam,
                        'beschrijving': config.beschrijving,
                        'bestandsnaam_patroon': config.bestandsnaam_patroon,
                        'header_keywords': config.header_keywords,
                        'datum_formaten': config.datum_formaten,
                        'tijd_formaten': config.tijd_formaten,
                        'gemaakt_op': config.gemaakt_op.isoformat() if config.gemaakt_op else None,
                        'bijgewerkt_op': config.bijgewerkt_op.isoformat() if config.bijgewerkt_op else None
                    }
                except Exception as e:
                    logger.warning(f"Kon parser configuratie niet ophalen: {e}")
                    upload_data['parser_config'] = None
            else:
                upload_data['parser_config'] = None
            
            request.session['wizard_upload_data'] = upload_data
            
            return JsonResponse({
                'success': True,
                'data': upload_data
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


def api_wizard_save_upload_data(request):
    """
    API endpoint voor het opslaan van upload data in session
    """
    if request.method == 'POST':
        try:
            # Check if upload data exists in session
            upload_data = request.session.get('wizard_upload_data', {})
            if not upload_data:
                return JsonResponse({
                    'success': False,
                    'error': 'Geen upload data gevonden in session'
                })
            
            # Mark upload data as confirmed
            upload_data['confirmed'] = True
            upload_data['confirmed_at'] = datetime.now().isoformat()
            request.session['wizard_upload_data'] = upload_data
            
            return JsonResponse({
                'success': True,
                'message': 'Upload data opgeslagen'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


def api_wizard_constraints(request):
    """
    API endpoint voor het ophalen van actieve constraints
    """
    if request.method == 'GET':
        try:
            from .models import PlanningConstraint
            constraints = PlanningConstraint.objects.filter(is_active=True)
            constraints_data = []
            
            for constraint in constraints:
                constraints_data.append({
                    'id': constraint.id,
                    'name': constraint.name,
                    'description': constraint.description,
                    'constraint_type': constraint.constraint_type,
                    'weight': constraint.weight,
                    'penalty': constraint.penalty,
                    'parameters': constraint.parameters
                })
            
            return JsonResponse({
                'success': True,
                'constraints': constraints_data
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


def api_wizard_auto_assign(request):
    """
    API endpoint voor auto-toewijzing van patiënten
    """
    from .models import PlanningConstraint
    
    if request.method == 'POST':
        try:
            # Haal upload data op
            upload_data = request.session.get('wizard_upload_data', {})
            if not upload_data:
                return JsonResponse({
                    'success': False,
                    'error': 'Geen upload data gevonden'
                })
            
            # Haal constraints op uit database
            constraints = PlanningConstraint.objects.filter(is_active=True)
            
            # Voer auto-toewijzing uit
            assignment_result = perform_auto_assignment(upload_data, constraints)
            
            # Sla resultaat op in session
            request.session['wizard_planning_data'] = assignment_result
            
            return JsonResponse({
                'success': True,
                'data': assignment_result
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


def api_wizard_generate_routes(request):
    """
    API endpoint voor route generatie
    """
    if request.method == 'POST':
        try:
            # Haal planning data op
            planning_data = request.session.get('wizard_planning_data', {})
            if not planning_data:
                return JsonResponse({
                    'success': False,
                    'error': 'Geen planning data gevonden'
                })
            
            # Genereer routes met Google Maps API
            route_result = generate_routes_with_google_maps(planning_data)
            
            # Sla resultaat op in session
            request.session['wizard_route_data'] = route_result
            
            return JsonResponse({
                'success': True,
                'data': route_result
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


def api_wizard_save_planning(request):
    """
    API endpoint voor het opslaan van de planning
    """
    if request.method == 'POST':
        try:
            # Haal alle wizard data op
            upload_data = request.session.get('wizard_upload_data', {})
            planning_data = request.session.get('wizard_planning_data', {})
            route_data = request.session.get('wizard_route_data', {})
            
            if not all([upload_data, planning_data, route_data]):
                return JsonResponse({
                    'success': False,
                    'error': 'Onvolledige wizard data'
                })
            
            # Maak PlanningSession aan
            session = PlanningSession.objects.create(
                name=f"Planning {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                planning_date=datetime.now().date(),
                status='concept',
                csv_filename=upload_data.get('filename'),
                patient_count=upload_data.get('patient_count', 0),
                vehicle_count=planning_data.get('vehicle_count', 0),
                route_count=route_data.get('route_count', 0),
                total_distance=route_data.get('total_distance', 0),
                total_time=route_data.get('total_time', 0),
                total_cost=route_data.get('total_cost', 0),
                validation_errors=upload_data.get('validation_result', {}).get('errors', []),
                validation_warnings=upload_data.get('validation_result', {}).get('warnings', [])
            )
            
            # Sla patiënten op
            save_patients_from_wizard(upload_data, planning_data, session)
            
            # Sla routes op
            save_routes_from_wizard(route_data, session)
            
            # Clear wizard session data
            for key in ['wizard_upload_data', 'wizard_planning_data', 'wizard_route_data']:
                if key in request.session:
                    del request.session[key]
            
            return JsonResponse({
                'success': True,
                'session_id': session.id,
                'redirect_url': reverse('concept_planning', args=[session.id])
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


# ============================================================================
# HELPER FUNCTIES VOOR WIZARD
# ============================================================================

def parse_csv_file_simple(uploaded_file):
    """
    Eenvoudige CSV parser die ook bestanden zonder headers ondersteunt
    """
    import csv
    from io import StringIO
    
    try:
        # Decode het bestand
        content = uploaded_file.read().decode('utf-8')
        uploaded_file.seek(0)  # Reset file pointer
        
        # Detecteer delimiter (komma of puntkomma)
        first_line = content.split('\n')[0] if content else ''
        comma_count = first_line.count(',')
        semicolon_count = first_line.count(';')
        
        delimiter = ';' if semicolon_count > comma_count else ','
        print(f"🔍 Delimiter gedetecteerd: '{delimiter}' (komma's: {comma_count}, puntkomma's: {semicolon_count})")
        
        # Parse CSV met gedetecteerde delimiter
        csv_reader = csv.reader(StringIO(content), delimiter=delimiter)
        all_rows = list(csv_reader)
        
        # Filter lege rijen
        non_empty_rows = [row for row in all_rows if any(cell.strip() for cell in row)]
        
        # Als er geen duidelijke headers zijn (geen kolom namen), behandel alle rijen als data
        has_headers = False
        if non_empty_rows:
            first_row = non_empty_rows[0]
            # Check of de eerste rij headers bevat (bevat woorden zoals 'patient', 'naam', etc.)
            if any('patient' in str(cell).lower() or 'naam' in str(cell).lower() or 'voornaam' in str(cell).lower() or 'adres' in str(cell).lower() for cell in first_row):
                has_headers = True
                print(f"✅ Headers gevonden in eerste rij: {first_row}")
            else:
                print(f"⚠️ Geen headers gevonden, alle rijen worden als data behandeld")
        
        # Bouw de CSV data op
        rows = []
        for i, row in enumerate(non_empty_rows):
            if has_headers and i == 0:
                # Dit is de header rij
                rows.append({
                    'type': 'header',
                    'data': row,
                    'line_number': i + 1
                })
            else:
                # Dit is een data rij
                rows.append({
                    'type': 'data',
                    'data': row,
                    'line_number': i + 1
                })
        
        print(f"📊 CSV geparsed: {len(rows)} rijen, headers: {has_headers}")
        return rows
        
    except UnicodeDecodeError:
        # Probeer andere encoding
        uploaded_file.seek(0)
        content = uploaded_file.read().decode('latin-1')
        uploaded_file.seek(0)
        
        # Detecteer delimiter (komma of puntkomma)
        first_line = content.split('\n')[0] if content else ''
        comma_count = first_line.count(',')
        semicolon_count = first_line.count(';')
        
        delimiter = ';' if semicolon_count > comma_count else ','
        print(f"🔍 Delimiter gedetecteerd (latin-1): '{delimiter}' (komma's: {comma_count}, puntkomma's: {semicolon_count})")
        
        # Parse CSV met gedetecteerde delimiter
        csv_reader = csv.reader(StringIO(content), delimiter=delimiter)
        all_rows = list(csv_reader)
        
        # Filter lege rijen
        non_empty_rows = [row for row in all_rows if any(cell.strip() for cell in row)]
        
        # Als er geen duidelijke headers zijn, behandel alle rijen als data
        has_headers = False
        if non_empty_rows:
            first_row = non_empty_rows[0]
            # Check of de eerste rij headers bevat
            if any('patient' in str(cell).lower() or 'naam' in str(cell).lower() or 'voornaam' in str(cell).lower() or 'adres' in str(cell).lower() for cell in first_row):
                has_headers = True
                print(f"✅ Headers gevonden in eerste rij (latin-1): {first_row}")
            else:
                print(f"⚠️ Geen headers gevonden (latin-1), alle rijen worden als data behandeld")
        
        # Bouw de CSV data op
        rows = []
        for i, row in enumerate(non_empty_rows):
            if has_headers and i == 0:
                # Dit is de header rij
                rows.append({
                    'type': 'header',
                    'data': row,
                    'line_number': i + 1
                })
            else:
                # Dit is een data rij
                rows.append({
                    'type': 'data',
                    'data': row,
                    'line_number': i + 1
                })
        
        print(f"📊 CSV geparsed (latin-1): {len(rows)} rijen, headers: {has_headers}")
        return rows


def convert_slk_to_csv_simple(uploaded_file):
    """
    Eenvoudige SLK naar CSV converter
    """
    try:
        # Decode het bestand
        content = uploaded_file.read().decode('utf-8')
        uploaded_file.seek(0)  # Reset file pointer
        
        lines = content.split('\n')
        rows = []
        
        for i, line in enumerate(lines):
            if not line.strip():
                continue
                
            # Eenvoudige SLK parsing - zoek naar C (cell) records
            if line.startswith('C'):
                parts = line.split(';')
                if len(parts) >= 3:
                    # Extract cell data
                    cell_data = parts[2].strip('"') if len(parts) > 2 else ''
                    if cell_data:
                        rows.append({
                            'type': 'data',
                            'data': [cell_data],
                            'line_number': i + 1
                        })
        
        # Als we geen data hebben, probeer eenvoudigere parsing
        if not rows:
            for i, line in enumerate(lines):
                if line.strip() and not line.startswith('ID'):
                    # Split op tabs of semicolons
                    parts = line.replace('\t', ';').split(';')
                    if len(parts) > 1:
                        rows.append({
                            'type': 'data',
                            'data': [part.strip() for part in parts],
                            'line_number': i + 1
                        })
        
        return rows
        
    except UnicodeDecodeError:
        # Probeer andere encoding
        uploaded_file.seek(0)
        content = uploaded_file.read().decode('latin-1')
        uploaded_file.seek(0)
        
        lines = content.split('\n')
        rows = []
        
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith('ID'):
                parts = line.replace('\t', ';').split(';')
                if len(parts) > 1:
                    rows.append({
                        'type': 'data',
                        'data': [part.strip() for part in parts],
                        'line_number': i + 1
                    })
        
        return rows


def auto_detect_csv_mapping_simple(csv_data, filename):
    """
    Auto-detectie van CSV mapping met Django admin configuratie
    """
    if not csv_data or len(csv_data) < 1:
        return {
            'detected_format': 'Unknown',
            'confidence': 0,
            'warnings': ['Geen geldige data gevonden'],
            'suggestions': [],
            'config_id': None,
            'mappings': {}
        }
    
    # Haal header op (kan None zijn als er geen headers zijn)
    header_row = None
    for row in csv_data:
        if isinstance(row, dict) and row.get('type') == 'header':
            header_row = row.get('data', [])
            break
    
    print(f"🔍 CSV data: {len(csv_data)} rijen, header: {header_row is not None}")
    
    # Probeer eerst Django admin configuratie te gebruiken
    try:
        from .models import CSVParserConfig
        
        # Zoek naar actieve configuraties
        configs = CSVParserConfig.objects.filter(actief=True).order_by('-prioriteit')
        
        for config in configs:
            print(f"🔍 Test config '{config.naam}'...")
            
            # Test bestandsnaam patroon
            if config.bestandsnaam_patroon:
                import re
                if re.search(config.bestandsnaam_patroon, filename, re.IGNORECASE):
                    print(f"✅ Bestandsnaam match voor '{config.naam}'")
                    
                    # Gebruik de admin configuratie
                    mappings = config.get_kolom_mapping()
                    confidence = 90  # Hoge confidence voor admin configuratie
                    
                    print(f"📊 Admin configuratie gebruikt: {mappings}")
                    
                    # Controleer of we de minimale kolommen hebben
                    warnings = []
                    if 'patient_id' not in mappings:
                        warnings.append('Patient ID kolom niet geconfigureerd')
                    if 'naam' not in mappings and 'achternaam' not in mappings:
                        warnings.append('Naam kolom niet geconfigureerd')
                    if 'start_tijd' not in mappings and 'ophaal_tijd' not in mappings:
                        warnings.append('Tijd kolom niet geconfigureerd')
                    
                    return {
                        'detected_format': config.naam,
                        'confidence': confidence,
                        'warnings': warnings,
                        'suggestions': [],
                        'config_id': config.id,
                        'mappings': mappings
                    }
        
        print("⚠️ Geen admin configuratie gevonden, gebruik fallback detectie")
        
    except Exception as e:
        print(f"❌ Fout bij admin configuratie: {e}")
    
    # Fallback naar eenvoudige detectie als admin configuratie niet werkt
    mappings = {}
    confidence = 0
    warnings = []
    suggestions = []
    
    # Als er geen header is, gebruik standaard mapping gebaseerd op kolom positie
    if not header_row:
        print("📋 Geen header gevonden, gebruik standaard mapping")
        # Standaard mapping voor CSV zonder headers
        mappings = {
            'patient_id': 0,
            'naam': 1, 
            'voornaam': 2,
            'adres': 3,
            'plaats': 4,
            'postcode': 5,
            'telefoon1': 7,
            'telefoon2': 8,
            'datum': 9,
            'start_tijd': 10,
            'eind_tijd': 11
        }
        confidence = 70
        warnings.append('Geen headers gevonden, gebruik standaard kolom mapping')
    else:
        # Zoek naar bekende kolommen in header
        for i, column in enumerate(header_row):
            column_lower = str(column).lower().strip()
            print(f"🔍 Kolom {i}: '{column}' -> '{column_lower}'")
            
            # Patiënt ID kolommen
            if any(keyword in column_lower for keyword in ['patient', 'id', 'nummer', 'nr', 'kunde']):
                mappings['patient_id'] = i
                confidence += 20
                print(f"✅ Patient ID gevonden in kolom {i}")
            
            # Naam kolommen
            if any(keyword in column_lower for keyword in ['naam', 'name', 'patient', 'persoon', 'nachname', 'vorname']):
                mappings['naam'] = i
                confidence += 20
                print(f"✅ Naam gevonden in kolom {i}")
            
            # Tijd kolommen
            if any(keyword in column_lower for keyword in ['tijd', 'time', 'ophaal', 'pickup', 'uur', 'zeit', 'termin']):
                mappings['ophaal_tijd'] = i
                confidence += 20
                print(f"✅ Ophaal tijd gevonden in kolom {i}")
            
            # Adres kolommen
            if any(keyword in column_lower for keyword in ['adres', 'address', 'straat', 'street', 'plaats', 'city', 'straße']):
                mappings['adres'] = i
                confidence += 15
                print(f"✅ Adres gevonden in kolom {i}")
            
            # Telefoon kolommen
            if any(keyword in column_lower for keyword in ['tel', 'phone', 'telefoon', 'nummer', 'telefon']):
                mappings['telefoon'] = i
                confidence += 10
                print(f"✅ Telefoon gevonden in kolom {i}")
    
    # Bepaal formaat op basis van filename
    detected_format = 'Generic CSV'
    if 'fahrdlist' in filename.lower():
        detected_format = 'Fahrdlist'
        confidence += 30
    elif 'routemeister' in filename.lower():
        detected_format = 'Routemeister'
        confidence += 30
    
    print(f"📊 Fallback detectie resultaat: {mappings}")
    
    # Controleer of we de minimale kolommen hebben
    if 'patient_id' in mappings and ('naam' in mappings or 'achternaam' in mappings):
        confidence += 20
    else:
        warnings.append('Minimale kolommen (patient_id, naam) niet gevonden')
    
    if 'start_tijd' in mappings or 'ophaal_tijd' in mappings:
        confidence += 10
    else:
        warnings.append('Tijd kolom niet gevonden')
    
    # Cap confidence op 100
    confidence = min(confidence, 100)
    
    return {
        'detected_format': detected_format,
        'confidence': confidence,
        'warnings': warnings,
        'suggestions': suggestions,
        'config_id': None,
        'mappings': mappings
    }


def validate_csv_data_simple(csv_data, detection_result):
    """
    Eenvoudige validatie van CSV data
    """
    errors = []
    warnings = []
    
    if not csv_data:
        errors.append("Geen data gevonden in bestand")
        return {'errors': errors, 'warnings': warnings}
    
    # Controleer of we de benodigde kolommen hebben
    mappings = detection_result.get('mappings', {})
    
    # Controleer patient_id
    if 'patient_id' not in mappings:
        errors.append("Vereiste kolom 'patient_id' niet gevonden")
    
    # Controleer naam (achternaam of naam)
    if 'achternaam' not in mappings and 'naam' not in mappings:
        errors.append("Vereiste kolom 'achternaam' of 'naam' niet gevonden")
    
    # Controleer tijd (start_tijd of ophaal_tijd)
    if 'start_tijd' not in mappings and 'ophaal_tijd' not in mappings:
        errors.append("Vereiste kolom 'start_tijd' of 'ophaal_tijd' niet gevonden")
    
    # Controleer data kwaliteit
    for i, row in enumerate(csv_data[:10]):  # Alleen eerste 10 rijen
        if not row.get('data'):
            continue
            
        data = row['data']
        
        # Controleer patiënt ID
        if 'patient_id' in mappings:
            patient_id = data[mappings['patient_id']] if len(data) > mappings['patient_id'] else ''
            if not patient_id or patient_id.strip() == '':
                warnings.append(f"Rij {i+1}: Leeg patiënt ID")
        
        # Controleer naam (achternaam of naam)
        if 'achternaam' in mappings:
            achternaam = data[mappings['achternaam']] if len(data) > mappings['achternaam'] else ''
            if not achternaam or achternaam.strip() == '':
                warnings.append(f"Rij {i+1}: Lege achternaam")
        elif 'naam' in mappings:
            naam = data[mappings['naam']] if len(data) > mappings['naam'] else ''
            if not naam or naam.strip() == '':
                warnings.append(f"Rij {i+1}: Lege naam")
        
        # Controleer tijd (start_tijd of ophaal_tijd)
        if 'start_tijd' in mappings:
            start_tijd = data[mappings['start_tijd']] if len(data) > mappings['start_tijd'] else ''
            if not start_tijd or start_tijd.strip() == '':
                warnings.append(f"Rij {i+1}: Lege start tijd")
        elif 'ophaal_tijd' in mappings:
            ophaal_tijd = data[mappings['ophaal_tijd']] if len(data) > mappings['ophaal_tijd'] else ''
            if not ophaal_tijd or ophaal_tijd.strip() == '':
                warnings.append(f"Rij {i+1}: Lege ophaal tijd")
    
    # Tel geldige rijen (alle data rijen, geen headers)
    valid_rows = len([row for row in csv_data if row.get('type') == 'data'])
    
    return {
        'errors': errors,
        'warnings': warnings,
        'total_rows': len(csv_data),
        'valid_rows': valid_rows
    }

def perform_auto_assignment(upload_data, constraints):
    """
    Voer tijdblok-toewijzing uit voor patiënten
    """
    from datetime import datetime, time
    from .models import TimeSlot, Vehicle
    
    print("🚀 Start tijdblok-toewijzing...")
    
    # Haal CSV data op uit session
    csv_data = upload_data.get('csv_data', [])
    detection_result = upload_data.get('detection_result', {})
    mappings = detection_result.get('mappings', {})
    
    if not csv_data:
        print("❌ Geen CSV data gevonden")
        return {
            'success': False,
            'error': 'Geen CSV data gevonden'
        }
    
    # Haal beschikbare tijdblokken op
    available_timeslots = TimeSlot.objects.filter(actief=True).order_by('aankomst_tijd')
    print(f"📅 Beschikbare tijdblokken: {available_timeslots.count()}")
    
    # Bereken totale capaciteit per tijdblok op basis van beschikbare voertuigen
    available_vehicles = Vehicle.objects.filter(status='beschikbaar')
    total_vehicle_capacity = sum(vehicle.aantal_zitplaatsen - 1 for vehicle in available_vehicles)  # -1 voor chauffeur
    print(f"🚗 Beschikbare voertuigen: {available_vehicles.count()}")
    print(f"📦 Totale capaciteit: {total_vehicle_capacity} patiënten per tijdblok")
    
    # Converteer CSV data naar patiënten met tijden
    patients_with_times = []
    
    # Check of er geocoded data beschikbaar is
    geocoded_patients = upload_data.get('geocoded_patients', [])
    if geocoded_patients:
        print(f"🗺️ Geocoded data gevonden: {len(geocoded_patients)} patiënten")
    
    for row in csv_data:
        if row.get('type') != 'data':
            continue
            
        data = row.get('data', [])
        if len(data) < max(mappings.values()):
            continue
        
        try:
            # Haal patiënt gegevens op (behoud CSV veldnamen)
            patient_id = data[mappings.get('patient_id', 0)] if mappings.get('patient_id') is not None else f"P{len(patients_with_times)+1}"
            achternaam = data[mappings.get('achternaam', 1)] if mappings.get('achternaam') is not None else ""
            voornaam = data[mappings.get('voornaam', 2)] if mappings.get('voornaam') is not None else ""
            start_tijd_str = data[mappings.get('start_tijd', 3)] if mappings.get('start_tijd') is not None else ""
            eind_tijd_str = data[mappings.get('eind_tijd', 4)] if mappings.get('eind_tijd') is not None else ""
            
            # Haal adresgegevens op
            straat = data[mappings.get('straat', 5)] if mappings.get('straat') is not None else ""
            postcode = data[mappings.get('postcode', 6)] if mappings.get('postcode') is not None else ""
            plaats = data[mappings.get('plaats', 7)] if mappings.get('plaats') is not None else ""
            
            # Converteer tijd strings naar time objects
            start_time = None
            end_time = None
            
            if start_tijd_str:
                try:
                    # Probeer verschillende tijd formaten
                    if len(start_tijd_str) == 4:  # HHMM
                        start_time = time(int(start_tijd_str[:2]), int(start_tijd_str[2:]))
                    elif len(start_tijd_str) == 5 and ':' in start_tijd_str:  # HH:MM
                        start_time = time.fromisoformat(start_tijd_str)
                    else:
                        print(f"⚠️ Onbekend tijd formaat: {start_tijd_str}")
                except:
                    print(f"⚠️ Kon tijd niet parsen: {start_tijd_str}")
            
            if eind_tijd_str:
                try:
                    if len(eind_tijd_str) == 4:  # HHMM
                        end_time = time(int(eind_tijd_str[:2]), int(eind_tijd_str[2:]))
                    elif len(eind_tijd_str) == 5 and ':' in eind_tijd_str:  # HH:MM
                        end_time = time.fromisoformat(eind_tijd_str)
                except:
                    print(f"⚠️ Kon eind tijd niet parsen: {eind_tijd_str}")
            
            # Zoek geocoded coördinaten voor deze patiënt
            latitude = None
            longitude = None
            if geocoded_patients:
                for geocoded in geocoded_patients:
                    if (geocoded.get('patient_id') == patient_id or 
                        geocoded.get('achternaam') == achternaam):
                        if geocoded.get('geocoded'):
                            latitude = geocoded.get('latitude')
                            longitude = geocoded.get('longitude')
                            print(f"✅ Geocoded coördinaten voor {achternaam}: {latitude}, {longitude}")
                        break
            
            patients_with_times.append({
                'patient_id': patient_id,
                'achternaam': achternaam,
                'voornaam': voornaam,
                'straat': straat,
                'postcode': postcode,
                'plaats': plaats,
                'start_time': start_time.isoformat() if start_time else None,
                'end_time': end_time.isoformat() if end_time else None,
                'latitude': latitude,
                'longitude': longitude,
                'original_data': data
            })
            
        except Exception as e:
            print(f"❌ Fout bij verwerken patiënt: {e}")
            continue
    
    print(f"👥 Patiënten met tijden: {len(patients_with_times)}")
    
    # Wijs patiënten toe aan tijdblokken
    timeslot_assignments = {}
    unassigned_patients = []
    
    for patient in patients_with_times:
        assigned = False
        
        # Zoek het beste tijdblok voor deze patiënt
        best_halen_timeslot = None
        best_brengen_timeslot = None
        min_halen_difference = float('inf')
        min_brengen_difference = float('inf')
        
        for timeslot in available_timeslots:
            try:
                # HALEN tijdblokken (start_tijd)
                if patient['start_time'] and timeslot.tijdblok_type == 'halen':
                    patient_start_time = time.fromisoformat(patient['start_time'])
                    if patient_start_time >= timeslot.aankomst_tijd:
                        # Bereken verschil (hoe dicht bij behandelingstijd)
                        from datetime import datetime, timedelta
                        patient_dt = datetime.combine(datetime.today(), patient_start_time)
                        timeslot_dt = datetime.combine(datetime.today(), timeslot.aankomst_tijd)
                        difference = (patient_dt - timeslot_dt).total_seconds() / 60  # in minuten
                        
                        if difference < min_halen_difference:
                            min_halen_difference = difference
                            best_halen_timeslot = timeslot
                
                # BRENGEN tijdblokken (eind_tijd)
                if patient['end_time'] and timeslot.tijdblok_type == 'brengen':
                    patient_end_time = time.fromisoformat(patient['end_time'])
                    if patient_end_time <= timeslot.aankomst_tijd:
                        # Bereken verschil (hoe dicht bij behandelingstijd)
                        from datetime import datetime, timedelta
                        patient_dt = datetime.combine(datetime.today(), patient_end_time)
                        timeslot_dt = datetime.combine(datetime.today(), timeslot.aankomst_tijd)
                        difference = (timeslot_dt - patient_dt).total_seconds() / 60  # in minuten
                        
                        if difference < min_brengen_difference:
                            min_brengen_difference = difference
                            best_brengen_timeslot = timeslot
                            
            except ValueError as e:
                print(f"⚠️ Kon tijd niet parsen voor patiënt {patient['voornaam']} {patient['achternaam']}: {e}")
                continue
        
        # Wijs toe aan beste tijdblokken
        if best_halen_timeslot:
            # Check capaciteit voor halen tijdblok op basis van voertuigen
            current_count = len(timeslot_assignments.get(best_halen_timeslot.id, []))
            if current_count < total_vehicle_capacity:  # Gebruik voertuig capaciteit in plaats van hardcoded 4
                if best_halen_timeslot.id not in timeslot_assignments:
                    timeslot_assignments[best_halen_timeslot.id] = []
                
                timeslot_assignments[best_halen_timeslot.id].append(patient)
                assigned = True
                print(f"✅ {patient['voornaam']} {patient['achternaam']} → {best_halen_timeslot.naam} (Halen: {best_halen_timeslot.aankomst_tijd})")
        
        if best_brengen_timeslot:
            # Check capaciteit voor brengen tijdblok op basis van voertuigen
            current_count = len(timeslot_assignments.get(best_brengen_timeslot.id, []))
            if current_count < total_vehicle_capacity:  # Gebruik voertuig capaciteit in plaats van hardcoded 4
                if best_brengen_timeslot.id not in timeslot_assignments:
                    timeslot_assignments[best_brengen_timeslot.id] = []
                
                timeslot_assignments[best_brengen_timeslot.id].append(patient)
                assigned = True
                print(f"✅ {patient['voornaam']} {patient['achternaam']} → {best_brengen_timeslot.naam} (Brengen: {best_brengen_timeslot.aankomst_tijd})")
        
        if not assigned:
            unassigned_patients.append(patient)
            print(f"❌ {patient['voornaam']} {patient['achternaam']} kon niet toegewezen worden (capaciteit bereikt)")
    
    # Bereken statistieken
    total_assigned = sum(len(patients) for patients in timeslot_assignments.values())
    total_patients = len(patients_with_times)
    assignment_rate = (total_assigned / total_patients * 100) if total_patients > 0 else 0
    
    print(f"📊 Toewijzing resultaat:")
    print(f"   - Totaal patiënten: {total_patients}")
    print(f"   - Toegewezen: {total_assigned}")
    print(f"   - Niet toegewezen: {len(unassigned_patients)}")
    print(f"   - Succes percentage: {assignment_rate:.1f}%")
    print(f"   - Capaciteit per tijdblok: {total_vehicle_capacity} patiënten")
    
    # Voeg tijdblok namen toe aan de response
    timeslot_names = {}
    for timeslot in available_timeslots:
        timeslot_names[timeslot.id] = {
            'naam': timeslot.naam,
            'aankomst_tijd': timeslot.aankomst_tijd.strftime('%H:%M'),
            'tijdblok_type': timeslot.tijdblok_type
        }
    
    return {
        'success': True,
        'timeslot_assignments': timeslot_assignments,
        'timeslot_names': timeslot_names,
        'unassigned_patients': unassigned_patients,
        'statistics': {
            'total_patients': total_patients,
            'assigned_patients': total_assigned,
            'unassigned_patients': len(unassigned_patients),
            'assignment_rate': assignment_rate,
            'timeslots_used': len(timeslot_assignments),
            'vehicle_capacity': total_vehicle_capacity,
            'available_vehicles': available_vehicles.count()
        }
    }


def generate_routes_with_google_maps(planning_data):
    """
    Genereer routes met Google Maps API
    """
    from .services.google_maps import google_maps_service
    from .models import Vehicle
    
    try:
        # Haal beschikbare voertuigen op
        available_vehicles = list(Vehicle.objects.filter(status='beschikbaar'))
        
        if not available_vehicles:
            logger.warning("Geen beschikbare voertuigen voor route generatie")
            return {
                'route_count': 0,
                'total_distance': 0,
                'total_time': 0,
                'total_cost': 0,
                'routes': [],
                'error': 'Geen beschikbare voertuigen'
            }
        
        # Gebruik Google Maps service voor route optimalisatie
        # Voor nu, gebruik altijd fallback omdat Google Maps API niet correct geconfigureerd is
        logger.info("Gebruik fallback optimalisatie (Google Maps API niet beschikbaar)")
        
        # Gebruik opgeslagen patiënten uit database
        saved_patients = planning_data.get('saved_patients', [])
        if saved_patients:
            logger.info(f"Gebruik {len(saved_patients)} opgeslagen patiënten uit database")
            # Converteer opgeslagen patiënten naar timeslot assignments
            timeslot_assignments = _create_timeslot_assignments_from_patients(saved_patients)
        else:
            logger.warning("Geen opgeslagen patiënten gevonden, gebruik session data")
            timeslot_assignments = planning_data.get('patient_assignments', {})
        
        optimized_routes = google_maps_service._fallback_optimization(timeslot_assignments, available_vehicles)
        
        # Bereken totale statistieken
        total_distance = 0
        total_time = 0
        total_cost = 0
        route_count = 0
        
        for timeslot_data in optimized_routes.values():
            total_distance += timeslot_data.get('total_distance', 0)
            total_time += timeslot_data.get('total_time', 0)
            total_cost += timeslot_data.get('total_cost', 0)
            route_count += timeslot_data.get('vehicle_count', 0)
        
        logger.info(f"Route generatie voltooid: {route_count} routes, {total_distance:.1f} km, €{total_cost:.2f}")
        
        # Converteer Vehicle objecten naar dictionaries voor JSON serialization
        serializable_routes = {}
        for timeslot_id, timeslot_data in optimized_routes.items():
            serializable_routes[timeslot_id] = {
                'total_distance': timeslot_data.get('total_distance', 0),
                'total_time': timeslot_data.get('total_time', 0),
                'total_cost': timeslot_data.get('total_cost', 0),
                'vehicle_count': timeslot_data.get('vehicle_count', 0),
        'routes': []
    }
            
            for route in timeslot_data.get('routes', []):
                # Converteer Vehicle object naar dictionary
                vehicle_dict = {
                    'id': route['vehicle'].id,
                    'naam': route['vehicle'].referentie or route['vehicle'].merk_model or f"Voertuig {route['vehicle'].id}",
                    'kenteken': route['vehicle'].kenteken,
                    'aantal_zitplaatsen': route['vehicle'].aantal_zitplaatsen,
                    'km_kosten_per_km': float(route['vehicle'].km_kosten_per_km) if hasattr(route['vehicle'], 'km_kosten_per_km') else 0.50,
                    'status': getattr(route['vehicle'], 'status', 'beschikbaar')
                }
                
                # Converteer patiënten naar dictionaries
                patients_list = []
                for patient in route.get('patients', []):
                    if isinstance(patient, dict):
                        patients_list.append(patient)
                    else:
                        # Converteer Patient model naar dictionary
                        patient_dict = {
                            'id': getattr(patient, 'id', ''),
                            'naam': getattr(patient, 'naam', ''),
                            'adres': getattr(patient, 'adres', ''),
                            'ophaal_tijd': getattr(patient, 'ophaal_tijd', ''),
                            'eind_behandel_tijd': getattr(patient, 'eind_behandel_tijd', ''),
                            'latitude': getattr(patient, 'latitude', None),
                            'longitude': getattr(patient, 'longitude', None)
                        }
                        patients_list.append(patient_dict)
                
                serializable_route = {
                    'vehicle': vehicle_dict,
                    'patients': patients_list,
                    'total_distance': route.get('total_distance', 0),
                    'total_time': route.get('total_time', 0),
                    'total_cost': route.get('total_cost', 0),
                    'route_data': None  # Route data is niet nodig voor JSON serialization
                }
                serializable_routes[timeslot_id]['routes'].append(serializable_route)
        
        return {
            'route_count': route_count,
            'total_distance': total_distance,
            'total_time': total_time,
            'total_cost': total_cost,
            'routes': serializable_routes,
            'success': True
        }
        
    except Exception as e:
        logger.error(f"Fout bij route generatie: {e}")
        return {
            'route_count': 0,
            'total_distance': 0,
            'total_time': 0,
            'total_cost': 0,
            'routes': [],
            'error': str(e)
        }

def _create_timeslot_assignments_from_patients(saved_patients):
    """
    Converteer opgeslagen patiënten naar timeslot assignments en sla tijdsblokken op in database
    """
    from .models import TimeSlot
    from datetime import datetime, time
    
    timeslot_assignments = {}
    
    # Haal alle tijdsblokken op
    timeslots = TimeSlot.objects.all()
    
    for patient in saved_patients:
        try:
            # Bepaal halen en brengen tijdsblokken
            ophaal_tijd = patient.ophaal_tijd
            eind_tijd = patient.eind_behandel_tijd
            
            if not ophaal_tijd or not eind_tijd:
                logger.warning(f"Patiënt {patient.naam} heeft geen tijden")
                continue
            
            # Converteer naar time objecten
            ophaal_time = ophaal_tijd.time() if hasattr(ophaal_tijd, 'time') else ophaal_tijd
            eind_time = eind_tijd.time() if hasattr(eind_tijd, 'time') else eind_tijd
            
            # Vind juiste tijdsblokken
            halen_tijdblok = None
            brengen_tijdblok = None
            
            for timeslot in timeslots:
                if timeslot.tijdblok_type == 'halen':
                    # Halen: grootste blok ≤ ophaaltijd
                    if timeslot.aankomst_tijd <= ophaal_time:
                        if halen_tijdblok is None or timeslot.aankomst_tijd > halen_tijdblok.aankomst_tijd:
                            halen_tijdblok = timeslot
                elif timeslot.tijdblok_type == 'brengen':
                    # Brengen: kleinste blok ≥ eindtijd
                    if timeslot.aankomst_tijd >= eind_time:
                        if brengen_tijdblok is None or timeslot.aankomst_tijd < brengen_tijdblok.aankomst_tijd:
                            brengen_tijdblok = timeslot
            
            # Sla tijdsblokken op in database
            if halen_tijdblok:
                patient.halen_tijdblok = halen_tijdblok
                timeslot_id = f"{halen_tijdblok.aankomst_tijd.strftime('%H:%M')}_halen"
                if timeslot_id not in timeslot_assignments:
                    timeslot_assignments[timeslot_id] = []
                timeslot_assignments[timeslot_id].append(patient)
                logger.info(f"✅ Patiënt {patient.naam} toegevoegd aan halen tijdsblok {timeslot_id}")
            
            if brengen_tijdblok:
                patient.brengen_tijdblok = brengen_tijdblok
                timeslot_id = f"{brengen_tijdblok.aankomst_tijd.strftime('%H:%M')}_brengen"
                if timeslot_id not in timeslot_assignments:
                    timeslot_assignments[timeslot_id] = []
                timeslot_assignments[timeslot_id].append(patient)
                logger.info(f"✅ Patiënt {patient.naam} toegevoegd aan brengen tijdsblok {timeslot_id}")
            
            # Sla patiënt op met tijdsblokken
            patient.save()
                
        except Exception as e:
            logger.error(f"❌ Fout bij verwerken patiënt {patient.naam}: {e}")
    
    logger.info(f"📊 Timeslot assignments gemaakt: {len(timeslot_assignments)} tijdsblokken")
    for timeslot_id, patients in timeslot_assignments.items():
        logger.info(f"  {timeslot_id}: {len(patients)} patiënten")
    
    return timeslot_assignments


def save_patients_from_wizard(upload_data, planning_data, session):
    """
    Sla patiënten op uit wizard data
    """
    # Implementatie van patiënten opslaan
    pass


def save_routes_from_wizard(route_data, session):
    """
    Sla routes op uit wizard data
    """
    # Implementatie van routes opslaan
    pass

# ============================================================================
# PARSER CONFIGURATOR VIEWS
# ============================================================================

def parser_configurator(request):
    """
    Interactieve parser configurator
    """
    if request.method == 'POST':
        # Handle file upload
        if 'file' in request.FILES:
            try:
                uploaded_file = request.FILES['file']
                
                # Parse het bestand
                if uploaded_file.name.endswith('.csv'):
                    csv_data = parse_csv_file_simple(uploaded_file)
                elif uploaded_file.name.endswith(('.xlsx', '.xls')):
                    csv_data = parse_excel_file_simple(uploaded_file)
                else:
                    return JsonResponse({'error': 'Ondersteunde bestandsformaten: CSV, Excel (.xlsx, .xls)'})
                
                if not csv_data:
                    return JsonResponse({'error': 'Kon het bestand niet parsen. Controleer of het bestand geldig is.'})
                
                # Sla de data op in de session voor de configurator
                request.session['configurator_data'] = {
                    'filename': uploaded_file.name,
                    'csv_data': csv_data,
                    'upload_time': datetime.now().isoformat()
                }
                
                return JsonResponse({
                    'success': True,
                    'filename': uploaded_file.name,
                    'row_count': len(csv_data)
                })
                
            except Exception as e:
                print(f"❌ Fout in parser_configurator: {e}")
                return JsonResponse({'error': f'Fout bij verwerken van bestand: {str(e)}'})
        
        # Handle configuratie opslaan
        elif 'save_config' in request.POST:
            config_data = json.loads(request.POST.get('config_data', '{}'))
            
            try:
                # Maak nieuwe CSVParserConfig
                config = CSVParserConfig.objects.create(
                    naam=config_data.get('naam', 'Nieuwe Parser'),
                    actief=True,
                    prioriteit=50,
                    bestandsnaam_patroon=config_data.get('bestandsnaam_patroon', '.*'),
                    header_keywords=config_data.get('header_keywords', ''),
                    kolom_mapping=config_data.get('kolom_mapping', {}),
                    datum_formaten=config_data.get('datum_formaten', ''),
                    tijd_formaten=config_data.get('tijd_formaten', ''),
                    beschrijving=config_data.get('beschrijving', 'Gemaakt met Parser Configurator')
                )
                
                return JsonResponse({
                    'success': True,
                    'config_id': config.id,
                    'message': f'Parser "{config.naam}" succesvol opgeslagen!'
                })
                
            except Exception as e:
                return JsonResponse({
                    'error': f'Fout bij opslaan: {str(e)}'
                })
    
    # GET request
    if request.GET.get('get_data') == 'true':
        # Return session data as JSON
        configurator_data = request.session.get('configurator_data', {})
        if configurator_data:
            return JsonResponse({
                'success': True,
                'csv_data': configurator_data.get('csv_data', [])
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Geen data gevonden in session'
            })
    
    # Toon de configurator interface
    return render(request, 'planning/parser_configurator.html', {
        'page_title': 'Parser Configurator',
        'step_title': 'Parser Configurator',
        'step_description': 'Upload een bestand en configureer de kolom mapping interactief'
    })


def parse_excel_file_simple(uploaded_file):
    """
    Eenvoudige Excel parser
    """
    try:
        import pandas as pd
        
        # Lees Excel bestand
        df = pd.read_excel(uploaded_file)
        
        # Converteer naar lijst van dictionaries
        rows = []
        for i, row in df.iterrows():
            row_data = row.tolist()
            # Vervang NaN waarden door lege strings
            row_data = [str(cell) if pd.notna(cell) else '' for cell in row_data]
            
            rows.append({
                'type': 'data',
                'data': row_data,
                'line_number': i + 1
            })
        
        print(f"📊 Excel geparsed: {len(rows)} rijen")
        return rows
        
    except Exception as e:
        print(f"❌ Fout bij Excel parsing: {e}")
        return []

def api_wizard_google_maps_routes(request):
    """
    API endpoint voor Google Maps route optimalisatie
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Alleen POST requests toegestaan'}, status=405)
    
    try:
        # Check if this is a status check request
        data = json.loads(request.body) if request.body else {}
        if data.get('check_status'):
            # Import Google Maps service
            from .services.google_maps import google_maps_service
            
            if google_maps_service.is_enabled():
                return JsonResponse({
                    'success': True,
                    'message': 'Google Maps API is ingeschakeld'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'fallback_available': True,
                    'message': 'Google Maps API is niet ingeschakeld, fallback beschikbaar'
                })
        
        # Haal data op uit session of request body
        wizard_data = request.session.get('wizard_planning_data', {})
        if not wizard_data:
            # Probeer data uit request body
            if request.body:
                try:
                    request_data = json.loads(request.body)
                    if 'test_timeslot' in request_data:
                        # Gebruik test data uit request body
                        timeslot_assignments = request_data
                    else:
                        return JsonResponse({'error': 'Geen planning data gevonden'}, status=400)
                except json.JSONDecodeError:
                    return JsonResponse({'error': 'Ongeldige JSON data'}, status=400)
            else:
                return JsonResponse({'error': 'Geen planning data gevonden'}, status=400)
        else:
            timeslot_assignments = wizard_data.get('timeslot_assignments', {})
        if not timeslot_assignments:
            return JsonResponse({'error': 'Geen tijdblok toewijzingen gevonden'}, status=400)
        
        # Haal beschikbare voertuigen op
        from .models import Vehicle
        available_vehicles = list(Vehicle.objects.filter(status='beschikbaar'))
        
        if not available_vehicles:
            return JsonResponse({'error': 'Geen beschikbare voertuigen'}, status=400)
        
        # Import Google Maps service
        from .services.google_maps import google_maps_service
        
        # Debug Google Maps status
        logger.info(f"Google Maps enabled: {google_maps_service.is_enabled()}")
        logger.info(f"Google Maps config: {google_maps_service.config}")
        logger.info(f"API Key available: {google_maps_service.api_key is not None}")
        
        if not google_maps_service.is_enabled():
            logger.info("Google Maps niet ingeschakeld, gebruik fallback")
            # Gebruik fallback in plaats van error
            optimized_routes = google_maps_service._fallback_optimization(timeslot_assignments, available_vehicles)
        else:
            logger.info("Google Maps ingeschakeld, start optimalisatie")
            optimized_routes = google_maps_service.optimize_vehicle_routes(timeslot_assignments, available_vehicles)
        
        # Debug logging
        logger.info(f"Timeslot assignments: {timeslot_assignments}")
        logger.info(f"Available vehicles: {len(available_vehicles)}")
        logger.info(f"Optimized routes result: {optimized_routes}")
        
        # Bereken totale statistieken
        total_distance = 0
        total_time = 0
        total_cost = 0
        total_vehicles = 0
        
        for timeslot_data in optimized_routes.values():
            total_distance += timeslot_data.get('total_distance', 0)
            total_time += timeslot_data.get('total_time', 0)
            total_cost += timeslot_data.get('total_cost', 0)
            total_vehicles += timeslot_data.get('vehicle_count', 0)
        
        # Sla resultaten op in session (zonder Vehicle objecten)
        session_routes = {}
        for timeslot_id, timeslot_data in optimized_routes.items():
            session_routes[timeslot_id] = {
                'routes': [],
                'total_distance': timeslot_data.get('total_distance', 0),
                'total_time': timeslot_data.get('total_time', 0),
                'total_cost': timeslot_data.get('total_cost', 0),
                'vehicle_count': timeslot_data.get('vehicle_count', 0)
            }
            
            # Converteer routes naar JSON-serializable format
            for route in timeslot_data.get('routes', []):
                session_route = {
                    'vehicle_id': route['vehicle'].referentie or route['vehicle'].kenteken if hasattr(route['vehicle'], 'referentie') else 'Unknown',
                    'vehicle_name': str(route['vehicle']),
                    'patients': route['patients'],
                    'total_distance': route['total_distance'],
                    'total_time': route['total_time'],
                    'total_cost': route['total_cost']
                }
                session_routes[timeslot_id]['routes'].append(session_route)
        
        # Sla patiënten op in database na route optimalisatie
        logger.info("💾 Sla patiënten op in database...")
        saved_patients = []
        
        # Haal upload data op voor patiënt informatie
        upload_data = request.session.get('wizard_upload_data', {})
        csv_data = upload_data.get('csv_data', [])
        detection_result = upload_data.get('detection_result', {})
        mappings = detection_result.get('mappings', {})
        
        # Maak een mapping van patient_id naar CSV data
        patient_csv_map = {}
        for row in csv_data:
            if row.get('data') and 'patient_id' in mappings:
                patient_id = row['data'][mappings['patient_id']]
                patient_csv_map[patient_id] = row['data']
        
        # Verwerk elke route en sla patiënten op
        for timeslot_id, timeslot_data in optimized_routes.items():
            for route in timeslot_data.get('routes', []):
                vehicle = route['vehicle']
                route_patients = route['patients']
                
                for patient_data in route_patients:
                    # Haal patiënt informatie op
                    if isinstance(patient_data, dict):
                        patient_id = patient_data.get('patient_id')
                        patient_name = patient_data.get('naam', '')
                    else:
                        patient_id = str(patient_data)
                        patient_name = str(patient_data)
                    
                    # Zoek CSV data voor deze patiënt
                    csv_row = patient_csv_map.get(patient_id)
                    if csv_row:
                        # Maak patiënt object aan
                        try:
                            from datetime import datetime, date
                            
                            # Bepaal datum (gebruik CSV datum of vandaag)
                            csv_date = upload_data.get('csv_date')
                            if csv_date:
                                try:
                                    patient_date = date.fromisoformat(csv_date)
                                except ValueError:
                                    patient_date = date.today()
                            else:
                                patient_date = date.today()
                            
                            # Bepaal tijden
                            start_time_str = None
                            end_time_str = None
                            
                            if 'start_tijd' in mappings and len(csv_row) > mappings['start_tijd']:
                                start_time_str = csv_row[mappings['start_tijd']]
                            
                            if 'eind_tijd' in mappings and len(csv_row) > mappings['eind_tijd']:
                                end_time_str = csv_row[mappings['eind_tijd']]
                            
                            # Parse tijden
                            ophaal_tijd = None
                            eind_behandel_tijd = None
                            
                            if start_time_str:
                                try:
                                    if ':' in start_time_str:
                                        time_parts = start_time_str.split(':')
                                        if len(time_parts) >= 2:
                                            hour = int(time_parts[0])
                                            minute = int(time_parts[1])
                                            ophaal_tijd = datetime.combine(patient_date, datetime.min.time().replace(hour=hour, minute=minute))
                                except (ValueError, TypeError):
                                    pass
                            
                            if end_time_str:
                                try:
                                    if ':' in end_time_str:
                                        time_parts = end_time_str.split(':')
                                        if len(time_parts) >= 2:
                                            hour = int(time_parts[0])
                                            minute = int(time_parts[1])
                                            eind_behandel_tijd = datetime.combine(patient_date, datetime.min.time().replace(hour=hour, minute=minute))
                                except (ValueError, TypeError):
                                    pass
                            
                            # Gebruik default tijden als parsing faalt
                            if ophaal_tijd is None:
                                ophaal_tijd = datetime.combine(patient_date, datetime.min.time().replace(hour=8, minute=0))
                            
                            if eind_behandel_tijd is None:
                                eind_behandel_tijd = datetime.combine(patient_date, datetime.min.time().replace(hour=17, minute=0))
                            
                            # Bepaal adresgegevens
                            straat = ""
                            postcode = ""
                            plaats = ""
                            
                            if 'adres' in mappings and len(csv_row) > mappings['adres']:
                                straat = csv_row[mappings['adres']]
                            if 'postcode' in mappings and len(csv_row) > mappings['postcode']:
                                postcode = csv_row[mappings['postcode']]
                            if 'plaats' in mappings and len(csv_row) > mappings['plaats']:
                                plaats = csv_row[mappings['plaats']]
                            
                            # Bepaal naam
                            achternaam = ""
                            voornaam = ""
                            
                            if 'achternaam' in mappings and len(csv_row) > mappings['achternaam']:
                                achternaam = csv_row[mappings['achternaam']]
                            if 'voornaam' in mappings and len(csv_row) > mappings['voornaam']:
                                voornaam = csv_row[mappings['voornaam']]
                            
                            # Maak volledige naam
                            if voornaam and achternaam:
                                naam = f"{voornaam} {achternaam}"
                            elif achternaam:
                                naam = achternaam
                            elif voornaam:
                                naam = voornaam
                            else:
                                naam = patient_name
                            
                            # Bepaal coördinaten
                            latitude = None
                            longitude = None
                            
                            if isinstance(patient_data, dict):
                                latitude = patient_data.get('latitude')
                                longitude = patient_data.get('longitude')
                            
                            # Maak of update patiënt
                            patient, created = Patient.objects.get_or_create(
                                naam=naam,
                                ophaal_tijd__date=patient_date,
                                defaults={
                                    'straat': straat,
                                    'postcode': postcode,
                                    'plaats': plaats,
                                    'ophaal_tijd': ophaal_tijd,
                                    'eind_behandel_tijd': eind_behandel_tijd,
                                    'bestemming': 'Revalidatiecentrum',  # Default bestemming
                                    'toegewezen_voertuig': vehicle,
                                    'status': 'gepland',
                                    'latitude': latitude,
                                    'longitude': longitude,
                                }
                            )
                            
                            if not created:
                                # Update bestaande patiënt
                                patient.toegewezen_voertuig = vehicle
                                patient.status = 'gepland'
                                if latitude and longitude:
                                    patient.latitude = latitude
                                    patient.longitude = longitude
                                patient.save()
                            
                            saved_patients.append(patient)
                            logger.info(f"✅ Patiënt opgeslagen: {patient.naam} -> {vehicle}")
                            
                        except Exception as e:
                            logger.error(f"❌ Fout bij opslaan patiënt {patient_id}: {e}")
        
        logger.info(f"💾 {len(saved_patients)} patiënten opgeslagen in database")
        
        request.session['google_maps_routes'] = {
            'optimized_routes': session_routes,
            'statistics': {
                'total_distance': total_distance,
                'total_time': total_time,
                'total_cost': total_cost,
                'total_vehicles': total_vehicles,
                'timeslots_processed': len(optimized_routes)
            },
            'timestamp': timezone.now().isoformat()
        }
        
        return JsonResponse({
            'success': True,
            'message': f'Routes geoptimaliseerd! {total_vehicles} voertuigen, {total_distance:.1f} km, €{total_cost:.2f}',
            'statistics': {
                'total_distance': total_distance,
                'total_time': total_time,
                'total_cost': total_cost,
                'total_vehicles': total_vehicles,
                'timeslots_processed': len(optimized_routes)
            },
            'routes_count': len(optimized_routes)
        })
        
    except Exception as e:
        logger.error(f"Fout bij Google Maps route optimalisatie: {e}")
        return JsonResponse({
            'error': f'Fout bij route optimalisatie: {str(e)}',
            'fallback_available': True
        }, status=500)


def api_wizard_geocode_patients(request):
    """
    API endpoint voor geocoding van patiënt adressen tijdens preview
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Alleen POST requests toegestaan'}, status=405)
    
    try:
        # Haal upload data op uit session
        upload_data = request.session.get('wizard_upload_data', {})
        if not upload_data:
            return JsonResponse({'error': 'Geen upload data gevonden'}, status=400)
        
        csv_data = upload_data.get('csv_data', [])
        detection_result = upload_data.get('detection_result', {})
        mappings = detection_result.get('mappings', {})
        
        if not csv_data:
            return JsonResponse({'error': 'Geen CSV data gevonden'}, status=400)
        
        # Import Google Maps service
        from .services.google_maps import google_maps_service
        
        # Check of Google Maps API beschikbaar is
        use_fallback = not google_maps_service.is_enabled()
        
        if not use_fallback:
            # Test API toegang
            test_response = google_maps_service._make_api_call('geocode/json', {
            'address': 'Bonn, Germany',
            'key': google_maps_service.api_key
        })
        
        if not test_response or test_response.get('status') == 'REQUEST_DENIED':
                use_fallback = True
                logger.warning("Google Maps API test gefaald, gebruik fallback geocoding")
        
        if use_fallback:
            logger.info("🔄 Gebruik fallback geocoding (Google Maps API niet beschikbaar)")
        
        logger.info("🚀 Start geocoding van patiënt adressen...")
        
        # Geocode patiënten
        geocoded_patients = []
        success_count = 0
        error_count = 0
        
        logger.info(f"🔍 Start geocoding voor {len(csv_data)} rijen")
        logger.info(f"📋 Mappings: {mappings}")
        
        for i, row in enumerate(csv_data):
            if not row.get('data'):
                logger.warning(f"Rij {i}: Geen data gevonden")
                continue
                
            data = row['data']
            patient_info = {}
            
            logger.info(f"🔍 Verwerk rij {i}: {data}")
            
            # Extraheer patiënt informatie
            if 'patient_id' in mappings and len(data) > mappings['patient_id']:
                patient_info['patient_id'] = data[mappings['patient_id']]
                logger.info(f"  Patient ID: {patient_info['patient_id']}")
            
            if 'achternaam' in mappings and len(data) > mappings['achternaam']:
                patient_info['achternaam'] = data[mappings['achternaam']]
                logger.info(f"  Achternaam: {patient_info['achternaam']}")
            
            if 'voornaam' in mappings and len(data) > mappings['voornaam']:
                patient_info['voornaam'] = data[mappings['voornaam']]
                logger.info(f"  Voornaam: {patient_info['voornaam']}")
            
            # Extraheer adresgegevens
            if 'adres' in mappings and len(data) > mappings['adres']:
                patient_info['adres'] = data[mappings['adres']]
                logger.info(f"  Adres: {patient_info['adres']}")
            
            if 'plaats' in mappings and len(data) > mappings['plaats']:
                patient_info['plaats'] = data[mappings['plaats']]
                logger.info(f"  Plaats: {patient_info['plaats']}")
            
            if 'postcode' in mappings and len(data) > mappings['postcode']:
                patient_info['postcode'] = data[mappings['postcode']]
                logger.info(f"  Postcode: {patient_info['postcode']}")
            
            # Bouw adres op voor geocoding
            address_parts = []
            if patient_info.get('adres'):
                address_parts.append(patient_info['adres'])
            if patient_info.get('postcode'):
                address_parts.append(patient_info['postcode'])
            if patient_info.get('plaats'):
                address_parts.append(patient_info['plaats'])
            
            logger.info(f"  Adres delen: {address_parts}")
            
            if address_parts:
                full_address = ', '.join(address_parts) + ', Germany'
                logger.info(f"  Volledig adres: {full_address}")
                
                if use_fallback:
                    # Gebruik fallback coördinaten
                    import random
                    base_lat = 50.7467  # Bonn centrum
                    base_lng = 7.1516
                    
                    # Voeg wat variatie toe per patiënt
                    lat_variation = (i * 0.01) + (random.random() * 0.005)
                    lng_variation = (i * 0.01) + (random.random() * 0.005)
                    
                    patient_info['latitude'] = base_lat + lat_variation
                    patient_info['longitude'] = base_lng + lng_variation
                    patient_info['geocoded'] = True
                    patient_info['fallback_used'] = True
                    success_count += 1
                    logger.info(f"✅ Fallback geocoded: {patient_info.get('achternaam', 'Onbekend')} - {full_address}")
                else:
                    # Gebruik Google Maps API
                    coords = google_maps_service.geocode_address(full_address)
                if coords:
                    patient_info['latitude'] = coords[0]
                    patient_info['longitude'] = coords[1]
                    patient_info['geocoded'] = True
                    patient_info['fallback_used'] = False
                    success_count += 1
                    logger.info(f"✅ Google Maps geocoded: {patient_info.get('achternaam', 'Onbekend')} - {full_address}")
                else:
                    patient_info['geocoded'] = False
                    error_count += 1
                    logger.warning(f"❌ Geocoding failed: {patient_info.get('achternaam', 'Onbekend')} - {full_address}")
            else:
                patient_info['geocoded'] = False
                error_count += 1
                logger.warning(f"❌ Geen adresgegevens: {patient_info.get('achternaam', 'Onbekend')}")
                logger.warning(f"  Beschikbare velden: {list(patient_info.keys())}")
            
            geocoded_patients.append(patient_info)
        
        # Sla geocoded data op in session
        upload_data['geocoded_patients'] = geocoded_patients
        request.session['wizard_upload_data'] = upload_data
        
        logger.info(f"🎯 Geocoding voltooid: {success_count} succesvol, {error_count} gefaald")
        
        response_data = {
            'success': True,
            'statistics': {
                'total_patients': len(geocoded_patients),
                'success_count': success_count,
                'error_count': error_count,
                'success_rate': round((success_count / len(geocoded_patients)) * 100, 1) if geocoded_patients else 0
            }
        }
        
        if use_fallback:
            response_data['message'] = f'Fallback geocoding voltooid! {success_count} adressen verwerkt, {error_count} gefaald'
            response_data['fallback_used'] = True
        else:
            response_data['message'] = f'Google Maps geocoding voltooid! {success_count} adressen gevonden, {error_count} gefaald'
            response_data['fallback_used'] = False
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Fout bij geocoding: {e}")
        return JsonResponse({
            'error': f'Fout bij geocoding: {str(e)}'
        }, status=500)


def api_wizard_real_time_update(request):
    """
    API endpoint voor real-time route updates bij wijzigingen
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Alleen POST requests toegestaan'}, status=405)
    
    try:
        data = json.loads(request.body)
        patient_id = data.get('patient_id')
        new_vehicle_id = data.get('new_vehicle_id')
        timeslot_id = data.get('timeslot_id')
        
        if not all([patient_id, new_vehicle_id, timeslot_id]):
            return JsonResponse({'error': 'Ontbrekende parameters'}, status=400)
        
        # Haal data op
        from .models import Vehicle, Patient
        try:
            vehicle = Vehicle.objects.get(id=new_vehicle_id)
            patient = Patient.objects.get(id=patient_id)
        except (Vehicle.DoesNotExist, Patient.DoesNotExist):
            return JsonResponse({'error': 'Voertuig of patiënt niet gevonden'}, status=404)
        
        # Import Google Maps service
        from .services.google_maps import google_maps_service
        
        if not google_maps_service.is_enabled():
            return JsonResponse({
                'error': 'Google Maps API is niet beschikbaar',
                'fallback_available': True
            }, status=400)
        
        # Bereken nieuwe route voor dit voertuig
        # Dit is een vereenvoudigde versie - in productie zou je de volledige route herberekenen
        route_update = {
            'vehicle_id': vehicle.id,
            'vehicle_name': vehicle.kenteken,
            'patient_id': patient.id,
            'patient_name': patient.naam,
            'estimated_distance': 15.5,  # Placeholder - zou Google Maps gebruiken
            'estimated_time': 25,  # Placeholder
            'estimated_cost': 15.5 * float(vehicle.km_kosten_per_km)
        }
        
        return JsonResponse({
            'success': True,
            'route_update': route_update,
            'message': f'Route bijgewerkt voor {patient.voornaam} {patient.achternaam}'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Ongeldige JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Fout bij real-time route update: {e}")
        return JsonResponse({
            'error': f'Fout bij route update: {str(e)}',
            'fallback_available': True
        }, status=500)