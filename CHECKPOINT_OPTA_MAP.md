# 🗺️ CHECKPOINT: OptaPlanner Map Issue

**Datum:** 21-08-2025  
**Status:** OptaPlanner gebruikt verkeerde kaart (België i.p.v. Duitsland)

## ✅ Wat werkt momenteel:

### **1. Tijdblokken Systeem**
- ✅ 10 correcte tijdblokken (4 Halen, 6 Brengen)
- ✅ Geen duplicaten meer
- ✅ Automatische clearing bij nieuwe planning

### **2. Patiënt Tijd Toewijzing**
- ✅ Kolom 18 = Start tijd (ophaal tijd) - NIET afspraak tijd
- ✅ Correcte tijdblok toewijzing volgens jouw logica
- ✅ Geen 1 uur aftrekken meer nodig

### **3. API Calls naar OptaPlanner**
- ✅ Alle API calls werken (200 status)
- ✅ Correcte volgorde: Clear → Depot → Vehicles → Patients → Route
- ✅ Patiënten worden toegevoegd met `type=pickup bool:true`
- ✅ Voertuigen worden correct toegevoegd
- ✅ Depot (Reha Center Bonn) wordt correct toegevoegd

### **4. Per-Tijdblok Verwerking**
- ✅ Automatische groepering van patiënten per tijdblok
- ✅ Per tijdblok: Clear → Depot → Vehicles → Patients → Route
- ✅ Lege tijdblokken worden overgeslagen

## 🔧 Wat er aangepast moet worden:

### **1. OptaPlanner Kaart**
- ❌ **PROBLEEM:** OptaPlanner gebruikt België kaart i.p.v. Duitsland
- ✅ **OPLOSSING:** OptaPlanner kaart wordt aangepast naar Duitsland

### **2. Web Pagina's (tussentijd)**
- 📝 Dashboard verbeteringen
- 📝 Planning workflow optimalisatie
- 📝 UI/UX verbeteringen
- 📝 Extra functionaliteiten

## 📊 Huidige Test Data:

### **Patiënten (2025-08-21):**
- Anette & Wilfried: 08:45 → `Holen 08:00 Uhr`
- Natalia & Beatrice: 10:15/10:25 → `Holen 09:30 Uhr`
- Brigitte, Kubra, Marita, Frank: 10:45 → `Holen 10:30 Uhr`
- Ute & Birgit: 11:45 → `Holen 10:30 Uhr`
- Hannelore & Stephan: 12:15 → `Holen 12:00 Uhr`

### **Voertuigen:**
- 6 voertuigen beschikbaar
- Correcte capaciteit en tarieven

### **Home Location:**
- Reha Center Bonn: 7.151631000, 50.746702862

## 🎯 Volgende Stappen:

1. **OptaPlanner kaart aanpassen** (jij)
2. **Web pagina's verbeteren** (ik)
3. **Complete end-to-end test** na kaart fix
4. **Route optimalisatie testen**

## 📝 API Call Voorbeelden:

```bash
# Clear
GET http://localhost:8080/api/clear

# Add Depot
GET http://localhost:8080/api/locationadd/Reha_Center_Bonn/7.151631000/50.746702862/0/0/_/1

# Add Vehicle
GET http://localhost:8080/api/vehicleadd/12_34_ab/7/0/28/3600

# Add Patient (pickup)
GET http://localhost:8080/api/locationadd/Wilfried_Hermanns/7.1885915/50.8093997/0/0/_/1

# Get Route
GET http://localhost:8080/api/route
```

---
**Checkpoint gemaakt:** 21-08-2025 20:57
