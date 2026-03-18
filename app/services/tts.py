"""
TTS-Service – Text-to-Speech via edge-tts.

Nutzt die kostenlose Microsoft Edge TTS API (benötigt Internetverbindung).
Generiert MP3-Audio-Dateien für Debattenbeiträge.

Stimmen sind nach Sprache kuratiert (Deutsch/Englisch).
Für die vollständige Liste: await list_all_voices()
"""
from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass, field

import edge_tts

# ---------------------------------------------------------------------------
# Voice registry – curated voices for debates
# ---------------------------------------------------------------------------

VOICES: dict[str, dict] = {
    # German
    "de-DE-ConradNeural": {"label": "Conrad (DE, männlich)", "lang": "de"},
    "de-DE-KillianNeural": {"label": "Killian (DE, männlich)", "lang": "de"},
    "de-DE-AmalaNeural": {"label": "Amala (DE, weiblich)", "lang": "de"},
    "de-DE-KatjaNeural": {"label": "Katja (DE, weiblich)", "lang": "de"},
    "de-AT-JonasNeural": {"label": "Jonas (AT, männlich)", "lang": "de"},
    "de-AT-IngridNeural": {"label": "Ingrid (AT, weiblich)", "lang": "de"},
    # English
    "en-US-GuyNeural": {"label": "Guy (US, male)", "lang": "en"},
    "en-US-JennyNeural": {"label": "Jenny (US, female)", "lang": "en"},
    "en-GB-RyanNeural": {"label": "Ryan (GB, male)", "lang": "en"},
    "en-GB-SoniaNeural": {"label": "Sonia (GB, female)", "lang": "en"},
    "en-US-AriaNeural": {"label": "Aria (US, female)", "lang": "en"},
    "en-US-DavisNeural": {"label": "Davis (US, male)", "lang": "en"},
}


@dataclass
class TTSResult:
    audio_path: Path
    voice: str
    duration_estimate: float = 0.0  # rough estimate in seconds


async def synthesize(text: str, voice: str, output_path: Path) -> TTSResult:
    """Generate an MP3 file from text using edge-tts."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))

    # Rough duration estimate: ~150 words/min for TTS
    word_count = len(text.split())
    duration_est = (word_count / 150) * 60

    return TTSResult(
        audio_path=output_path,
        voice=voice,
        duration_estimate=duration_est,
    )


async def list_all_voices() -> list[dict]:
    """Fetch all available edge-tts voices."""
    voices = await edge_tts.list_voices()
    return voices


def get_curated_voices(lang: str | None = None) -> dict[str, dict]:
    """Return curated voice selection, optionally filtered by language."""
    if lang:
        return {k: v for k, v in VOICES.items() if v["lang"] == lang}
    return VOICES
