from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.home, name='home'),
    path('patients/today/', views.patients_today, name='patients_today'),
    
    # Planning (direct naar route results)
    path('planning/', views.route_results, name='planning_overview'),  # Redirect naar route results
    path('planning/new/', views.new_planning, name='new_planning'),
    path('planning/step2/', views.planning_step2, name='planning_step2'),
    path('planning/step3/', views.planning_step3, name='planning_step3'),
    path('planning/concept/', views.concept_planning, name='concept_planning'),
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
]
