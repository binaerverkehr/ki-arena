"""
KI Arena – Hauptanwendung.

Startet den FastAPI-Server mit:
- Jinja2-Templates für die HTML-Seiten (HTMX-basiert)
- REST API für Debattensteuerung
- WebSocket für Live-Fortschritts-Updates
- Static Files (CSS/JS) und Audio-Serving aus dem debates-Ordner
"""
from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.routers import pages, api, ws


BASE_DIR = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Startup / Shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate environment on startup and print helpful status."""
    print("\n" + "=" * 56)
    print("  ⚔  KI Arena – Starting up")
    print("=" * 56)

    # Check providers
    providers = settings.available_providers()
    has_any_llm = False

    if settings.anthropic_api_key:
        print("  ✓  Anthropic API key found")
        has_any_llm = True
    else:
        print("  ⚠  Anthropic API key missing — Claude models unavailable")
        print("     → Set ANTHROPIC_API_KEY in .env")

    if settings.openai_api_key:
        print("  ✓  OpenAI API key found")
        has_any_llm = True
    else:
        print("  ⚠  OpenAI API key missing — GPT models unavailable")
        print("     → Set OPENAI_API_KEY in .env")

    # Check Ollama
    import httpx
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            models = resp.json().get("models", [])
            names = [m["name"] for m in models]
            print(f"  ✓  Ollama erreichbar – {len(names)} Modell(e): {', '.join(names[:5])}")
            has_any_llm = True
    except Exception:
        print(f"  ⚠  Ollama nicht erreichbar ({settings.ollama_base_url})")
        print("     → Starte Ollama oder passe OLLAMA_BASE_URL in .env an")

    if not has_any_llm:
        print("\n  ✗  KEIN LLM-Provider verfügbar!")
        print("     Mindestens ein API-Key oder Ollama wird benötigt.")
        print("     → Kopiere .env.example nach .env und trage Keys ein.\n")
        sys.exit(1)

    print(f"\n  📂  Debatten-Ordner: {settings.debates_dir.resolve()}")

    # Load past debates from disk
    from app.services.debate import load_debates_from_disk
    loaded = load_debates_from_disk()
    if loaded:
        print(f"  📜  {loaded} gespeicherte Debatte(n) geladen")
    else:
        print(f"  📜  Keine gespeicherten Debatten gefunden")

    print(f"  🌐  http://{settings.host}:{settings.port}")
    print("=" * 56 + "\n")

    yield  # App runs

    print("\n⚔  KI Arena – Shutting down\n")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="KI Arena", version="0.1.0", lifespan=lifespan)

# Static files & templates
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/audio", StaticFiles(directory=str(settings.debates_dir)), name="audio")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.state.templates = templates

# Routers
app.include_router(pages.router)
app.include_router(api.router)
app.include_router(ws.router)


# ---------------------------------------------------------------------------
# Global error handler
# ---------------------------------------------------------------------------

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return HTMLResponse(
        content="""
        <html><head><title>404 – KI Arena</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;800&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="/static/css/style.css"></head>
        <body style="display:flex;align-items:center;justify-content:center;min-height:100vh">
        <div style="text-align:center;max-width:500px;padding:2rem">
            <p style="font-size:4rem;margin-bottom:0.5rem;opacity:0.4">⚔</p>
            <h1 style="font-family:'Outfit',sans-serif;font-weight:800;font-size:2rem;margin-bottom:0.5rem">404 – Nicht gefunden</h1>
            <p style="color:var(--text-muted,#7a7a94);margin-bottom:1.5rem">
                Diese Debatte existiert nicht oder wurde noch nicht gestartet.
            </p>
            <a href="/" style="color:var(--accent-a,#6c5ce7);text-decoration:none;font-weight:600">
                ← Zur Startseite
            </a>
        </div></body></html>
        """,
        status_code=404,
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    return HTMLResponse(
        content=f"""
        <html><head><title>Fehler – KI Arena</title>
        <link rel="stylesheet" href="/static/css/style.css"></head>
        <body style="display:flex;align-items:center;justify-content:center;min-height:100vh">
        <div style="text-align:center;max-width:500px;padding:2rem">
            <h1 style="font-size:2rem;margin-bottom:1rem">⚠ Etwas ist schiefgelaufen</h1>
            <p style="color:var(--text-muted,#999);margin-bottom:1.5rem">{str(exc)[:200]}</p>
            <a href="/" style="color:var(--accent-a,#6c5ce7)">← Zurück zur Startseite</a>
        </div></body></html>
        """,
        status_code=500,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run():
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    run()
