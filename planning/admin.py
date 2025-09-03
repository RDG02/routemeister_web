from django.contrib import admin
from django.urls import path, reverse
from django.utils.html import format_html
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Patient, Vehicle, UserProfile, TimeSlot, Configuration, Location
from .models_extended import CSVImportLog, PlanningSession, PlanningAction, NotificationSettings, MobileAppNotification
from .widgets import ColorPickerWidget
from .models import CSVParserConfig
from .models import PlanningConstraint
from .models import GoogleMapsConfig, GoogleMapsAPILog

# Register your models here.

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['naam', 'plaats', 'ophaal_tijd', 'status', 'mobile_status', 'toegewezen_tijdblok', 'toegewezen_voertuig']
    list_filter = ['status', 'mobile_status', 'plaats', 'ophaal_tijd', 'toegewezen_tijdblok']
    search_fields = ['naam', 'telefoonnummer', 'plaats']
    date_hierarchy = 'ophaal_tijd'
    
    fieldsets = (
        ('Basis Informatie', {
            'fields': ('naam', 'telefoonnummer', 'straat', 'postcode', 'plaats')
        }),
        ('Transport Details', {
            'fields': ('ophaal_tijd', 'eind_behandel_tijd', 'bestemming')
        }),
        ('Planning', {
            'fields': ('halen_tijdblok', 'bringen_tijdblok', 'toegewezen_voertuig')
        }),
        ('Status', {
            'fields': ('status', 'mobile_status', 'mobile_notification_sent')
        }),
        ('GPS & Geocoding', {
            'fields': ('latitude', 'longitude', 'geocoding_status', 'geocoding_notes')
        }),
    )
    
@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ['referentie', 'kenteken', 'merk_model', 'kleur_preview', 'aantal_zitplaatsen', 'speciale_zitplaatsen', 'km_kosten_per_km', 'status']
    list_filter = ['status']
    search_fields = ['referentie', 'kenteken', 'merk_model']
    
    fieldsets = (
        ('Basis Informatie', {
            'fields': ('referentie', 'kenteken', 'merk_model', 'foto')
        }),
        ('Capaciteit', {
            'fields': ('aantal_zitplaatsen', 'speciale_zitplaatsen')
        }),
        ('Kosten en Tijden', {
            'fields': ('km_kosten_per_km', 'maximale_rit_tijd')
        }),
        ('Visuele Eigenschappen', {
            'fields': ('kleur',)
        }),
        ('Status', {
            'fields': ('status',)
        }),
    )
    
    formfield_overrides = {
        'kleur': {'widget': ColorPickerWidget},
    }
    
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'kleur':
            kwargs['widget'] = ColorPickerWidget()
        return super().formfield_for_dbfield(db_field, request, **kwargs)
    
    def kleur_preview(self, obj):
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #ccc; border-radius: 3px; display: inline-block;"></div>',
            obj.kleur
        )
    kleur_preview.short_description = 'Kleur'

@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ['naam', 'tijdblok_type', 'aankomst_tijd', 'actief', 'default_selected', 'dag_van_week']
    list_filter = ['tijdblok_type', 'actief', 'default_selected', 'dag_van_week']
    search_fields = ['naam']
    
    fieldsets = (
        ('Basis Informatie', {
            'fields': ('naam', 'tijdblok_type')
        }),
        ('Tijdsblokken', {
            'fields': ('aankomst_tijd',),
            'description': 'Tijd van aankomst reha center (halen) of eind tijd voor brengen (brengen)'
        }),
        ('Beperkingen', {
            'fields': ('max_rijtijd_minuten',),
            'description': 'Maximale rijtijd in minuten (deze tijd is ook al aan voertuigen gekoppeld, zie max reistijd bij voertuigen)'
        }),
        ('Planning', {
            'fields': ('actief', 'default_selected', 'dag_van_week'),
            'description': 'Stel in welke tijdblokken standaard geselecteerd zijn op de planning pagina.'
        }),
    )

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'rol', 'toegewezen_voertuig']
    list_filter = ['rol']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']


@admin.register(Configuration)
class ConfigurationAdmin(admin.ModelAdmin):
    """
    Admin interface voor systeem configuratie
    """
    list_display = ['key', 'value', 'is_active', 'updated_at']
    list_filter = ['is_active', 'created_at', 'updated_at']
    search_fields = ['key', 'value', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basis Configuratie', {
            'fields': ('key', 'value', 'description', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Toon alleen actieve configuraties standaard"""
        return super().get_queryset(request)
    
    def save_model(self, request, obj, form, change):
        """Log wijzigingen in configuratie"""
        if change:
            # Log de wijziging
            from django.contrib.admin.models import LogEntry, CHANGE
            from django.contrib.contenttypes.models import ContentType
            
            content_type = ContentType.objects.get_for_model(self.model)
            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=content_type.id,
                object_id=obj.pk,
                object_repr=str(obj),
                action_flag=CHANGE,
                change_message=f"Configuratie gewijzigd: {obj.key}"
            )
        super().save_model(request, obj, form, change)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    """
    Admin interface voor locaties
    """
    list_display = ['name', 'location_type', 'latitude', 'longitude', 'is_active', 'is_default', 'updated_at']
    list_filter = ['location_type', 'is_active', 'is_default', 'created_at', 'updated_at']
    search_fields = ['name', 'address', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basis Informatie', {
            'fields': ('name', 'location_type', 'description')
        }),
        ('Adres & Geocoding', {
            'fields': ('address',),
            'description': 'Vul het adres in en klik op "Geolocate" om automatisch coördinaten te genereren.'
        }),
        ('Coördinaten', {
            'fields': ('latitude', 'longitude'),
            'description': 'Coördinaten worden automatisch gegenereerd. Je kunt ze ook handmatig aanpassen.'
        }),
        ('Status', {
            'fields': ('is_active', 'is_default')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    class Media:
        css = {
            'all': ('admin/css/location_admin.css',)
        }
        js = ('admin/js/location_admin.js',)
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('geolocate/', self.admin_site.admin_view(self.geolocate_view), name='location_geolocate'),
        ]
        return custom_urls + urls
    
    @method_decorator(csrf_exempt)
    def geolocate_view(self, request):
        """AJAX endpoint voor geocoding"""
        if request.method == 'POST':
            address = request.POST.get('address', '')
            if address:
                # Maak een tijdelijke locatie voor geocoding
                temp_location = Location(address=address)
                if temp_location.geocode_address():
                    return JsonResponse({
                        'success': True,
                        'latitude': float(temp_location.latitude),
                        'longitude': float(temp_location.longitude)
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': 'Adres niet gevonden'
                    })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Geen adres opgegeven'
                })
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    def get_queryset(self, request):
        """Toon alleen actieve locaties standaard"""
        return super().get_queryset(request)
    
    actions = ['geocode_selected_locations']
    
    def geocode_selected_locations(self, request, queryset):
        """Geocode geselecteerde locaties op basis van hun adres"""
        success_count = 0
        failed_count = 0
        
        for location in queryset:
            if location.address:
                if location.geocode_address():
                    location.save()
                    success_count += 1
                else:
                    failed_count += 1
        
        if success_count > 0:
            self.message_user(request, f'{success_count} locatie(s) succesvol geocoded.')
        if failed_count > 0:
            self.message_user(request, f'{failed_count} locatie(s) konden niet worden geocoded.', level='WARNING')
    
    geocode_selected_locations.short_description = "Geocode geselecteerde locaties"
    
    def save_model(self, request, obj, form, change):
        """Log wijzigingen in locatie"""
        if change:
            # Log de wijziging
            from django.contrib.admin.models import LogEntry, CHANGE
            from django.contrib.contenttypes.models import ContentType
            
            content_type = ContentType.objects.get_for_model(self.model)
            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=content_type.id,
                object_id=obj.pk,
                object_repr=str(obj),
                action_flag=CHANGE,
                change_message=f"Locatie gewijzigd: {obj.name}"
            )
        super().save_model(request, obj, form, change)


# Import extended admin classes
from .admin_extended import (
    CSVImportLogAdmin, PlanningSessionAdmin, PlanningActionAdmin,
    NotificationSettingsAdmin, MobileAppNotificationAdmin
)

@admin.register(CSVParserConfig)
class CSVParserConfigAdmin(admin.ModelAdmin):
    list_display = ['naam', 'actief', 'prioriteit', 'bestandsnaam_patroon', 'gemaakt_op', 'parser_configurator_link']
    list_filter = ['actief', 'prioriteit']
    search_fields = ['naam', 'beschrijving']
    ordering = ['-prioriteit', 'naam']
    
    fieldsets = (
        ('Basis Informatie', {
            'fields': ('naam', 'actief', 'prioriteit', 'beschrijving')
        }),
        ('Bestand Detectie', {
            'fields': ('bestandsnaam_patroon', 'header_keywords')
        }),
        ('Kolom Mapping', {
            'fields': ('kolom_mapping',),
            'description': 'JSON mapping van kolom indexen naar veldnamen'
        }),
        ('Formaten', {
            'fields': ('datum_formaten', 'tijd_formaten')
        }),
    )
    
    def parser_configurator_link(self, obj):
        url = reverse('parser_configurator')
        return format_html('<a href="{}" target="_blank">🔧 Parser Configurator</a>', url)
    parser_configurator_link.short_description = 'Configurator'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('parser-configurator/', self.admin_site.admin_view(self.parser_configurator_view), name='parser_configurator'),
        ]
        return custom_urls + urls
    
    def parser_configurator_view(self, request):
        from django.shortcuts import redirect
        return redirect('parser_configurator')

@admin.register(PlanningConstraint)
class PlanningConstraintAdmin(admin.ModelAdmin):
    list_display = ['name', 'constraint_type', 'weight', 'penalty', 'is_active']
    list_filter = ['constraint_type', 'is_active']
    search_fields = ['name', 'description']
    ordering = ['constraint_type', 'name']
    
    fieldsets = (
        ('Basis Informatie', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Constraint Instellingen', {
            'fields': ('constraint_type', 'weight', 'penalty')
        }),
        ('Parameters', {
            'fields': ('parameters',),
            'description': 'JSON parameters voor deze constraint'
        }),
    )

@admin.register(GoogleMapsConfig)
class GoogleMapsConfigAdmin(admin.ModelAdmin):
    """Admin interface voor Google Maps configuratie"""
    
    list_display = ['enabled', 'vehicle_optimization', 'distance_weight', 'time_weight', 'daily_api_limit', 'updated_at']
    list_filter = ['enabled', 'vehicle_optimization', 'real_time_updates']
    
    fieldsets = (
        ('API Configuratie', {
            'fields': ('api_key', 'enabled')
        }),
        ('Optimalisatie Gewichten', {
            'fields': ('distance_weight', 'time_weight', 'vehicle_utilization_weight'),
            'description': 'Gewichten voor route optimalisatie (totaal moet 100% zijn)'
        }),
        ('Voertuig Optimalisatie', {
            'fields': ('vehicle_optimization',)
        }),
        ('API Limieten', {
            'fields': ('daily_api_limit', 'monthly_api_limit'),
            'description': 'Dagelijkse en maandelijkse API call limieten'
        }),
        ('UI Instellingen', {
            'fields': ('show_loading_timer', 'real_time_updates')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        # Valideer dat gewichten optellen tot 100%
        total_weight = obj.distance_weight + obj.time_weight + obj.vehicle_utilization_weight
        if total_weight != 100:
            self.message_user(
                request, 
                f'Waarschuwing: Gewichten tellen op tot {total_weight}% in plaats van 100%', 
                level='WARNING'
            )
        
        super().save_model(request, obj, form, change)


@admin.register(GoogleMapsAPILog)
class GoogleMapsAPILogAdmin(admin.ModelAdmin):
    """Admin interface voor Google Maps API logs"""
    
    list_display = ['api_type', 'calls_made', 'estimated_cost', 'date']
    list_filter = ['api_type', 'date']
    readonly_fields = ['api_type', 'calls_made', 'estimated_cost', 'date', 'created_at']
    
    fieldsets = (
        ('API Call Informatie', {
            'fields': ('api_type', 'calls_made', 'estimated_cost')
        }),
        ('Periode', {
            'fields': ('date', 'created_at')
        }),
    )
    
    def has_add_permission(self, request):
        # API logs worden automatisch aangemaakt, niet handmatig
        return False
    
    def has_change_permission(self, request, obj=None):
        # API logs zijn read-only
        return False
    
    actions = ['reset_daily_logs', 'export_api_stats']
    
    def reset_daily_logs(self, request, queryset):
        """Reset dagelijkse API logs"""
        count = queryset.delete()[0]
        self.message_user(request, f'{count} API logs gereset')
    reset_daily_logs.short_description = "Reset geselecteerde API logs"
    
    def export_api_stats(self, request, queryset):
        """Export API statistieken"""
        # Implementeer export functionaliteit
        self.message_user(request, 'API statistieken export functionaliteit komt binnenkort')
    export_api_stats.short_description = "Export API statistieken"
