from django.db import models
from django.contrib.auth.models import User
from .models import Vehicle, TimeSlot, Patient


class CSVImportLog(models.Model):
    """
    Log van CSV imports voor audit trail
    """
    IMPORT_STATUS_CHOICES = [
        ('success', 'Succesvol'),
        ('partial', 'Gedeeltelijk succesvol'),
        ('failed', 'Mislukt'),
    ]
    
    filename = models.CharField(max_length=255, help_text="Naam van het geïmporteerde bestand")
    imported_by = models.ForeignKey(User, on_delete=models.CASCADE, help_text="Gebruiker die de import heeft uitgevoerd")
    import_date = models.DateTimeField(auto_now_add=True, help_text="Datum en tijd van import")
    status = models.CharField(max_length=20, choices=IMPORT_STATUS_CHOICES, help_text="Status van de import")
    total_patients = models.IntegerField(default=0, help_text="Totaal aantal patiënten in CSV")
    imported_patients = models.IntegerField(default=0, help_text="Aantal succesvol geïmporteerde patiënten")
    errors = models.TextField(blank=True, help_text="Fouten tijdens import")
    csv_content = models.TextField(help_text="Inhoud van het CSV bestand (voor audit)")
    
    class Meta:
        verbose_name = "CSV Import Log"
        verbose_name_plural = "CSV Import Logs"
        ordering = ['-import_date']
    
    def __str__(self):
        return f"{self.filename} - {self.imported_by.username} - {self.import_date.strftime('%d-%m-%Y %H:%M')}"


class PlanningSession(models.Model):
    """
    Planning sessie voor concept planning en workflow management
    """
    PLANNING_STATUS_CHOICES = [
        ('concept', 'Concept'),
        ('processing', 'Verwerking'),
        ('completed', 'Voltooid'),
        ('published', 'Gepubliceerd'),
        ('archived', 'Gearchiveerd'),
    ]
    
    name = models.CharField(max_length=200, help_text="Naam van de planning sessie")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, help_text="Planner die de sessie heeft aangemaakt")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Aanmaakdatum")
    updated_at = models.DateTimeField(auto_now=True, help_text="Laatste wijziging")
    status = models.CharField(max_length=20, choices=PLANNING_STATUS_CHOICES, default='concept', help_text="Status van de planning")
    planning_date = models.DateField(help_text="Datum waarvoor de planning geldt")
    description = models.TextField(blank=True, help_text="Beschrijving van de planning")
    
    # Planning data
    selected_vehicles = models.ManyToManyField(Vehicle, help_text="Geselecteerde voertuigen")
    selected_timeslots = models.ManyToManyField(TimeSlot, help_text="Geselecteerde tijdblokken")
    routes_data = models.JSONField(default=dict, help_text="Route data in JSON formaat")
    
    # Route constraints
    max_route_time = models.IntegerField(default=60, help_text="Maximale reistijd per route in minuten")
    use_google_maps = models.BooleanField(default=True, help_text="Gebruik Google Maps voor echte routes")
    
    # Metadata
    total_routes = models.IntegerField(default=0, help_text="Totaal aantal routes")
    total_patients = models.IntegerField(default=0, help_text="Totaal aantal patiënten")
    total_distance = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Totale afstand in km")
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Totale kosten")
    total_time = models.IntegerField(default=0, help_text="Totale tijd in minuten")
    
    # Validation results
    validation_errors = models.JSONField(default=list, help_text="Validatie fouten")
    validation_warnings = models.JSONField(default=list, help_text="Validatie waarschuwingen")
    
    class Meta:
        verbose_name = "Planning Sessie"
        verbose_name_plural = "Planning Sessies"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.planning_date} - {self.get_status_display()}"
    
    def get_total_cost(self):
        """Bereken totale kosten van alle routes"""
        total = 0
        for route in self.routes_data.get('routes', []):
            total += route.get('cost', 0)
        return total
    
    def get_total_distance(self):
        """Bereken totale afstand van alle routes"""
        total = 0
        for route in self.routes_data.get('routes', []):
            total += route.get('distance', 0)
        return total


class PlanningAction(models.Model):
    """
    Log van alle planning acties voor audit trail
    """
    ACTION_TYPES = [
        ('create', 'Planning aangemaakt'),
        ('edit', 'Planning bewerkt'),
        ('patient_add', 'Patiënt toegevoegd'),
        ('patient_remove', 'Patiënt verwijderd'),
        ('patient_move', 'Patiënt verplaatst'),
        ('vehicle_change', 'Voertuig gewijzigd'),
        ('order_change', 'Volgorde gewijzigd'),
        ('timeslot_change', 'Tijdblok gewijzigd'),
        ('approve', 'Planning goedgekeurd'),
        ('publish', 'Planning gepubliceerd'),
        ('revert', 'Wijziging teruggedraaid'),
    ]
    
    planning_session = models.ForeignKey(PlanningSession, on_delete=models.CASCADE, help_text="Planning sessie")
    user = models.ForeignKey(User, on_delete=models.CASCADE, help_text="Gebruiker die de actie heeft uitgevoerd")
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES, help_text="Type actie")
    timestamp = models.DateTimeField(auto_now_add=True, help_text="Tijdstip van de actie")
    description = models.TextField(help_text="Beschrijving van de actie")
    details = models.JSONField(default=dict, help_text="Details van de wijziging")
    
    class Meta:
        verbose_name = "Planning Actie"
        verbose_name_plural = "Planning Acties"
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_action_type_display()} - {self.timestamp.strftime('%d-%m-%Y %H:%M')}"


class NotificationSettings(models.Model):
    """
    Instellingen voor notificaties
    """
    NOTIFICATION_TYPES = [
        ('planning_ready', 'Planning klaar'),
        ('planning_not_sent', 'Planning niet naar chauffeurs gestuurd'),
        ('daily_reminder', 'Dagelijkse herinnering'),
        ('weekly_reminder', 'Wekelijkse herinnering'),
    ]
    
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, help_text="Type notificatie")
    enabled = models.BooleanField(default=True, help_text="Of deze notificatie actief is")
    email_recipients = models.TextField(help_text="Email adressen (gescheiden door komma's)")
    days_ahead = models.IntegerField(default=1, help_text="Aantal dagen vooruit voor notificatie")
    time_of_day = models.TimeField(default='09:00', help_text="Tijdstip voor notificatie")
    last_sent = models.DateTimeField(null=True, blank=True, help_text="Laatste keer verzonden")
    
    class Meta:
        verbose_name = "Notificatie Instelling"
        verbose_name_plural = "Notificatie Instellingen"
    
    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.email_recipients}"


class MobileAppNotification(models.Model):
    """
    Notificaties voor de mobile app
    """
    NOTIFICATION_STATUS_CHOICES = [
        ('pending', 'Wachtend'),
        ('sent', 'Verzonden'),
        ('delivered', 'Afgeleverd'),
        ('failed', 'Mislukt'),
    ]
    
    planning_session = models.ForeignKey(PlanningSession, on_delete=models.CASCADE, help_text="Planning sessie")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, help_text="Voertuig")
    driver = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, help_text="Chauffeur")
    notification_type = models.CharField(max_length=50, help_text="Type notificatie")
    message = models.TextField(help_text="Bericht voor de chauffeur")
    status = models.CharField(max_length=20, choices=NOTIFICATION_STATUS_CHOICES, default='pending')
    sent_at = models.DateTimeField(null=True, blank=True, help_text="Tijdstip verzonden")
    delivered_at = models.DateTimeField(null=True, blank=True, help_text="Tijdstip afgeleverd")
    
    class Meta:
        verbose_name = "Mobile App Notificatie"
        verbose_name_plural = "Mobile App Notificaties"
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"{self.vehicle.kenteken} - {self.get_status_display()} - {self.sent_at}"
