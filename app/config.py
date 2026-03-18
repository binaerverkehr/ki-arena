"""
Zentrale Konfiguration für KI Arena.

Alle Einstellungen werden aus Umgebungsvariablen oder einer .env-Datei geladen.
Siehe .env.example für eine Vorlage mit allen verfügbaren Optionen.
"""
from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """App-Konfiguration. Werte werden automatisch aus .env geladen."""

    # ── LLM-Provider API-Keys ──────────────────────────────────
    # Nur Modelle für konfigurierte Keys werden im UI angezeigt.
    anthropic_api_key: str = ""       # Für Claude-Modelle (console.anthropic.com)
    openai_api_key: str = ""          # Für GPT-Modelle (platform.openai.com)
    ollama_base_url: str = "http://localhost:11434"  # Lokal, kein Key nötig

    # ── Server ─────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True                # Hot-Reload bei Code-Änderungen

    # ── Pfade ──────────────────────────────────────────────────
    # Hier werden generierte Debatten gespeichert (JSON + MP3-Audio).
    debates_dir: Path = Path("./debates")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def available_providers(self) -> list[str]:
        """Gibt eine Liste der konfigurierten LLM-Provider zurück."""
        providers = []
        if self.anthropic_api_key:
            providers.append("anthropic")
        if self.openai_api_key:
            providers.append("openai")
        # Ollama ist immer verfügbar (Verbindungsfehler treten erst zur Laufzeit auf)
        providers.append("ollama")
        return providers


# Singleton – wird beim Import erstellt
settings = Settings()
settings.debates_dir.mkdir(parents=True, exist_ok=True)
