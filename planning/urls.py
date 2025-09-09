from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('patients/today/', views.patients_today, name='patients_today'),
    
    # Planning (direct naar route results)
    path('planning/', views.route_results, name='planning_overview'),  # Redirect naar route results
    # Oude planning URLs verwijderd - vervangen door wizard
    path('planning/concept/', views.concept_planning, name='concept_planning'),
    path('planning/new-ui/', views.planning_new, name='planning_new'),
    path('planning/processing/', views.planning_processing, name='planning_processing'),
    path('planning/results/', views.planning_results, name='planning_results'),
    path('planning/<int:planning_id>/', views.view_planning, name='view_planning'),
    
    # API endpoints for concept planning
    path('api/get-patient-coordinates/', views.api_get_patient_coordinates, name='api_get_patient_coordinates'),
    path('api/log-planning-action/', views.api_log_planning_action, name='api_log_planning_action'),
    path('api/save-concept-planning/', views.api_save_concept_planning, name='api_save_concept_planning'),
    path('api/export-planning-csv/', views.api_export_planning_csv, name='api_export_planning_csv'),
    
    # Statistieken
    path('statistics/', views.statistics_view, name='statistics'),
    
    # Voertuigen CRUD
    path('vehicles/', views.vehicles_list, name='vehicles_list'),
    path('vehicles/new/', views.vehicle_create, name='vehicle_create'),
    path('vehicles/<int:vehicle_id>/edit/', views.vehicle_edit, name='vehicle_edit'),
    path('vehicles/<int:vehicle_id>/delete/', views.vehicle_delete, name='vehicle_delete'),
    
    # Gebruikers CRUD
    path('users/', views.users_list, name='users_list'),
    path('users/new/', views.user_create, name='user_create'),
    path('users/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:user_id>/delete/', views.user_delete, name='user_delete'),
    
    # Instellingen
    path('settings/', views.settings_view, name='settings'),
    
    # Bestaande functionaliteit
    path('upload/', views.upload_csv, name='upload_csv'),
    path('tijdblokken/', views.timeslot_selection, name='timeslot_selection'),
    path('auto-assign/', views.auto_assign_patients, name='auto_assign_patients'),
    path('plan-routes/', views.plan_routes, name='plan_routes'),
    path('plan-routes-simple/', views.plan_routes_simple, name='plan_routes_simple'),
    path('plan-routes-optaplanner/', views.plan_routes_optaplanner, name='plan_routes_optaplanner'),
    path('test-optaplanner/', views.test_optaplanner_api, name='test_optaplanner_api'),
    path('optaplanner-status/', views.optaplanner_status, name='optaplanner_status'),
    path('start-optaplanner-planning/', views.start_optaplanner_planning, name='start_optaplanner_planning'),
    path('route-results/', views.route_results, name='route_results'),
    path('vehicles-overview/', views.vehicles_overview, name='vehicles_overview'),
    path('timeslots-overview/', views.timeslots_overview, name='timeslots_overview'),

    # Nieuwe Planning Wizard URLs (Geoptimaliseerd - 3 stappen)
    path('wizard/', views.planning_wizard_upload, name='planning_wizard_start'),
    path('wizard/upload/', views.planning_wizard_upload, name='planning_wizard_upload'),
    path('wizard/preview/', views.planning_wizard_preview, name='planning_wizard_preview'),
    path('wizard/assignment/', views.planning_wizard_assignment, name='planning_wizard_assignment'),
    path('wizard/routes/', views.planning_wizard_routes, name='planning_wizard_routes'),
    
    # API endpoints voor wizard
    path('api/wizard/upload/', views.api_wizard_upload, name='api_wizard_upload'),
    path('api/wizard/save-upload-data/', views.api_wizard_save_upload_data, name='api_wizard_save_upload_data'),
    path('api/wizard/constraints/', views.api_wizard_constraints, name='api_wizard_constraints'),
    path('api/wizard/auto-assign/', views.api_wizard_auto_assign, name='api_wizard_auto_assign'),
    path('api/wizard/generate-routes/', views.api_wizard_generate_routes, name='api_wizard_generate_routes'),
    path('api/generate-routes/', views.api_generate_routes, name='api_generate_routes'),
    path('api/wizard/save-planning/', views.api_wizard_save_planning, name='api_wizard_save_planning'),
    path('api/update-patient-assignment/', views.api_update_patient_assignment, name='api_update_patient_assignment'),

    # Google Maps API endpoints
    path('api/google-maps-routes/', views.api_wizard_google_maps_routes, name='api_wizard_google_maps_routes'),
    path('api/geocode-patients/', views.api_wizard_geocode_patients, name='api_wizard_geocode_patients'),
    path('api/real-time-update/', views.api_wizard_real_time_update, name='api_wizard_real_time_update'),

    # Parser Configurator
    path('parser-configurator/', views.parser_configurator, name='parser_configurator'),
]
