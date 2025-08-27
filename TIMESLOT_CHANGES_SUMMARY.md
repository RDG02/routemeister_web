# Tijdblokken Structuur Wijzigingen - Samenvatting

## Overzicht van Wijzigingen

De tijdblokken structuur is volledig aangepast volgens de nieuwe workflow specificatie.

### Oude Structuur
- Één tijdblok met zowel heen als terug tijden
- Velden: `heen_start_tijd`, `heen_eind_tijd`, `terug_start_tijd`, `terug_eind_tijd`
- `max_patienten_per_rit` veld

### Nieuwe Structuur
- Aparte tijdblokken voor "halen" en "brengen"
- Velden: `tijdblok_type` (halen/brengen), `aankomst_tijd`
- Verwijderd: `max_patienten_per_rit` (afhankelijk van voertuig capaciteit)

## Database Wijzigingen

### TimeSlot Model (planning/models.py)
- **Toegevoegd:**
  - `tijdblok_type` (CharField) - 'halen' of 'brengen'
  - `aankomst_tijd` (TimeField) - tijd van aankomst reha center (halen) of eind tijd voor brengen (brengen)
  
- **Verwijderd:**
  - `heen_start_tijd`, `heen_eind_tijd`
  - `terug_start_tijd`, `terug_eind_tijd`
  - `max_patienten_per_rit`

- **Behouden:**
  - `max_rijtijd_minuten` (deze is gekoppeld aan voertuigen)

## Nieuwe Tijdblokken

### HALEN Tijdblokken
- 08:00 Uhr (aankomst 08:00)
- 09:30 Uhr (aankomst 09:30)
- 12:00 Uhr (aankomst 12:00)

### BRENGEN Tijdblokken
- 12:00 Uhr (eind 12:00)
- 14:00 Uhr (eind 14:00)
- 16:00 Uhr (eind 16:00)
- 17:00 Uhr (eind 17:00)

## Aangepaste Bestanden

### 1. planning/models.py
- TimeSlot model volledig herzien
- Nieuwe velden en verwijderde velden
- Aangepaste Meta ordering

### 2. planning/admin.py
- TimeSlotAdmin aangepast voor nieuwe velden
- Nieuwe fieldsets structuur
- Verbeterde beschrijvingen

### 3. planning/templates/planning/timeslot_selection.html
- Template aangepast voor nieuwe structuur
- Aparte secties voor halen en brengen tijdblokken
- Gebruik van `tijdblok_type` en `aankomst_tijd`

### 4. assign_timeslots.py
- Script aangepast voor nieuwe logica
- Aparte filtering voor halen en brengen tijdblokken
- Nieuwe toewijzingslogica gebaseerd op aankomst tijden

### 5. check_timeslots.py
- Script aangepast voor nieuwe structuur
- Aparte groepering voor halen en brengen
- Verbeterde output format

### 6. create_new_timeslots.py (nieuw)
- Script om nieuwe tijdblokken aan te maken
- Volgens de nieuwe specificatie

## Migratie

### planning/migrations/0019_alter_timeslot_options_and_more.py
- Database migratie voor nieuwe structuur
- Verwijdering van oude velden
- Toevoeging van nieuwe velden met default waarden

## Workflow Voordelen

1. **Duidelijker scheiding:** Aparte tijdblokken voor halen en brengen
2. **Flexibiliteit:** Verschillende tijden voor halen en brengen mogelijk
3. **Eenvoud:** Één tijd per tijdblok in plaats van start/eind tijden
4. **Voertuig integratie:** Max patiënten afhankelijk van voertuig capaciteit
5. **Betere planning:** Duidelijkere aankomst tijden voor reha center

## Volgende Stappen

1. Test de admin interface
2. Test de tijdblok toewijzing met echte patiënten
3. Controleer of alle views correct werken
4. Update eventuele andere scripts die nog verwijzen naar oude structuur

## Scripts om uit te voeren

```bash
# Maak nieuwe tijdblokken aan
python create_new_timeslots.py

# Controleer tijdblokken
python check_timeslots.py

# Wijs tijdblokken toe aan patiënten
python assign_timeslots.py
```
