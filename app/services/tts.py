"""
TTS-Service – Text-to-Speech via edge-tts.

Nutzt die kostenlose Microsoft Edge TTS API (benötigt Internetverbindung).
Generiert MP3-Audio-Dateien für Debattenbeiträge.

Stimmen sind nach Sprache kuratiert (Deutsch/Englisch).
Für die vollständige Liste: await list_all_voices()
"""
from __future__ import annotations

import re
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
    word_boundaries: list[dict] = field(default_factory=list)  # [{offset_ms, duration_ms, text}, ...]


def _clean_for_tts(text: str) -> str:
    """Remove markdown formatting and other artifacts that TTS would read aloud."""
    # Remove bold/italic markers: **text**, *text*, __text__, _text_
    text = re.sub(r'\*{1,3}', '', text)
    text = re.sub(r'_{1,3}', '', text)
    # Remove markdown headers: ## Header
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Remove markdown links: [text](url) → text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Remove leftover special chars that sound odd when spoken
    text = re.sub(r'[`~]', '', text)
    # Collapse multiple whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


async def synthesize(text: str, voice: str, output_path: Path) -> TTSResult:
    """Generate an MP3 file from text using edge-tts.

    Uses streaming to capture WordBoundary events for precise subtitle timing.
    Each boundary contains offset_ms, duration_ms, and the spoken text fragment.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    text = _clean_for_tts(text)
    communicate = edge_tts.Communicate(text, voice)

    sentence_boundaries: list[dict] = []
    audio_chunks: list[bytes] = []

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_chunks.append(chunk["data"])
        elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
            # offset/duration come in 100ns ticks – convert to milliseconds
            sentence_boundaries.append({
                "offset_ms": chunk["offset"] / 10_000,
                "duration_ms": chunk["duration"] / 10_000,
                "text": chunk["text"],
            })

    # Interpolate word-level timings from sentence boundaries
    # Weight each word's duration by its character count (longer words take
    # longer to speak).  This is much more accurate than even distribution.
    word_boundaries: list[dict] = []
    for sb in sentence_boundaries:
        words = sb["text"].split()
        if not words:
            continue
        sent_offset = sb["offset_ms"]
        sent_duration = sb["duration_ms"]
        total_chars = sum(len(w) for w in words)
        if total_chars == 0:
            total_chars = 1
        cursor = sent_offset
        for w in words:
            word_dur = (len(w) / total_chars) * sent_duration
            word_boundaries.append({
                "offset_ms": round(cursor, 1),
                "duration_ms": round(word_dur, 1),
                "text": w,
            })
            cursor += word_dur

    # Write audio data
    with open(output_path, "wb") as f:
        for c in audio_chunks:
            f.write(c)

    # Write subtitle JSON alongside the audio file
    subs_path = output_path.with_suffix(".subs.json")
    import json
    subs_path.write_text(
        json.dumps(word_boundaries, ensure_ascii=False),
        encoding="utf-8",
    )

    # Duration estimate from last word boundary (more accurate than word-count heuristic)
    if word_boundaries:
        last = word_boundaries[-1]
        duration_est = (last["offset_ms"] + last["duration_ms"]) / 1000
    else:
        word_count = len(text.split())
        duration_est = (word_count / 150) * 60

    return TTSResult(
        audio_path=output_path,
        voice=voice,
        duration_estimate=duration_est,
        word_boundaries=word_boundaries,
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
