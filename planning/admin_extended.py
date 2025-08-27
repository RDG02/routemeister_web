from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models_extended import (
    CSVImportLog, PlanningSession, PlanningAction, 
    NotificationSettings, MobileAppNotification
)


@admin.register(CSVImportLog)
class CSVImportLogAdmin(admin.ModelAdmin):
    list_display = ['filename', 'imported_by', 'import_date', 'status', 'total_patients', 'imported_patients']
    list_filter = ['status', 'import_date', 'imported_by']
    search_fields = ['filename', 'imported_by__username']
    readonly_fields = ['import_date', 'total_patients', 'imported_patients']
    ordering = ['-import_date']
    
    fieldsets = (
        ('Import Details', {
            'fields': ('filename', 'imported_by', 'import_date', 'status')
        }),
        ('Patient Statistics', {
            'fields': ('total_patients', 'imported_patients', 'errors')
        }),
        ('CSV Content (Audit)', {
            'fields': ('csv_content',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        return False  # CSV logs worden alleen automatisch aangemaakt


@admin.register(PlanningSession)
class PlanningSessionAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'planning_date', 'status', 'total_routes', 'total_patients', 'total_cost_display']
    list_filter = ['status', 'planning_date', 'created_by', 'created_at']
    search_fields = ['name', 'created_by__username', 'description']
    readonly_fields = ['created_at', 'updated_at', 'total_routes', 'total_patients', 'total_distance', 'total_cost', 'total_time']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'created_by', 'planning_date', 'status', 'description')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Planning Data', {
            'fields': ('selected_vehicles', 'selected_timeslots', 'routes_data')
        }),
        ('Statistics', {
            'fields': ('total_routes', 'total_patients', 'total_distance', 'total_cost', 'total_time')
        }),
    )
    
    def total_cost_display(self, obj):
        return f"€{obj.total_cost:.2f}"
    total_cost_display.short_description = 'Total Cost'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')


@admin.register(PlanningAction)
class PlanningActionAdmin(admin.ModelAdmin):
    list_display = ['user', 'action_type', 'planning_session', 'timestamp', 'description_short']
    list_filter = ['action_type', 'timestamp', 'user', 'planning_session']
    search_fields = ['user__username', 'description', 'planning_session__name']
    readonly_fields = ['timestamp', 'details_formatted']
    ordering = ['-timestamp']
    
    fieldsets = (
        ('Action Details', {
            'fields': ('planning_session', 'user', 'action_type', 'timestamp', 'description')
        }),
        ('Action Details (JSON)', {
            'fields': ('details_formatted',),
            'classes': ('collapse',)
        }),
    )
    
    def description_short(self, obj):
        return obj.description[:100] + '...' if len(obj.description) > 100 else obj.description
    description_short.short_description = 'Description'
    
    def details_formatted(self, obj):
        import json
        return format_html('<pre>{}</pre>', json.dumps(obj.details, indent=2))
    details_formatted.short_description = 'Details (Formatted)'
    
    def has_add_permission(self, request):
        return False  # Actions worden alleen automatisch aangemaakt
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'planning_session')


@admin.register(NotificationSettings)
class NotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ['notification_type', 'enabled', 'email_recipients', 'days_ahead', 'time_of_day', 'last_sent']
    list_filter = ['notification_type', 'enabled', 'days_ahead']
    search_fields = ['email_recipients', 'notification_type']
    ordering = ['notification_type']
    
    fieldsets = (
        ('Notification Configuration', {
            'fields': ('notification_type', 'enabled', 'email_recipients')
        }),
        ('Timing', {
            'fields': ('days_ahead', 'time_of_day', 'last_sent')
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing existing object
            return ['last_sent']
        return []


@admin.register(MobileAppNotification)
class MobileAppNotificationAdmin(admin.ModelAdmin):
    list_display = ['vehicle', 'driver', 'notification_type', 'status', 'sent_at', 'delivered_at']
    list_filter = ['status', 'notification_type', 'sent_at', 'vehicle']
    search_fields = ['vehicle__kenteken', 'driver__username', 'message']
    readonly_fields = ['sent_at', 'delivered_at']
    ordering = ['-sent_at']
    
    fieldsets = (
        ('Notification Details', {
            'fields': ('planning_session', 'vehicle', 'driver', 'notification_type', 'message', 'status')
        }),
        ('Timestamps', {
            'fields': ('sent_at', 'delivered_at')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('vehicle', 'driver', 'planning_session')
