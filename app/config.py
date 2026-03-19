"""
Zentrale Konfiguration für KI Arena.

Alle Einstellungen werden aus Umgebungsvariablen oder einer .env-Datei geladen.
Siehe .env.example für eine Vorlage mit allen verfügbaren Optionen.
"""
from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings


# Zentrales Konfigurationsverzeichnis im Home-Ordner
CONFIG_DIR = Path.home() / ".ki-arena"


def _find_env_file() -> str | None:
    """Sucht die .env-Datei: zuerst im CWD, dann in ~/.ki-arena/."""
    cwd_env = Path(".env")
    if cwd_env.is_file():
        return str(cwd_env)
    config_env = CONFIG_DIR / ".env"
    if config_env.is_file():
        return str(config_env)
    return None


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
    debug: bool = False

    # ── Pfade ──────────────────────────────────────────────────
    # Hier werden generierte Debatten gespeichert (JSON + MP3-Audio).
    debates_dir: Path = CONFIG_DIR / "debates"

    model_config = {
        "env_file": _find_env_file(),
        "env_file_encoding": "utf-8",
    }

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


def save_env(keys: dict[str, str]) -> None:
    """Schreibt API-Keys in ~/.ki-arena/.env (erstellt Verzeichnis bei Bedarf)."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    env_path = CONFIG_DIR / ".env"

    # Bestehende .env lesen falls vorhanden
    existing: dict[str, str] = {}
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()

    # Neue Werte übernehmen (leere Werte entfernen vorhandene Keys nicht)
    for k, v in keys.items():
        if v:
            existing[k] = v

    # Datei schreiben
    lines = [f"{k}={v}" for k, v in existing.items()]
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def reload_settings() -> Settings:
    """Lädt Settings neu aus .env und aktualisiert das bestehende Singleton in-place.

    Da andere Module 'from app.config import settings' verwenden und damit
    eine eigene Referenz halten, muss das bestehende Objekt mutiert werden.
    """
    fresh = Settings(
        _env_file=_find_env_file(),
        _env_file_encoding="utf-8",
    )
    # Alle Felder in-place aktualisieren
    for field_name in Settings.model_fields:
        setattr(settings, field_name, getattr(fresh, field_name))
    settings.debates_dir.mkdir(parents=True, exist_ok=True)
    return settings


# Singleton – wird beim Import erstellt
settings = Settings()
settings.debates_dir.mkdir(parents=True, exist_ok=True)
