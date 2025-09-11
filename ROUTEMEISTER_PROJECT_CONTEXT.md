# 🚀 Routemeister Project Context Document

**Laatste update:** 25-08-2025  
**Versie:** 1.0  
**Doel:** Uitgebreide project documentatie voor AI assistentie

---

## 📋 Project Overzicht

**Routemeister** is een geavanceerd Django webapplicatie voor patiëntentransport planning in Duitsland. Het systeem automatiseert de complexe taak van het plannen van transportroutes voor patiënten naar en van revalidatiecentra.

### 🎯 Hoofddoelen
- **Automatische route planning** voor patiëntentransport
- **CSV/SLK import** van patiëntgegevens uit verschillende systemen
- **Dual planner systeem**: Snelle lokale planner + geavanceerde OptaPlanner
- **Real-time dashboard** voor planning monitoring
- **Constraint-based optimalisatie** met hard/soft constraints

---

## 🏗️ Architectuur Overzicht

### **Tech Stack**
- **Backend:** Django 5.2.5 (Python)
- **Database:** SQLite3 (development)
- **Frontend:** HTML5, CSS3, JavaScript, Bootstrap
- **Maps:** Leaflet.js + Google Maps API (optioneel)
- **External Services:** OptaPlanner (Java service)

### **Project Structuur**
```
routemeister_web/
├── routemeister/           # Django project settings
├── planning/              # Main Django app
│   ├── models.py         # Core data models
│   ├── models_extended.py # Extended models (CSVImportLog, PlanningSession)
│   ├── views.py          # Main business logic (6000+ lines)
│   ├── services/         # Business services
│   │   ├── optaplanner.py    # OptaPlanner integration
│   │   ├── simple_router.py  # Local constraint-based planner
│   │   └── csv_parser.py     # CSV parsing logic
│   ├── templates/        # HTML templates
│   ├── static/          # CSS, JS, images
│   └── management/      # Django management commands
├── db.sqlite3           # SQLite database
└── Various test files   # Test scripts and utilities
```

---

## 🗄️ Database Models & Relationships

### **Core Models**

#### 1. **Patient** (Hoofdmodel)
```python
class Patient(models.Model):
    # Basis gegevens
    naam = CharField(max_length=200)
    telefoonnummer = CharField(max_length=20)
    
    # Adres & GPS
    straat, postcode, plaats = CharField()
    latitude, longitude = FloatField()  # Voor route planning
    geocoding_status = CharField()     # pending/success/failed
    
    # Transport details
    start_behandel_tijd = DateTimeField() # Wanneer behandeling start
    eind_behandel_tijd = DateTimeField()  # Wanneer behandeling eindigd
    bestemming = CharField()
    
    # Planning toewijzingen
    halen_tijdblok = ForeignKey(TimeSlot)    # Tijdblok voor ophalen
    bringen_tijdblok = ForeignKey(TimeSlot)  # Tijdblok voor terugbrengen
    toegewezen_voertuig = ForeignKey(Vehicle)
    
    # Status & speciale behoeften
    status = CharField()  # nieuw/gepland/onderweg/notificatie_send/afgeleverd
    rolstoel = BooleanField()
    mobile_status = CharField()  # Voor chauffeur notificaties
```

#### 2. **Vehicle** (Voertuig beheer)
```python
class Vehicle(models.Model):
    # Identificatie
    referentie = CharField()  # W206, etc.
    kenteken = CharField(unique=True)
    merk_model = CharField()
    
    # Capaciteit
    aantal_zitplaatsen = IntegerField(default=7)
    speciale_zitplaatsen = IntegerField(default=0)  # Speciale plaatsen
    
    # Kosten & beperkingen
    km_kosten_per_km = DecimalField(default=0.29)
    maximale_rit_tijd = IntegerField(default=3600)  # seconden
    
    # Visueel & status
    kleur = CharField(default='#3498db')  # Hex kleur
    status = CharField()  # beschikbaar/onderhoud/defect
```

#### 3. **TimeSlot** (Tijdblok systeem)
```python
class TimeSlot(models.Model):
    naam = CharField()  # "08:00 Uhr", "09:30 Uhr"
    tijdblok_type = CharField()  # 'halen' of 'brengen'
    aankomst_tijd = TimeField()  # Tijd bij reha center
    max_rijtijd_minuten = IntegerField(default=60)
    actief = BooleanField(default=True)
    dag_van_week = CharField()  # maandag/vrijdag/alle_dagen
```

#### 4. **Location** (Locatie beheer)
```python
class Location(models.Model):
    name = CharField()  # "Reha Center Bonn"
    location_type = CharField()  # home/depot
    address = TextField()
    latitude, longitude = DecimalField()
    is_default = BooleanField()  # Standaard home locatie
```

### **Extended Models**

#### 5. **CSVImportLog** (Import tracking)
```python
class CSVImportLog(models.Model):
    filename = CharField()
    imported_by = ForeignKey(User)
    import_date = DateTimeField(auto_now_add=True)  # Tijd van import
    status = CharField()  # success/failed/processing
    total_patients = IntegerField()
    imported_patients = IntegerField()
    csv_content = TextField()  # Volledige CSV voor debugging
```

**Admin Interface met Download Functionaliteit:**
```python
@admin.register(CSVImportLog)
class CSVImportLogAdmin(admin.ModelAdmin):
    list_display = ("filename", "imported_by", "import_date", "status", "download_link")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:log_id>/download/",
                self.admin_site.admin_view(self.download_csv),
                name="csvimportlog_download",
            ),
        ]
        return custom_urls + urls

    def download_link(self, obj):
        return format_html('<a href="{}">Download CSV</a>', f"{obj.id}/download/")
    download_link.short_description = "Download"

    def download_csv(self, request, log_id):
        log = CSVImportLog.objects.get(pk=log_id)
        response = HttpResponse(log.csv_content, content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{log.filename}"'
        return response
```

#### 6. **PlanningSession** (Workflow management)
```python
class PlanningSession(models.Model):
    name = CharField()
    created_by = ForeignKey(User)
    status = CharField()  # concept/processing/completed/published
    planning_date = DateField()
    selected_vehicles = ManyToManyField(Vehicle)
    selected_timeslots = ManyToManyField(TimeSlot)
    routes_data = JSONField()  # Route resultaten
```

---

## 🔄 Belangrijke Workflows

### **1. CSV Import Workflow**
```
1. Upload CSV/SLK bestand → upload_csv()
2. Detecteer formaat (Fahrdlist/Routemeister/Generic)
3. Parse kolommen volgens CSVParserConfig
4. Valideer en geocode adressen
5. Maak Patient objecten
6. Log import resultaten in CSVImportLog
7. Redirect naar planning wizard
```

### **2. Planning Wizard Workflow**
```
Stap 1: Upload & Preview
├── CSV upload en validatie
├── Patiënt preview met geocoding status
└── Tijdblok selectie

Stap 2: timeblock-Assignment
├── Patiënten toewijzen aan tijdblokken
├── HALEN: start_behandel_tijd → halen_tijdblok (exacte tijd match)
├── BRINGEN: eind_behandel_tijd → bringen_tijdblok (exacte tijd match)
├── Drag & Drop Interface:
│   ├── Patiënten slepen tussen tijdblokken (met validatie)
│   ├── Patiënten verwijderen uit tijdblokken 
│   ├── Real-time validatie tijdens slepen
│   ├── Confirmation dialogs voor regel overtredingen
│   ├── Logging van alle wijzigingen in de django admin instellingen 
│   └── Visual feedback (hover states, drop zones)
└── Validatie en feedback

Stap 3: Route Planning
├── Constraint configuratie
├── Route generatie
└── Resultaten weergave
```

### **2.1. Drag & Drop Implementation Details**

**Moderne, mobielvriendelijke implementatie met dnd-kit**
```javascript
// Modern drag & drop met dnd-kit - Mobielvriendelijk
import { DndContext, DragOverlay, closestCenter } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { useSortable, useDroppable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

// Main drag & drop context
function TimeslotAssignmentInterface() {
    const [activeId, setActiveId] = useState(null);
    const [patients, setPatients] = useState([]);
    const [timeslots, setTimeslots] = useState([]);

    function handleDragStart(event) {
        setActiveId(event.active.id);
    }

    function handleDragOver(event) {
        const { active, over } = event;
        
        if (!over) return;
        
        const activePatient = patients.find(p => p.id === active.id);
        const overTimeslot = timeslots.find(t => t.id === over.id);
        
        if (activePatient && overTimeslot) {
            // Real-time validatie tijdens slepen
            validateTimeslotAssignment(activePatient.id, overTimeslot.id, overTimeslot.type);
        }
    }

    function handleDragEnd(event) {
        const { active, over } = event;
        
        if (!over) return;
        
        const patientId = active.id;
        const timeslotId = over.id;
        const timeslotType = over.data.current?.type;
        
        // Validatie en assignment
        validateAndAssignPatient(patientId, timeslotId, timeslotType);
        
        setActiveId(null);
    }

    return (
        <DndContext
            collisionDetection={closestCenter}
            onDragStart={handleDragStart}
            onDragOver={handleDragOver}
            onDragEnd={handleDragEnd}
        >
            <div className="timeslot-assignment-interface">
                {/* Patiënten lijst */}
                <SortableContext items={patients.map(p => p.id)} strategy={verticalListSortingStrategy}>
                    {patients.map(patient => (
                        <PatientCard key={patient.id} patient={patient} />
                    ))}
                </SortableContext>
                
                {/* Tijdblok drop zones */}
                {timeslots.map(timeslot => (
                    <TimeslotDropZone key={timeslot.id} timeslot={timeslot} />
                ))}
                
                {/* Trash zone voor verwijderen */}
                <TrashDropZone />
            </div>
            
            <DragOverlay>
                {activeId ? <PatientCard patient={patients.find(p => p.id === activeId)} /> : null}
            </DragOverlay>
        </DndContext>
    );
}

// Sortable patiënt card component
function PatientCard({ patient }) {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging,
    } = useSortable({ id: patient.id });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
    };

    return (
        <div
            ref={setNodeRef}
            style={style}
            {...attributes}
            {...listeners}
            className={`patient-card ${isDragging ? 'dragging' : ''}`}
        >
            <div className="patient-info">
                <h4>{patient.naam}</h4>
                <p>{patient.start_behandel_tijd} - {patient.eind_behandel_tijd}</p>
                {patient.rolstoel && <span className="wheelchair-icon">♿</span>}
            </div>
        </div>
    );
}

// Drop zone component
function TimeslotDropZone({ timeslot }) {
    const { setNodeRef, isOver } = useDroppable({
        id: timeslot.id,
        data: { type: timeslot.tijdblok_type }
    });

    return (
        <div
            ref={setNodeRef}
            className={`timeslot-drop-zone ${isOver ? 'drag-over' : ''}`}
            data-timeslot-id={timeslot.id}
            data-timeslot-type={timeslot.tijdblok_type}
        >
            <h3>{timeslot.naam} ({timeslot.tijdblok_type})</h3>
            <div className="assigned-patients">
                {timeslot.patients?.map(patient => (
                    <PatientCard key={patient.id} patient={patient} />
                ))}
            </div>
        </div>
    );
}
```

#### **Validatie en Confirmation**
```javascript
// Validatie functie
async function validateAndAssignPatient(patientId, timeslotId, timeslotType) {
    try {
        // Check of wijziging tegen de regels is
        const response = await fetch(`/api/validate-timeslot-assignment/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                patient_id: patientId,
                timeslot_id: timeslotId,
                timeslot_type: timeslotType
            })
        });
        
        const data = await response.json();
        
        if (data.violates_rules) {
            // Toon confirmation dialog
            showConfirmationDialog(data, patientId, timeslotId, timeslotType);
        } else {
            // Direct toewijzen
            await assignPatientToTimeslot(patientId, timeslotId, timeslotType);
        }
    } catch (error) {
        console.error('Validatie fout:', error);
        showErrorMessage('Er is een fout opgetreden bij de validatie');
    }
}

// Modern confirmation dialog
function showConfirmationDialog(validationData, patientId, timeslotId, timeslotType) {
    const violations = validationData.violations.join('\n');
    
    // Gebruik moderne modal i.p.v. browser confirm
    const modal = document.createElement('div');
    modal.className = 'confirmation-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <h3>⚠️ WAARSCHUWING</h3>
            <p>Deze wijziging overtreedt de planning regels:</p>
            <pre>${violations}</pre>
            <div class="modal-actions">
                <button class="btn-cancel">Annuleren</button>
                <button class="btn-confirm">Toch doorgaan</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    modal.querySelector('.btn-cancel').onclick = () => {
        document.body.removeChild(modal);
    };
    
    modal.querySelector('.btn-confirm').onclick = async () => {
        document.body.removeChild(modal);
        await assignPatientToTimeslot(patientId, timeslotId, timeslotType, true);
    };
}
```

#### **Installatie dnd-kit**
```bash
# NPM installatie (aanbevolen)
npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities

# Of via CDN voor snelle implementatie
<script src="https://unpkg.com/@dnd-kit/core@6.0.8/dist/index.umd.js"></script>
<script src="https://unpkg.com/@dnd-kit/sortable@7.0.2/dist/index.umd.js"></script>
<script src="https://unpkg.com/@dnd-kit/utilities@3.2.1/dist/index.umd.js"></script>
```

#### **CSS Styling voor dnd-kit**
```css
/* Drag & Drop Styling */
.timeslot-assignment-interface {
    display: grid;
    grid-template-columns: 1fr 2fr;
    gap: 20px;
    padding: 20px;
}

.patient-card {
    background: #fff;
    border: 2px solid #e1e5e9;
    border-radius: 8px;
    padding: 12px;
    margin: 8px 0;
    cursor: grab;
    transition: all 0.2s ease;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.patient-card:hover {
    border-color: #3498db;
    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

.patient-card.dragging {
    opacity: 0.5;
    transform: rotate(5deg);
}

.timeslot-drop-zone {
    background: #f8f9fa;
    border: 2px dashed #dee2e6;
    border-radius: 8px;
    padding: 16px;
    min-height: 200px;
    transition: all 0.2s ease;
}

.timeslot-drop-zone.drag-over {
    border-color: #28a745;
    background: #d4edda;
}

.trash-drop-zone {
    background: #f8d7da;
    border: 2px dashed #dc3545;
    border-radius: 8px;
    padding: 20px;
    text-align: center;
    color: #721c24;
    margin-top: 20px;
}

.confirmation-modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0,0,0,0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}

.modal-content {
    background: white;
    padding: 24px;
    border-radius: 8px;
    max-width: 500px;
    width: 90%;
}

.modal-actions {
    display: flex;
    gap: 12px;
    justify-content: flex-end;
    margin-top: 20px;
}

.btn-cancel, .btn-confirm {
    padding: 8px 16px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-weight: 500;
}

.btn-cancel {
    background: #6c757d;
    color: white;
}

.btn-confirm {
    background: #dc3545;
    color: white;
}

.wheelchair-icon {
    background: #ffc107;
    color: #000;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 12px;
    margin-left: 8px;
}
```

**Backend API Endpoints:**
```python
@csrf_exempt
def api_validate_timeslot_assignment(request):
    """Validate if timeslot assignment violates rules"""
    import json
    data = json.loads(request.body)
    
    patient_id = data.get('patient_id')
    timeslot_id = data.get('timeslot_id')
    timeslot_type = data.get('timeslot_type')
    
    patient = Patient.objects.get(id=patient_id)
    new_timeslot = TimeSlot.objects.get(id=timeslot_id)
    
    violations = []
    
    # Check tijdvenster regels
    if timeslot_type == 'halen':
        current_time = patient.start_behandel_tijd.time()
        new_time = new_timeslot.aankomst_tijd
        
        # Geen tolerantie - exacte match vereist
        if current_time != new_time:
            violations.append(f"⏰ Tijdvenster overtreding: {current_time} → {new_time} (exacte match vereist)")
    
    # Check voertuig capaciteit
    current_patients = Patient.objects.filter(
        **{f'{timeslot_type}_tijdblok': new_timeslot}
    ).count()
    
@csrf_exempt
def api_assign_patient_timeslot(request):
    """Assign patient to timeslot via drag & drop with logging"""
    import json
    data = json.loads(request.body)
    
    patient_id = data.get('patient_id')
    timeslot_id = data.get('timeslot_id')
    timeslot_type = data.get('timeslot_type')
    force = data.get('force', False)
    
    patient = Patient.objects.get(id=patient_id)
    new_timeslot = TimeSlot.objects.get(id=timeslot_id)
    
    # Log oude waarde
    old_timeslot = getattr(patient, f'{timeslot_type}_tijdblok')
    
    # Update patiënt
    if timeslot_type == 'halen':
        patient.halen_tijdblok = new_timeslot
    else:
        patient.bringen_tijdblok = new_timeslot
    
    patient.save()
    
    # Log wijziging
    from .models_extended import TimeslotAssignmentLog
    TimeslotAssignmentLog.objects.create(
        patient=patient,
        timeslot_type=timeslot_type,
        old_timeslot=old_timeslot,
        new_timeslot=new_timeslot,
        changed_by=request.user if request.user.is_authenticated else None,
        force_assignment=force,
        change_reason='drag_and_drop'
    )
    
    return JsonResponse({'status': 'success'})

@csrf_exempt
def api_remove_patient_timeslot(request):
    """Remove patient from timeslot with logging"""
    import json
    data = json.loads(request.body)
    
    patient_id = data.get('patient_id')
    timeslot_type = data.get('timeslot_type')
    
    patient = Patient.objects.get(id=patient_id)
    
    # Log oude waarde
    old_timeslot = getattr(patient, f'{timeslot_type}_tijdblok')
    
    # Update patiënt
    if timeslot_type == 'halen':
        patient.halen_tijdblok = None
    else:
        patient.bringen_tijdblok = None
    
    patient.save()
    
    # Log wijziging
    from .models_extended import TimeslotAssignmentLog
    TimeslotAssignmentLog.objects.create(
        patient=patient,
        timeslot_type=timeslot_type,
        old_timeslot=old_timeslot,
        new_timeslot=None,
        changed_by=request.user if request.user.is_authenticated else None,
        force_assignment=False,
        change_reason='drag_and_drop_remove'
    )
    
    return JsonResponse({'status': 'success'})
```

**TimeslotAssignmentLog Model:**
```python
class TimeslotAssignmentLog(models.Model):
    """Log alle wijzigingen aan timeslot toewijzingen"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    timeslot_type = models.CharField(max_length=10, choices=[
        ('halen', 'Halen'),
        ('brengen', 'Brengen')
    ])
    old_timeslot = models.ForeignKey(TimeSlot, on_delete=models.SET_NULL, null=True, blank=True, related_name='old_assignments')
    new_timeslot = models.ForeignKey(TimeSlot, on_delete=models.SET_NULL, null=True, blank=True, related_name='new_assignments')
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    force_assignment = models.BooleanField(default=False, help_text="Was dit een geforceerde toewijzing tegen de regels?")
    change_reason = models.CharField(max_length=50, choices=[
        ('drag_and_drop', 'Drag & Drop'),
        ('drag_and_drop_remove', 'Drag & Drop Remove'),
        ('auto_assignment', 'Auto Assignment'),
        ('manual_edit', 'Manual Edit'),
        ('csv_import', 'CSV Import')
    ])
    
    class Meta:
        verbose_name = "Timeslot Assignment Log"
        verbose_name_plural = "Timeslot Assignment Logs"
        ordering = ['-changed_at']
    
    def __str__(self):
        return f"{self.patient.naam} - {self.timeslot_type} - {self.changed_at}"
```

### **3. Route Planning Workflow**

#### **Google maps API planner **
```
1. Groepeer patiënten per tijdblok
2. controleer voertuigen met status beschikbaar 
3. Valideer hard constraints:
   - Voertuig capaciteit
   - Maximale reistijd
   - Tijdvensters
   - Rolstoel vereisten
4. Bereken soft constraint scores:
   - Minimale afstand/tijd
   - Evenwichtige belasting
   - Minimale wachttijd
5. genereer route per tijdsblok met patienten en voertuigen 
```

#### **OptaPlanner **
```
1. Clear OptaPlanner database
2. Voeg depot toe (uit admin instellingen)
3. Voeg voertuigen toe per tijdblok
4. Voeg patiënten toe als pickup locations
5. Start route optimalisatie
6. Haal resultaten op per tijdsblok
7. Parse en toon routes
```

---

## 🎨 Code Structuur & Patronen

### **Views.py Structuur** (6000+ regels)
```python
# Main workflow functions
def dashboard()              # Dashboard met statistieken
def upload_csv()            # CSV import en verwerking
def planning_wizard_*()     # stappen planning wizard
def auto_assign_patients()  # Automatische tijdblok toewijzing
def plan_routes_*()         # Route planning (google/optaplanner)
def route_results()         # Route resultaten weergave

# API endpoints
@csrf_exempt
def api_generate_routes()   # AJAX route generatie
def api_*()                 # Andere API endpoints

# Utility functions
def convert_time_format()   # Tijd conversie (845 → 08:45)
def parse_csv_*()          # CSV parsing helpers
```

### **Services Pattern**
```python
# planning/services/
├── optaplanner.py      # OptaPlanner API integration
├── google_router.py    # Google maps API integration
├── csv_parser.py       # CSV format detection & parsing
└── geocoding.py        # Address geocoding services
```

### **Template Structuur**
```html
# planning/templates/planning/
├── base.html                    # Base template
├── dashboard.html              # Main dashboard
├── wizard/
│   ├── start.html             # Wizard stap 1: Upload
│   ├── preview.html           # Wizard stap 2: Preview
│   └── assignment.html        # Wizard stap 3: Planning
├── route_results.html         # Route resultaten
└── static/                    # CSS, JS, images
```

---

## ⚙️ Configuratie Details

### **Django Settings**
```python
# routemeister/settings.py
INSTALLED_APPS = ['planning']
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3'}}
STATIC_URL = 'static/'
MEDIA_URL = '/media/'

# OptaPlanner Configuration
OPTAPLANNER_URL = 'http://localhost:8000'
OPTAPLANNER_ENABLED = True
```

### **CSV Parser Configuraties**
```python
# Automatische detectie van CSV formaten
CSVParserConfig.objects.create(
    naam='Fahrdlist',
    bestandsnaam_patroon='fahrdlist.*\\.csv',
    header_keywords='kunde,termin,fahrer',
    kolom_mapping={
        'patient_id': 1,
        'achternaam': 2,
        'voornaam': 3,
        'adres': 6,
        'postcode': 7,        # Postcode veld
        'landcode': 8,        # Landcode veld (D/DE, NL, etc.)
        'datum': 15,
        'start_behandel_tijd': 17,
        'eind_behandel_tijd': 18
    }
)

# Routemeister CSV configuratie
CSVParserConfig.objects.create(
    naam='Routemeister',
    bestandsnaam_patroon='routemeister.*\\.csv',
    header_keywords='patient,achternaam,voornaam,adres,plaats,postcode,telefoon',
    kolom_mapping={
        'patient_id': 1,
        'achternaam': 2,
        'voornaam': 3,
        'adres': 6,
        'plaats': 8,
        'postcode': 9,        # Postcode veld
        'landcode': 10,       # Landcode veld (D/DE, NL, etc.)
        'telefoon1': 11,
        'telefoon2': 12,
        'datum': 15,
        'start_behandel_tijd': 17,
        'eind_behandel_tijd': 18
    }
)
```

### **TimeSlot Configuratie**
```python
# Standaard tijdblokken
HALEN_TIMESLOTS = [
    ('08:00 Uhr', time(8, 0)),
    ('09:30 Uhr', time(9, 30)),
    ('10:30 Uhr', time(10, 30)),
    ('12:00 Uhr', time(12, 0))
]

BRINGEN_TIMESLOTS = [
    ('14:00 Uhr', time(14, 0)),
    ('15:30 Uhr', time(15, 30)),
    ('16:30 Uhr', time(16, 30)),
    ('17:30 Uhr', time(17, 30)),
    ('18:30 Uhr', time(18, 30)),
    ('19:30 Uhr', time(19, 30))
]
```

---

## 🔧 Constraint System

### **Hard Constraints** (Moeten voldaan worden)
1. **Voertuig Capaciteit**: `total_passengers <= vehicle.aantal_zitplaatsen`
2. **Maximale Reistijd**: `estimated_travel_time <= vehicle.maximale_rit_tijd`
3. **Tijdvensters**: Patiënten moeten exacte tijdvenster match hebben
4. **Voertuig Beschikbaarheid**: `vehicle.status == 'beschikbaar'`
5. **Patiënt Vereisten**: `wheelchair_patients <= vehicle.speciale_zitplaatsen`

### **Soft Constraints** (Optimalisatie doelen)
1. **Minimale Totale Afstand**: `total_distance * 0.1`
2. **Minimale Totale Tijd**: `total_time * 0.05`
3. **Evenwichtige Belasting**: Penalty voor <30% of >90% belasting
4. **Minimale Wachttijd**: `waiting_time * 0.2`

---

## 🚨 Bekende Issues & Limitations

### **Huidige Problemen**
1. **OptaPlanner Kaart**: Gebruikt België i.p.v. Duitsland (wordt opgelost)
2. **Geocoding**: Soms falen adressen (fallback naar default locatie)
3. **Performance**: Grote CSV bestanden kunnen traag zijn
4. **Error Handling**: Sommige edge cases niet afgehandeld

### **Technical Debt**
1. **Views.py**: 6000+ regels in één bestand (kan opgesplitst worden)
2. **Hardcoded Values**: Sommige configuraties hardcoded
3. **Test Coverage**: Beperkte test coverage
4. **Documentation**: Inline comments kunnen beter

---

## 🎯 Development Prioriteiten

### **Korte Termijn** (1-2 weken)
1. **OptaPlanner kaart fix** (Duitsland i.p.v. België)
2. **Error handling verbeteren**
3. **Performance optimalisatie**
4. **UI/UX verbeteringen**

### **Middellange Termijn** (1-2 maanden)
1. **Code refactoring** (views.py opsplitsen)
2. **Test suite uitbreiden**
3. **Mobile app integratie**
4. **Advanced reporting**

### **Lange Termijn** (3+ maanden)
1. **Multi-tenant support**
2. **Advanced analytics**
3. **Machine learning optimalisatie**
4. **API voor externe systemen**

---

## 📚 Belangrijke Bestanden

### **Core Files**
- `planning/views.py` - Main business logic (6000+ lines)
- `planning/models.py` - Database models
- `planning/services/simple_router.py` - Local planner
- `planning/services/optaplanner.py` - External planner integration

### **Configuration Files**
- `routemeister/settings.py` - Django settings
- `planning/urls.py` - URL routing
- `planning/admin.py` - Django admin interface

### **Templates**
- `planning/templates/planning/dashboard.html` - Main dashboard
- `planning/templates/planning/wizard/` - Planning wizard
- `planning/static/` - CSS, JS, images

### **Test Files**
- `test_*.py` - Various test scripts
- `debug_*.py` - Debugging utilities
- `check_*.py` - Data validation scripts

---

## 🔍 Debugging & Monitoring

### **Logging**
```python
import logging
logger = logging.getLogger(__name__)

# Gebruik in views
logger.info(f"Planning routes for {patient_count} patients")
logger.error(f"OptaPlanner error: {error_message}")
```

### **Debug Scripts**
- `debug_optaplanner_calls.py` - OptaPlanner API debugging
- `debug_planning_flow.py` - Planning workflow debugging
- `check_patients.py` - Patient data validation
- `check_timeslots.py` - TimeSlot validation

### **Database Queries**
```python
# Veelgebruikte queries
patients = Patient.objects.filter(
    start_behandel_tijd__date=today,
    toegewezen_voertuig__isnull=False
)

vehicles = Vehicle.objects.filter(status='beschikbaar')
timeslots = TimeSlot.objects.filter(actief=True)
```

---

## 🚀 Deployment & Production

### **Development Setup**
```bash
# Virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install django

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run server
python manage.py runserver
```

### **Production Considerations**
- **Database**: PostgreSQL i.p.v. SQLite
- **Static Files**: WhiteNoise of CDN
- **Media Files**: AWS S3 of similar
- **Security**: DEBUG=False, SECRET_KEY, ALLOWED_HOSTS
- **Monitoring**: Sentry voor error tracking
- **Backup**: Database backup strategie

---

**Dit document wordt automatisch bijgewerkt bij belangrijke wijzigingen aan het project.**
