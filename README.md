# ⚔ KI Arena

Zwei KIs debattieren live – mit TTS-Audio und animiertem Player. Alles in einer unified Web-App.

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

```bash
# 1. In den Projektordner wechseln
cd ki-arena

# 2. Dependencies installieren
uv sync

# 3. Environment konfigurieren
cp .env.example .env
# → Mindestens einen API-Key eintragen (oder Ollama lokal starten)

# 4. Server starten
uv run python -m app.main

# 5. Browser öffnen
open http://localhost:8000
```

Beim Start zeigt die App an, welche Provider verfügbar sind:

```
========================================================
  ⚔  KI Arena – Starting up
========================================================
  ✓  Anthropic API key found
  ⚠  OpenAI API key missing — GPT models unavailable
  ✓  Ollama erreichbar – 3 Modell(e): llama3:latest, ...

  📂  Debatten-Ordner: /pfad/zu/ki-arena/debates
  🌐  http://0.0.0.0:8000
========================================================
```

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
│   │   ├── debate.html       # Live-Ansicht + WebSocket-Client
│   │   ├── player.html       # Audio-Player mit Keyboard-Shortcuts
│   │   └── partials/
│   │       └── debate_turn.html
│   └── static/
│       ├── css/style.css     # Dark Arena Theme
│       └── js/arena.js       # Frontend-Utilities
├── debates/                  # Generierte Debatten (JSON + MP3)
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
**Lösung:** Trage mindestens einen Key in `.env` ein:
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

## Nächste Schritte

- [ ] YouTube-Export (HTML-Video mit Untertiteln)
- [ ] Debatte speichern/laden (JSON-Import/Export)
- [ ] Voting-System nach Debatte
- [ ] Custom System Prompts pro Debattant
- [ ] Ollama Model-Discovery mit Pull-Option im UI
- [ ] Docker-Compose Setup
