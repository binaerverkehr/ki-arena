# ⚔ KI Arena

Zwei KIs debattieren live – mit TTS-Audio und animiertem Player. Alles in einer unified Web-App.

> **Von [Jay Imdahl](https://jayimdahl.de/)** — [YouTube: @binaerverkehr](https://www.youtube.com/@binaerverkehr/featured) | [Website](https://jayimdahl.de/)

| Konfigurator | Debatte | Player |
|:---:|:---:|:---:|
| ![Konfigurator](docs/screenshots/configurator.png) | ![Debatte](docs/screenshots/debate.png) | ![Player](docs/screenshots/player.png) |

## Video-Tutorial (DE)

[![Video-Tutorial](https://img.youtube.com/vi/Wl0gBK_iSIc/0.jpg)](https://www.youtube.com/watch?v= Wl0gBK_iSIc)

## Features

- **Konfigurator** – Thema, Modelle, Stimmen, Runden, Positionen – alles im Browser
- **Live-Debatte** – WebSocket-basierte Fortschrittsanzeige während die KIs debattieren
- **Multi-Provider** – Anthropic (Claude), OpenAI (GPT-4o), Ollama (lokal)
- **TTS-Audio** – edge-tts generiert MP3s für jeden Debattenbeitrag
- **Audio-Player** – Sequenzieller Player mit Visualizer, Auto-Advance, Keyboard-Shortcuts
- **Moderator** – Optionales Intro & Zusammenfassung durch KI-Moderator

## Tech Stack

| Komponente | Technologie |
|---|---|
| Backend | FastAPI (async, WebSocket) |
| Frontend | HTMX + Jinja2 Templates |
| TTS | edge-tts (Microsoft Edge voices, kostenlos) |
| LLMs | anthropic SDK, openai SDK, Ollama HTTP API |
| Tooling | Python 3.12+, uv |

## Quickstart

### Option A: Als Paket installieren (empfohlen)

```bash
# 1. Installieren (einmalig)
pipx install ki-arena        # oder: uv tool install ki-arena

# 2. Starten — Browser öffnet sich automatisch
ki-arena
```

Beim ersten Start erscheint eine **Einrichtungsseite im Browser**, auf der du deine API-Keys eingeben kannst. Keine `.env`-Datei nötig.

### Option B: Aus dem Repository

```bash
# 1. In den Projektordner wechseln
cd ki-arena

# 2. Dependencies installieren
uv sync

# 3. Server starten — Browser öffnet sich automatisch
uv run python -m app.main
```

API-Keys können über die Einrichtungsseite im Browser (`/setup`) oder wie bisher über eine `.env`-Datei konfiguriert werden.

### Startup-Ausgabe

Beim Start zeigt die App an, welche Provider verfügbar sind:

```
========================================================
  ⚔  KI Arena – Starting up
========================================================
  ✓  Anthropic API key found
  ⚠  OpenAI API key missing — GPT models unavailable
  ✓  Ollama erreichbar – 3 Modell(e): llama3:latest, ...

  📂  Debatten-Ordner: ~/.ki-arena/debates
  🌐  http://localhost:8000
========================================================
```

## Ausführliche Anleitung für Einsteiger (macOS & Windows)

Falls du noch nie mit Python oder der Kommandozeile gearbeitet hast, folge dieser Schritt-für-Schritt-Anleitung.

### Schritt 1: Terminal / Kommandozeile öffnen

**macOS:**
1. Drücke `Cmd + Leertaste` (Spotlight-Suche öffnet sich)
2. Tippe `Terminal` ein und drücke `Enter`

**Windows:**
1. Drücke `Windows-Taste + R`
2. Tippe `cmd` ein und drücke `Enter`
3. Alternativ: Suche im Startmenü nach „Eingabeaufforderung" oder „PowerShell"

> Im Folgenden werden alle Befehle in diesem Terminal/dieser Kommandozeile eingegeben.

### Schritt 2: Python installieren

KI Arena benötigt **Python 3.12 oder neuer**.

**Prüfen, ob Python bereits installiert ist:**
```bash
python3 --version
```
Wenn eine Versionsnummer wie `Python 3.12.x` erscheint, ist Python bereits installiert. Weiter mit Schritt 3.

**macOS – Python installieren:**

*Option A: Über die offizielle Website*
1. Gehe zu https://www.python.org/downloads/
2. Klicke auf „Download Python 3.12.x" (die große gelbe Schaltfläche)
3. Öffne die heruntergeladene `.pkg`-Datei und folge dem Installationsassistenten
4. Starte das Terminal neu und prüfe mit `python3 --version`

*Option B: Über Homebrew (falls Homebrew installiert ist)*
```bash
brew install python@3.12
```

**Windows – Python installieren:**
1. Gehe zu https://www.python.org/downloads/
2. Klicke auf „Download Python 3.12.x"
3. Öffne die heruntergeladene `.exe`-Datei
4. **Wichtig:** Setze im Installationsfenster unbedingt den Haken bei **„Add python.exe to PATH"** (ganz unten im Fenster)
5. Klicke auf „Install Now"
6. Schließe die Eingabeaufforderung und öffne sie neu
7. Prüfe mit `python --version` (unter Windows ohne `3`)

### Schritt 3: `uv` installieren (Python-Paketmanager)

`uv` ist ein moderner Python-Paketmanager, der alle Abhängigkeiten automatisch installiert.

**macOS:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
Danach Terminal schließen und neu öffnen, damit der Befehl `uv` verfügbar ist.

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
Danach Eingabeaufforderung schließen und neu öffnen.

**Prüfen, ob die Installation geklappt hat:**
```bash
uv --version
```

### Schritt 4: KI Arena herunterladen

Falls du das Projekt als ZIP-Datei erhalten hast:
1. Entpacke die ZIP-Datei (Doppelklick auf macOS, Rechtsklick → „Alle extrahieren" auf Windows)
2. Merke dir den Ordnerpfad (z.B. `Downloads/ki-arena`)

Falls du Git installiert hast:
```bash
git clone https://github.com/binaerverkehr/ki-arena.git
```

Wechsle im Terminal in den Projektordner:

**macOS:**
```bash
cd ~/Downloads/ki-arena
```

**Windows:**
```cmd
cd %USERPROFILE%\Downloads\ki-arena
```

> **Tipp:** Du kannst den Ordner auch per Drag & Drop ins Terminal ziehen, um den Pfad einzufügen.

### Schritt 5: Abhängigkeiten installieren

Dieser Befehl installiert automatisch alle benötigten Python-Pakete:
```bash
uv sync
```

Das dauert beim ersten Mal ca. 1–2 Minuten. Wenn alles klappt, erscheint keine Fehlermeldung.

### Schritt 6: API-Key besorgen und eintragen

Die KI Arena braucht Zugang zu einem KI-Sprachmodell. Du hast drei Optionen:

---

#### Option A: Anthropic (Claude) – empfohlen

1. Gehe zu https://console.anthropic.com/
2. Erstelle ein kostenloses Konto (E-Mail + Bestätigung)
3. Gehe zu **Settings → API Keys** (oder direkt: https://console.anthropic.com/settings/keys)
4. Klicke auf **„Create Key"**
5. Gib dem Key einen Namen (z.B. „KI Arena") und klicke auf **„Create Key"**
6. **Kopiere den Key sofort** – er wird nur einmal angezeigt! Er beginnt mit `sk-ant-api03-...`

> **Kosten:** Anthropic bietet ein kostenloses Startguthaben. Danach fallen geringe Kosten pro Debatte an (ca. $0.01–0.10 je nach Modell und Länge). Du musst eine Zahlungsmethode hinterlegen, um das kostenlose Guthaben zu nutzen.

---

#### Option B: OpenAI (GPT-4o)

1. Gehe zu https://platform.openai.com/
2. Erstelle ein Konto oder melde dich an
3. Gehe zu **API Keys** (oder direkt: https://platform.openai.com/api-keys)
4. Klicke auf **„Create new secret key"**
5. Gib dem Key einen Namen und klicke auf **„Create secret key"**
6. **Kopiere den Key sofort** – er beginnt mit `sk-...`

> **Kosten:** Ähnlich wie Anthropic – geringes Startguthaben, dann Pay-per-Use. Zahlungsmethode erforderlich.

---

#### Option C: Ollama (kostenlos & lokal, kein API-Key nötig)

Ollama lässt KI-Modelle direkt auf deinem Computer laufen – komplett kostenlos und ohne Internet (nach dem Download).

1. Gehe zu https://ollama.com/download
2. Lade die Version für dein Betriebssystem herunter und installiere sie
3. Öffne ein **neues** Terminal-Fenster und starte Ollama:
   ```bash
   ollama serve
   ```
4. Öffne ein **weiteres** Terminal-Fenster und lade ein Modell herunter:
   ```bash
   ollama pull llama3
   ```
   (Das Modell ist ca. 4 GB groß – braucht etwas Zeit.)

> **Hinweis:** Ollama braucht einen Computer mit mindestens 8 GB RAM. Auf älteren oder schwächeren Geräten kann es langsam sein.

---

#### API-Key eintragen

**Am einfachsten: Über die Web-Oberfläche**

Starte die App (siehe Schritt 7) — beim ersten Start öffnet sich automatisch die Einrichtungsseite im Browser. Dort trägst du deinen API-Key ein und klickst auf „Speichern & Starten". Fertig!

Die Keys werden sicher in `~/.ki-arena/.env` gespeichert.

**Alternativ: Manuell per `.env`-Datei**

```bash
# macOS:
cp .env.example .env && open -e .env

# Windows:
copy .env.example .env && notepad .env
```

Beispiel:
```
ANTHROPIC_API_KEY=sk-ant-api03-dein-key-hier-einfügen
```

> **Wichtig:** Die `.env`-Datei enthält geheime Schlüssel. Teile sie niemals mit anderen und lade sie nicht ins Internet hoch.

### Schritt 7: KI Arena starten

```bash
uv run python -m app.main
```

Wenn alles funktioniert, öffnet sich automatisch dein Browser mit der KI Arena.

Falls kein API-Key konfiguriert ist, erscheint die Einrichtungsseite — trage dort deinen Key ein und klicke auf „Speichern & Starten".

Falls der Browser sich nicht automatisch öffnet, gehe manuell zu: **http://localhost:8000**

### Nächstes Mal starten

Wenn du die KI Arena später erneut starten willst, brauchst du nur zwei Schritte:

1. Terminal öffnen und in den Projektordner wechseln:
   ```bash
   cd ~/Downloads/ki-arena    # macOS
   cd %USERPROFILE%\Downloads\ki-arena    # Windows
   ```
2. Server starten:
   ```bash
   uv run python -m app.main
   ```

Falls du Ollama nutzt: Stelle sicher, dass `ollama serve` in einem separaten Terminal-Fenster läuft.

---

## Projektstruktur

```
ki-arena/
├── app/
│   ├── main.py              # FastAPI App + Startup-Checks + Error-Handler
│   ├── config.py             # pydantic-settings (.env-basiert)
│   ├── services/
│   │   ├── llm.py            # LLM-Provider (Anthropic, OpenAI, Ollama)
│   │   ├── tts.py            # edge-tts Wrapper mit kuratierten Stimmen
│   │   └── debate.py         # Debate Engine (Runden-Orchestrierung)
│   ├── routers/
│   │   ├── pages.py          # Template-Routes (/, /debate, /player)
│   │   ├── api.py            # REST API + HTMX Partials
│   │   └── ws.py             # WebSocket für Live-Updates
│   ├── templates/
│   │   ├── base.html         # Layout (HTMX, Fonts, Navigation)
│   │   ├── index.html        # Konfigurator mit Validierung
│   │   ├── setup.html        # Einrichtungsseite für API-Keys
│   │   ├── debate.html       # Live-Ansicht + WebSocket-Client
│   │   ├── player.html       # Audio-Player mit Keyboard-Shortcuts
│   │   └── partials/
│   │       └── debate_turn.html
│   └── static/
│       ├── css/style.css     # Dark Arena Theme
│       └── js/arena.js       # Frontend-Utilities
├── debates/                  # Generierte Debatten (JSON + MP3) – oder ~/.ki-arena/debates/
├── pyproject.toml
├── .env.example
└── README.md
```

## Ablauf

1. **Konfigurieren** → Thema, Modelle, Stimmen, Runden wählen
2. **Starten** → Debatte läuft asynchron im Hintergrund
3. **Live verfolgen** → WebSocket pusht Fortschritts-Updates in Echtzeit
4. **Anhören** → Audio-Player spielt alle Beiträge sequenziell ab

## Audio-Player Keyboard-Shortcuts

| Taste | Funktion |
|---|---|
| `Space` | Play / Pause |
| `←` / `→` | Vorheriges / Nächstes Segment |
| `↑` / `↓` | Lauter / Leiser |
| `Home` / `End` | Zum Anfang / Ende |
| `M` | Stummschalten ein/aus |

## Troubleshooting

### „Keine LLM-Modelle verfügbar"
→ Es ist kein API-Key konfiguriert und Ollama ist nicht erreichbar.
**Lösung:** Öffne die Einstellungen unter `/setup` im Browser und trage mindestens einen API-Key ein. Alternativ per `.env`-Datei:
```bash
# Option A: Anthropic
ANTHROPIC_API_KEY=sk-ant-api03-...

# Option B: OpenAI
OPENAI_API_KEY=sk-...

# Option C: Ollama (kein Key nötig)
# Stelle sicher, dass Ollama läuft: ollama serve
```

### App startet nicht / Port belegt
```bash
# Anderen Port nutzen:
PORT=8080 uv run python -m app.main

# Oder prüfen, was Port 8000 belegt:
lsof -i :8000
```

### Ollama-Modelle tauchen nicht im Dropdown auf
→ Stelle sicher, dass Ollama läuft und erreichbar ist:
```bash
# Ollama starten
ollama serve

# Modell installieren (falls noch nicht geschehen)
ollama pull llama3

# Testen
curl http://localhost:11434/api/tags
```

### TTS-Fehler / Keine Audio-Dateien
→ `edge-tts` braucht eine Internetverbindung (nutzt Microsoft Edge Cloud-Stimmen).
**Offline?** Dann werden Debatten ohne Audio generiert – die Texte sind trotzdem verfügbar.

### Debatte bleibt bei „Running" hängen
→ Lade die Seite neu. Falls die Debatte einen Fehler hatte, wird dieser in der Debattenansicht angezeigt. Häufige Ursachen:
- API Rate-Limit erreicht (warte kurz, dann erneut versuchen)
- Ungültiger API-Key
- Ollama-Modell nicht installiert

### macOS: Python 3.14 / ensurepip Problem
Wenn du Python 3.14 beta nutzt und Probleme mit `uv sync` hast:
```bash
# Explizit Python 3.12 nutzen:
uv python install 3.12
uv sync --python 3.12
```

## Mitmachen

Du hast eine Idee, einen Bug gefunden oder möchtest ein Feature beitragen? Dann freue ich mich über deine Beteiligung!

- **Feature-Requests & Bugs** — Erstelle ein [Issue auf GitHub](https://github.com/binaerverkehr/ki-arena/issues)
- **Pull Requests** — Fork das Repo, erstelle einen Branch und schick einen PR
- **Feedback** — Schreib mir auf [YouTube](https://www.youtube.com/@binaerverkehr/featured) oder über meine [Website](https://jayimdahl.de/)

---

Gefällt dir KI Arena? [![Buy Me a Coffee](docs/assets/bmc-button.png)](https://buymeacoffee.com/binaerverkehr)
