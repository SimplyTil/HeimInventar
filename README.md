# 🏠 NexoSync - Smart Kitchen Inventory System

Ein intelligentes Haushalts-Inventarsystem zur Verwaltung von Lebensmitteln mit Barcode-Scanner, Einkaufslisten und umfangreicher Statistik.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![Flask](https://img.shields.io/badge/Flask-3.0.0-lightgrey.svg)

## 📋 Inhaltsverzeichnis

- [Features](#-features)
- [Installation](#-installation)
- [Verwendung](#-verwendung)
- [Technologie-Stack](#-technologie-stack)
- [API-Dokumentation](#-api-dokumentation)
- [Datenbank-Schema](#-datenbank-schema)
- [Raspberry Pi Setup](#-raspberry-pi-setup)
- [Entwicklung](#-entwicklung)

## ✨ Features

### 📱 Kernfunktionen
- **Barcode-Scanner**: EAN-Codes scannen mit Kamera oder manueller Eingabe
- **Open Food Facts Integration**: Automatisches Abrufen von Produktinformationen
- **Produktverwaltung**: Hinzufügen, Bearbeiten, Löschen von Produkten
- **Kamera-Integration**: Direkte Kameraaufnahme für Produktfotos mit Live-Vorschau
- **Bild-Kompression**: Automatische Optimierung für Raspberry Pi (max 200KB)
- **Dateisystem-Storage**: Bilder werden in `static/uploads/` gespeichert, nicht in der Datenbank

### 🛒 Intelligente Features
- **Duplikat-Erkennung**: Warnt beim Hinzufügen bereits vorhandener Produkte
- **Einkaufsliste**: 
  - Manuelles Hinzufügen von Artikeln
  - Automatische Generierung aus abgelaufenen/niedrigen Beständen
  - Abhaken und Löschen erledigter Einkäufe
- **Barcode-Verlauf**: 
  - Speichert alle gescannten Produkte mit vollständigen Metadaten
  - Quick-Add Funktion für bereits gelöschte Produkte
  - Persistenz auch nach Produkt-Löschung
- **Kategorien & Tags**: 
  - Automatische Kategorisierung via Open Food Facts API
  - Manuelle Tags für eigene Organisation
- **Preis-Tracking**: Gesamtwert des Inventars und Kostenübersicht

### 📊 Statistiken & Analytics
**Basis-Statistiken**: 
- Gesamtanzahl Produkte
- Abgelaufene Produkte
- Bald ablaufende Produkte (innerhalb 7 Tage)
- Gesamtwert des Inventars
  
**Erweiterte Statistiken**:
- Verschwendungs-Tracking (Wert abgelaufener Produkte)
- Kategorie-Breakdown mit Anzahl pro Kategorie
- Top 5 gescannte Produkte
- Wöchentliche Trends

### 🎨 Design & UX
- **Dark Mode**: Automatische Erkennung des System-Themes
- **Mobile-First**: Optimiert für Smartphone-Nutzung
- **Responsive Design**: Separate Layouts für Desktop und Mobile
- **Collapsible Search**: Platzsparende mobile Suche mit Slide-Animation
- **Touch-optimiert**: Große Buttons und Checkboxen für mobile Geräte
- **Burger-Menu**: Kompakte Filter-Sidebar
- **Glass-Panel Design**: Moderne Optik mit Backdrop-Blur-Effekten

### 🔒 Sicherheit & Performance
- **Input-Sanitization**: Schutz vor SQL-Injection und XSS
- **EAN-Validierung**: Format-Prüfung für Barcodes (8-13 Stellen)
- **Datei-System Storage**: Effiziente Bild-Speicherung mit automatischer Löschung
- **Automatische Migrations**: Nahtlose Datenbank-Updates beim Start
- **Indizierte Suche**: Optimierte Abfragen auf Name, Standort und Ablaufdatum
- **Size Limits**: Max 1MB Request-Größe, Bild-Kompression auf ~50-200KB

## 🚀 Installation

### Voraussetzungen
- Python 3.8 oder höher
- SQLite3 (im Python-Standard enthalten)
- Internetverbindung (für Open Food Facts API)

### Quick Start

1. **Repository klonen/herunterladen**
```bash
cd /pfad/zu/deinem/ordner
```

2. **Virtuelle Umgebung erstellen** (empfohlen)
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac/Raspberry Pi
# oder
venv\Scripts\activate  # Windows
```

3. **Dependencies installieren**
```bash
pip install -r requirements.txt
# Oder manuell:
# pip install flask requests gunicorn
```

4. **Server starten**

**Entwicklung (Testing):**
```bash
python app.py
```

**Production (Raspberry Pi 24/7):**
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
# -w 4 = 4 Worker-Prozesse (für Raspberry Pi 4)
# -w 2 = für Raspberry Pi Zero/3
```

Die Datenbank wird automatisch beim ersten Start erstellt.

### Für Netzwerk-Zugriff (Raspberry Pi)
Die App ist bereits für 0.0.0.0 konfiguriert, sodass du von jedem Gerät im Netzwerk zugreifen kannst:
```
http://<raspberry-pi-ip>:5000
```

**Production-Server mit Gunicorn (empfohlen):**
```bash
# Mehr Worker für bessere Performance
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 app:app

# Mit Logging
gunicorn -w 4 -b 0.0.0.0:5000 --access-logfile - --error-logfile - app:app
```

## 📖 Verwendung

### Produkt hinzufügen
1. **Barcode scannen**: Kamera-Button drücken oder EAN manuell eingeben
2. **Produktdaten**: Open Food Facts lädt automatisch Name, Kategorie, Bild
3. **Optional**: Eigenes Foto mit Kamera aufnehmen (Live-Vorschau)
4. **Details eingeben**: Ablaufdatum, Standort, Menge, Preis
5. **Speichern**: Produkt wird zur Datenbank hinzugefügt

### Barcode-Verlauf nutzen (NEU!)
**Gelöschte Produkte schnell wieder hinzufügen:**
1. Barcode scannen (auch von gelöschten Produkten)
2. **Verlauf**-Button klicken (📜 Icon)
3. Alle jemals gescannten Produkte werden angezeigt
4. **Quick Add** klicken → alle gespeicherten Daten werden vorausgefüllt
5. Nur Ablaufdatum aktualisieren und speichern

**Vorteile:**
- Keine Daten gehen verloren, auch nach Löschung
- Scan-Count zeigt Häufigkeit
- Kategorien, Tags, Diät-Flags bleiben erhalten

### Einkaufsliste generieren
1. **Einkaufsliste**-Button öffnen (🛒 Icon)
2. **Manuell hinzufügen**: Artikel-Name, Menge, optional Kategorie
3. **Auto-Generieren**: System findet automatisch:
   - Abgelaufene Produkte
   - Produkte mit Menge ≤ 2
4. **Abhaken**: Erledigte Einkäufe markieren
5. **Löschen**: Abgehakte Artikel entfernen

### Filter nutzen
**Burger-Menu öffnen (☰) für:**
- **Standort**: Nach Lagerort filtern (Kühlschrank, Vorratsschrank, Gefrierschrank)
- **Ablauf**: Nur abgelaufene/bald ablaufende anzeigen
- **Vegetarisch/Vegan**: Ernährungsfilter
- **Suche**: Nach Name oder EAN durchsuchen

### Statistiken anzeigen
**Basis-Statistiken** (📊 Icon):
- Produkt-Übersicht
- Ablauf-Status
- Gesamtwert

**Erweiterte Statistiken** (📊 im Modal):
- Verschwendungs-Wert
- Kategorie-Verteilung
- Top-Produkte
- Wöchentliche Entwicklung

## 🛠️ Technologie-Stack

### Backend
- **Flask 3.0.0**: Python Web Framework
- **SQLite3**: Leichtgewichtige Datenbank mit automatischen Migrations
- **Requests**: HTTP-Client für Open Food Facts API
- **UUID**: Generierung eindeutiger Dateinamen für Bilder
- **Base64**: Bild-Encoding für Upload

### Frontend
- **Vue.js 3**: Reaktives JavaScript Framework (Global Production Build)
- **Tailwind CSS**: Utility-First CSS Framework
- **Font Awesome**: Icon-Bibliothek
- **HTML5-QRCode**: Barcode-Scanner Library
- **MediaDevices API**: Kamera-Zugriff mit Stream-Verwaltung

### APIs & Integrationen
- **Open Food Facts API**: Produktdaten-Abruf (Name, Kategorie, Bild, Nährwerte)
- **MediaDevices API**: getUserMedia() für Kamera-Zugriff
- **Browser Notifications API**: Push-Benachrichtigungen

## 📡 API-Dokumentation

### Produkte

#### `GET /api/products`
Alle Produkte abrufen
```json
[
  {
    "id": 1,
    "ean": "4025127020997",
    "name": "Milch 3.5%",
    "expiry_date": "2025-12-01",
    "purchase_date": "2025-11-20",
    "location": "Kühlschrank",
    "quantity": 2,
    "weight_volume": "1L",
    "notes": "",
    "is_vegetarian": 1,
    "is_vegan": 0,
    "price": 1.29,
    "image_url": "/static/uploads/abc123def456.jpg",
    "category": "Milchprodukte",
    "tags": "bio,regional",
    "scan_count": 3,
    "last_scanned": "2025-11-26T10:30:00",
    "created_at": "2025-11-20T14:22:00"
  }
]
```

#### `POST /api/products`
Neues Produkt erstellen
```json
{
  "ean": "4025127020997",
  "name": "Milch",
  "expiry_date": "2025-12-01",
  "purchase_date": "2025-11-26",
  "location": "Kühlschrank",
  "quantity": 2,
  "weight_volume": "1L",
  "notes": "Bio-Qualität",
  "is_vegetarian": true,
  "is_vegan": false,
  "price": 1.29,
  "image_url": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
  "category": "Milchprodukte",
  "tags": "bio,regional"
}
```
**Response**: `201 Created` mit ID

**Besonderheit**: Base64-Bilder werden automatisch in `static/uploads/` gespeichert und die URL wird zu `/static/uploads/{uuid}.jpg` konvertiert.

#### `PUT /api/products/{id}`
Produkt aktualisieren (gleiche Felder wie POST)

**Besonderheit**: Alte Bilder werden automatisch gelöscht bei Ersetzung.

#### `DELETE /api/products/{id}`
Produkt löschen

**Wichtig**: 
- Produkt wird aus Datenbank entfernt
- Barcode-Verlauf bleibt **erhalten** (für Quick-Add)
- Bild-Datei wird gelöscht
- Metadaten werden in `barcode_history` aktualisiert

#### `POST /api/products/check-duplicate`
Duplikat-Check vor Hinzufügen
```json
{
  "ean": "4025127020997"
}
```
**Response**:
```json
{
  "exists": true,
  "product": { /* vollständiges Produkt-Objekt */ }
}
```

### Barcode-Scanning

#### `GET /api/scan/{ean}`
Produktinfo von Open Food Facts abrufen
```json
{
  "found": true,
  "name": "Milch 3.5% Frische Vollmilch",
  "image_url": "https://images.openfoodfacts.org/...",
  "quantity": "1L",
  "brands": "Weihenstephan",
  "category": "Milchprodukte"
}
```

**Automatische Aktionen:**
- Barcode-Verlauf wird aktualisiert
- Scan-Count wird erhöht
- Kategorie wird extrahiert
- Vegetarisch/Vegan wird erkannt

### Barcode-Verlauf (NEU!)

#### `GET /api/barcode-history?limit=20`
Scan-Verlauf abrufen (enthält auch gelöschte Produkte!)
```json
[
  {
    "id": 1,
    "ean": "4025127020997",
    "name": "Milch 3.5%",
    "category": "Milchprodukte",
    "weight_volume": "1L",
    "tags": "bio,regional",
    "is_vegetarian": 1,
    "is_vegan": 0,
    "scan_count": 5,
    "last_scanned": "2025-11-26T10:30:00"
  }
]
```

**Use Case**: Gelöschte Produkte können über Quick-Add mit allen ursprünglichen Daten wieder hinzugefügt werden.

### Einkaufsliste

#### `GET /api/shopping-list`
Alle Einkaufslisten-Einträge
```json
[
  {
    "id": 1,
    "name": "Milch",
    "quantity": 2,
    "category": "Milchprodukte",
    "checked": 0,
    "notes": "Bio",
    "created_at": "2025-11-26T09:00:00"
  }
]
```

#### `POST /api/shopping-list`
Artikel hinzufügen
```json
{
  "name": "Eier",
  "quantity": 12,
  "category": "Tierprodukte",
  "notes": "Freiland"
}
```

#### `PUT /api/shopping-list/{id}`
Artikel aktualisieren (z.B. abhaken)
```json
{
  "checked": 1
}
```

#### `DELETE /api/shopping-list/{id}`
Einzelnen Artikel löschen

#### `POST /api/shopping-list/generate`
Automatisch generieren
```json
{
  "items_added": 3,
  "message": "3 Artikel zur Einkaufsliste hinzugefügt"
}
```

Findet automatisch:
- Abgelaufene Produkte
- Produkte mit Menge ≤ 2

#### `DELETE /api/shopping-list/clear-checked`
Alle abgehakten Artikel löschen
```json
{
  "deleted": 5,
  "message": "5 erledigte Artikel gelöscht"
}
```

### Statistiken

#### `GET /api/statistics`
Basis-Statistiken
```json
{
  "total": 42,
  "expired": 3,
  "expiring_soon": 5,
  "total_value": 127.50,
  "by_location": {
    "Kühlschrank": 15,
    "Vorratsschrank": 20,
    "Gefrierschrank": 7
  }
}
```

#### `GET /api/statistics/advanced`
Erweiterte Statistiken
```json
{
  "waste_value": 12.50,
  "waste_count": 3,
  "category_breakdown": [
    {"category": "Milchprodukte", "count": 8},
    {"category": "Gemüse", "count": 12}
  ],
  "top_scanned": [
    {"name": "Milch 3.5%", "scan_count": 15},
    {"name": "Eier", "scan_count": 10}
  ],
  "weekly_additions": 8
}
```

## 🗄️ Datenbank-Schema

### Tabelle: `products`
Haupt-Produkttabelle mit allen Informationen
```sql
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ean TEXT,                      -- EAN-Barcode (8-13 Stellen)
    name TEXT NOT NULL,            -- Produktname (max 200 Zeichen)
    expiry_date TEXT,              -- Ablaufdatum (YYYY-MM-DD)
    purchase_date TEXT,            -- Kaufdatum (YYYY-MM-DD)
    location TEXT,                 -- Lagerort (max 100 Zeichen)
    quantity INTEGER DEFAULT 1,    -- Menge (1-9999)
    weight_volume TEXT,            -- Gewicht/Volumen (z.B. "1L", "500g")
    notes TEXT,                    -- Notizen (max 1000 Zeichen)
    is_vegetarian INTEGER DEFAULT 0,  -- Vegetarisch (0/1)
    is_vegan INTEGER DEFAULT 0,       -- Vegan (0/1)
    price REAL DEFAULT 0.0,           -- Preis in Euro
    image_url TEXT,                   -- Pfad zum Bild (/static/uploads/...)
    category TEXT,                    -- Kategorie (von API oder manuell)
    tags TEXT,                        -- Tags (kommasepariert)
    scan_count INTEGER DEFAULT 0,     -- Anzahl Scans
    last_scanned TEXT,                -- Letzter Scan (ISO-Format)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indizes für Performance
CREATE INDEX idx_expiry_date ON products(expiry_date);
CREATE INDEX idx_location ON products(location);
CREATE INDEX idx_name ON products(name);
```

### Tabelle: `barcode_history` (NEU!)
Persistente Speicherung aller Scans (bleibt nach Löschung erhalten)
```sql
CREATE TABLE barcode_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ean TEXT NOT NULL,                -- EAN-Barcode
    name TEXT,                        -- Produktname
    category TEXT,                    -- Kategorie
    weight_volume TEXT,               -- Gewicht/Volumen
    tags TEXT,                        -- Tags
    is_vegetarian INTEGER DEFAULT 0,  -- Vegetarisch
    is_vegan INTEGER DEFAULT 0,       -- Vegan
    scan_count INTEGER DEFAULT 1,     -- Anzahl Scans
    last_scanned TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Wichtig**: Diese Tabelle wird **nie** gelöscht, auch nicht beim Löschen von Produkten! Ermöglicht Quick-Add für gelöschte Produkte.

### Tabelle: `shopping_list`
Einkaufsliste mit manuellen und auto-generierten Einträgen
```sql
CREATE TABLE shopping_list (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,               -- Artikel-Name
    quantity INTEGER DEFAULT 1,       -- Menge
    category TEXT,                    -- Kategorie
    checked INTEGER DEFAULT 0,        -- Abgehakt (0/1)
    notes TEXT,                       -- Notizen
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🍓 Raspberry Pi Setup

### Empfohlene Hardware
- **Raspberry Pi 4** (2GB+ RAM empfohlen)
- **32GB+ SD-Karte** (Class 10 oder UHS-I)
- **Kamera-Modul** oder USB-Webcam (optional für Desktop-Modus)
- **Gehäuse mit Lüfter** (bei dauerhaftem Betrieb)

### Installation auf Raspberry Pi

1. **System aktualisieren**
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv -y
```

2. **Projekt kopieren**
```bash
cd /home/pi
# Projekt-Dateien hierher kopieren
cd HeimInventar
```

3. **Virtuelle Umgebung erstellen**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

4. **Server starten**

**Testing (Development):**
```bash
python app.py
```

**Production (24/7 mit Gunicorn):**
```bash
gunicorn -w 2 -b 0.0.0.0:5000 --timeout 120 app:app
# -w 2 = 2 Worker (für Pi Zero/3)
# -w 4 = 4 Worker (für Pi 4/5)
```

### Autostart einrichten (Systemd Service mit Gunicorn)

1. **Service-Datei erstellen**
```bash
sudo nano /etc/systemd/system/nexosync.service
```

2. **Konfiguration einfügen**
```ini
[Unit]
Description=NexoSync Smart Kitchen Inventory
After=network.target

[Service]
Type=notify
User=pi
WorkingDirectory=/home/pi/HeimInventar
Environment="PATH=/home/pi/HeimInventar/venv/bin"
ExecStart=/home/pi/HeimInventar/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Anpassungen je nach Raspberry Pi Modell:**
- **Pi Zero/3**: `-w 2` (2 Worker)
- **Pi 4 (2GB)**: `-w 3` (3 Worker)
- **Pi 4 (4GB+)**: `-w 4` (4 Worker)
- **Pi 5**: `-w 6` (6 Worker)

3. **Service aktivieren**
```bash
sudo systemctl daemon-reload
sudo systemctl enable nexosync
sudo systemctl start nexosync
sudo systemctl status nexosync
```

4. **Service-Befehle**
```bash
sudo systemctl stop nexosync      # Stoppen
sudo systemctl restart nexosync   # Neustarten
sudo journalctl -u nexosync -f    # Logs anzeigen
sudo systemctl status nexosync    # Status prüfen
```

### Performance-Optimierung für Raspberry Pi

**SQLite optimieren:**
```bash
sqlite3 inventory.db "VACUUM;"
sqlite3 inventory.db "ANALYZE;"
```

**Swap erweitern** (bei wenig RAM):
```bash
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# CONF_SWAPSIZE=1024
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

**Alte Bilder aufräumen** (optional):
```bash
# Bilder älter als 90 Tage löschen
find /home/pi/HeimInventar/static/uploads -type f -mtime +90 -delete
```

### Backup-Strategie

**Datenbank sichern:**
```bash
# Manuelles Backup
cp inventory.db inventory_backup_$(date +%Y%m%d).db

# Automatisches Backup (Crontab)
crontab -e
# Täglich um 3 Uhr
0 3 * * * cp /home/pi/HeimInventar/inventory.db /home/pi/backups/inventory_$(date +\%Y\%m\%d).db
```

**Bilder sichern:**
```bash
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz static/uploads/
```

### Kamera-Zugriff über HTTP

Moderne Browser benötigen HTTPS oder `localhost` für Kamera-Zugriff.

**Workaround für Android/Chrome:**
1. Öffne `chrome://flags/#unsafely-treat-insecure-origin-as-secure`
2. Füge `http://<RASPBERRY-PI-IP>:5000` hinzu
3. Flag aktivieren und Chrome neu starten

**Bessere Lösung: HTTPS mit Let's Encrypt** (siehe Sicherheitshinweise)

## 👨‍💻 Entwicklung

### Projektstruktur
```
HeimInventar/
├── app.py                    # Flask Backend (850+ Zeilen)
├── inventory.db             # SQLite Datenbank
├── requirements.txt         # Python Dependencies
├── README.md               # Diese Datei
├── static/
│   ├── css/
│   │   └── style.css       # Custom Styles (170+ Zeilen)
│   ├── js/
│   │   └── app.js          # Vue.js Frontend (500+ Zeilen)
│   └── uploads/            # Produkt-Bilder (automatisch erstellt)
└── templates/
    └── index.html          # Haupt-Template (900+ Zeilen)
```

### Debug-Modus aktivieren
```python
# In app.py (letzte Zeilen)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)  # debug=True
```

**Debug-Features:**
- Auto-Reload bei Code-Änderungen
- Detaillierte Fehler im Browser
- Flask Debug Toolbar (optional)

### Logging einrichten
```python
# Am Anfang von app.py hinzufügen
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('nexosync.log'),
        logging.StreamHandler()
    ]
)
```

### Datenbank direkt verwalten
```bash
# SQLite Shell öffnen
sqlite3 inventory.db

# Nützliche Befehle:
.tables                           # Tabellen anzeigen
.schema products                  # Schema anzeigen
SELECT * FROM products;           # Alle Produkte
SELECT * FROM barcode_history;    # Verlauf anzeigen
DELETE FROM products WHERE id=1;  # Produkt löschen
.exit                            # Beenden
```

### Frontend entwickeln
**Vue.js DevTools** (Chrome Extension) installieren für:
- Komponenten-Inspektion
- State-Management Debugging
- Event-Tracking

**Tailwind CSS Klassen nachschlagen:**
- https://tailwindcss.com/docs

### Testing

**Manuelles Testing:**
```bash
# Produkt hinzufügen
curl -X POST http://localhost:5000/api/products \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","quantity":1}'

# Produkte abrufen
curl http://localhost:5000/api/products

# Barcode scannen
curl http://localhost:5000/api/scan/4025127020997
```

**Datenbank resetten:**
```bash
rm inventory.db
python app.py  # Erstellt neue DB
```

## 🔄 Changelog

### v2.0 - "Persistence Update" (26. November 2025)
#### 🎉 Neue Features
- ✅ **Barcode-Verlauf mit vollständigen Metadaten**
  - Speichert Name, Kategorie, Tags, Diät-Flags
  - Persistenz auch nach Produkt-Löschung
  - Quick-Add Funktion für gelöschte Produkte
  
- ✅ **Dateisystem-basierte Bild-Speicherung**
  - Bilder in `static/uploads/` statt Datenbank
  - UUID-basierte Dateinamen
  - Automatische Löschung bei Ersetzung/Entfernung
  - Deutlich bessere Performance

- ✅ **Einkaufslisten-Generator**
  - Automatische Erkennung niedriger Bestände
  - Abgelaufene Produkte automatisch hinzufügen
  - Abhaken und Löschen erledigter Einkäufe

- ✅ **Erweiterte Statistiken**
  - Verschwendungs-Tracking
  - Kategorie-Breakdown
  - Top gescannte Produkte
  - Wöchentliche Trends

- ✅ **Kategorien & Tags Support**
  - Automatische Kategorisierung via Open Food Facts
  - Manuelle Tags für Organisation
  - Filter nach Kategorie

#### 🐛 Bugfixes
- Bild-Speicherung optimiert (keine Speicherprobleme mehr)
- Barcode-Verlauf bleibt nach Löschung erhalten
- Automatische Migrations für alle Tabellen

#### 🔧 Technische Verbesserungen
- 3-Tabellen-Architektur (products, shopping_list, barcode_history)
- Erweiterte API mit 15+ Endpoints
- Base64 → File-System Konvertierung
- Automatische Bild-Cleanup

### v1.0 - "Initial Release" (November 2025)
- ✅ Basis-Produktverwaltung
- ✅ Barcode-Scanner mit Open Food Facts
- ✅ Dark Mode (automatisch)
- ✅ Kamera-Integration
- ✅ Duplikat-Erkennung
- ✅ Mobile-First Design
- ✅ Filter & Suche
- ✅ Preis-Tracking
- ✅ Basis-Statistiken

## 🔐 Sicherheitshinweise

### Produktions-Deployment
**NICHT für öffentliches Internet ohne zusätzliche Sicherheit!**

Empfohlene Maßnahmen:
- **Reverse Proxy** (Nginx/Apache) mit HTTPS
- **Authentifizierung** (Basic Auth oder OAuth)
- **Firewall-Regeln** (nur lokales Netzwerk)
- **Rate Limiting** (gegen Brute-Force)

### Beispiel: Nginx mit Basic Auth
```nginx
server {
    listen 80;
    server_name nexosync.local;
    
    location / {
        auth_basic "NexoSync Login";
        auth_basic_user_file /etc/nginx/.htpasswd;
        
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### HTTPS mit Let's Encrypt
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d nexosync.example.com
```

## ❓ FAQ

**Q: Funktioniert das offline?**  
A: Ja, grundsätzlich. Nur der Barcode-Scanner benötigt Internet für Open Food Facts API. Bereits gespeicherte Produkte funktionieren offline.

**Q: Kann ich das mit mehreren Personen nutzen?**  
A: Ja, alle Geräte im gleichen Netzwerk können auf den Raspberry Pi zugreifen. Die Datenbank ist für mehrere gleichzeitige Nutzer ausgelegt.

**Q: Wie viele Produkte kann ich speichern?**  
A: Praktisch unbegrenzt. SQLite skaliert bis zu Millionen Einträge. Auf einem Raspberry Pi mit 32GB SD-Karte sind 10.000+ Produkte problemlos möglich.

**Q: Was passiert mit gelöschten Produkten?**  
A: Die Produkt-Daten werden aus der Haupttabelle entfernt, aber der Barcode-Verlauf bleibt erhalten. Du kannst gelöschte Produkte jederzeit wieder scannen und mit "Quick Add" hinzufügen.

**Q: Wie groß werden die Bilder?**  
A: Automatisch komprimiert auf ~50-200KB (max 400×400px, JPEG 0.7). Optimiert für Raspberry Pi Storage.

**Q: Kann ich eigene Kategorien erstellen?**  
A: Ja, beim manuellen Hinzufügen kannst du beliebige Kategorien und Tags eingeben. Die API-Kategorien werden automatisch erkannt.

**Q: Unterstützt das Barcode-Typen außer EAN?**  
A: Aktuell nur EAN-8, EAN-13 und kompatible Formate (UPC). Erweiterung für QR-Codes ist geplant.

**Q: Kann ich die Daten exportieren?**  
A: Die Datenbank ist SQLite-Standard. Export via:
```bash
sqlite3 inventory.db ".mode csv" ".output products.csv" "SELECT * FROM products;"
```

## 🤝 Contributing

Contributions sind willkommen! 

**Pull Requests bitte mit:**
- Beschreibung der Änderung
- Testing-Nachweis
- Code-Kommentare (Deutsch oder Englisch)

**Feature-Requests:**
- Issue öffnen mit [FEATURE] im Titel
- Use-Case beschreiben
- Mockups/Screenshots (optional)

## 📜 Lizenz

MIT License - Copyright (c) 2025 NexoSync

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software.

## 🙏 Credits

- **Open Food Facts** - Produktdaten-API
- **Tailwind CSS** - UI Framework
- **Vue.js** - Frontend Framework
- **Font Awesome** - Icons
- **HTML5-QRCode** - Barcode-Scanner Library

## 📞 Support

**Bei Problemen:**
1. Issues auf GitHub öffnen
2. Logs prüfen: `journalctl -u nexosync -f`
3. Debug-Modus aktivieren

---

**🏠 NexoSync - Dein smartes Zuhause beginnt hier!**

*Entwickelt mit ❤️ für smarte Haushalte | Optimiert für Raspberry Pi | Mobile-First Design | Open Source*

```
 _   _                 ____
| \ | | _____  _____ / ___| _   _ _ __   ___
|  \| |/ _ \ \/ / _ \___ \| | | | '_ \ / __|
| |\  |  __/>  < (_) |__) | |_| | | | | (__
|_| \_|\___/_/\_\___/____/ \__, |_| |_|\___|
                           |___/
```

**Viel Spaß beim Organisieren! 🚀🎉**
