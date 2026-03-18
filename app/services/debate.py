"""
Debate Engine – Orchestriert mehrrundige LLM-Debatten mit TTS-Audio.

Ablauf einer Debatte:
1. Moderator-Intro (optional) → LLM generiert Einleitung
2. Debattenrunden → Abwechselnd argumentieren Debattant A und B
3. Moderator-Zusammenfassung (optional) → LLM bewertet die Argumente
4. TTS-Generierung → Alle Texte werden als MP3-Audio vertont
5. Speicherung → JSON-Metadaten + Audio-Dateien in debates/{id}/

Fortschritts-Updates werden über eine Callback-Funktion (on_update)
an den WebSocket-Handler weitergeleitet.
"""
from __future__ import annotations

import json
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Awaitable
from uuid import uuid4

from app.config import settings
from app.services import llm, tts


class DebateStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    GENERATING_AUDIO = "generating_audio"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class Debater:
    name: str
    model: str
    voice: str
    position: str  # e.g. "pro" or "contra"
    system_prompt: str = ""


@dataclass
class Turn:
    round_num: int
    debater_name: str
    model: str
    position: str
    content: str
    audio_file: str | None = None
    subs_file: str | None = None
    tokens_used: int = 0
    timestamp: str = ""


@dataclass
class DebateConfig:
    topic: str
    language: str  # "de" or "en"
    debater_a: Debater
    debater_b: Debater
    num_rounds: int = 3
    max_tokens_per_turn: int = 1024
    moderator_intro: bool = True
    moderator_summary: bool = True
    moderator_system_prompt: str = ""


@dataclass
class Debate:
    id: str = field(default_factory=lambda: uuid4().hex[:12])
    config: DebateConfig | None = None
    status: DebateStatus = DebateStatus.PENDING
    turns: list[Turn] = field(default_factory=list)
    intro_text: str = ""
    intro_audio: str | None = None
    intro_subs: str | None = None
    summary_text: str = ""
    summary_audio: str | None = None
    summary_subs: str | None = None
    error: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def output_dir(self) -> Path:
        return settings.debates_dir / self.id

    def to_dict(self) -> dict:
        """Serialisiert die komplette Debatte inkl. Config für JSON-Speicherung."""
        result = {
            "id": self.id,
            "status": self.status.value,
            "created_at": self.created_at,
            "intro_text": self.intro_text,
            "intro_audio": self.intro_audio,
            "intro_subs": self.intro_subs,
            "summary_text": self.summary_text,
            "summary_audio": self.summary_audio,
            "summary_subs": self.summary_subs,
            "error": self.error,
            "turns": [
                {
                    "round_num": t.round_num,
                    "debater_name": t.debater_name,
                    "model": t.model,
                    "position": t.position,
                    "content": t.content,
                    "audio_file": t.audio_file,
                    "subs_file": t.subs_file,
                    "tokens_used": t.tokens_used,
                }
                for t in self.turns
            ],
        }
        if self.config:
            result["config"] = {
                "topic": self.config.topic,
                "language": self.config.language,
                "num_rounds": self.config.num_rounds,
                "max_tokens_per_turn": self.config.max_tokens_per_turn,
                "moderator_intro": self.config.moderator_intro,
                "moderator_summary": self.config.moderator_summary,
                "debater_a": {
                    "name": self.config.debater_a.name,
                    "model": self.config.debater_a.model,
                    "voice": self.config.debater_a.voice,
                    "position": self.config.debater_a.position,
                },
                "debater_b": {
                    "name": self.config.debater_b.name,
                    "model": self.config.debater_b.model,
                    "voice": self.config.debater_b.voice,
                    "position": self.config.debater_b.position,
                },
            }
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "Debate":
        """Rekonstruiert eine Debatte aus einem gespeicherten JSON-Dict."""
        config = None
        if "config" in data:
            c = data["config"]
            config = DebateConfig(
                topic=c["topic"],
                language=c.get("language", "de"),
                num_rounds=c.get("num_rounds", 3),
                max_tokens_per_turn=c.get("max_tokens_per_turn", 1024),
                moderator_intro=c.get("moderator_intro", True),
                moderator_summary=c.get("moderator_summary", True),
                debater_a=Debater(**c["debater_a"]),
                debater_b=Debater(**c["debater_b"]),
            )
        elif "topic" in data:
            # Fallback für alte JSON-Dateien ohne verschachtelte Config
            config = DebateConfig(
                topic=data["topic"],
                language="de",
                debater_a=Debater(name="KI Alpha", model="unknown", voice="", position="Pro"),
                debater_b=Debater(name="KI Beta", model="unknown", voice="", position="Contra"),
            )

        turns = [
            Turn(
                round_num=t["round_num"],
                debater_name=t["debater_name"],
                model=t.get("model", ""),
                position=t.get("position", ""),
                content=t["content"],
                audio_file=t.get("audio_file"),
                subs_file=t.get("subs_file"),
                tokens_used=t.get("tokens_used", 0),
            )
            for t in data.get("turns", [])
        ]

        return cls(
            id=data["id"],
            config=config,
            status=DebateStatus(data.get("status", "completed")),
            turns=turns,
            intro_text=data.get("intro_text", ""),
            intro_audio=data.get("intro_audio"),
            intro_subs=data.get("intro_subs"),
            summary_text=data.get("summary_text", ""),
            summary_audio=data.get("summary_audio"),
            summary_subs=data.get("summary_subs"),
            error=data.get("error", ""),
            created_at=data.get("created_at", ""),
        )


# In-memory store for active debates
_debates: dict[str, Debate] = {}


def get_debate(debate_id: str) -> Debate | None:
    return _debates.get(debate_id)


def list_debates() -> list[Debate]:
    return sorted(_debates.values(), key=lambda d: d.created_at, reverse=True)


def load_debates_from_disk() -> int:
    """Lädt alle gespeicherten Debatten aus dem debates-Ordner.

    Wird beim App-Start aufgerufen, damit vergangene Debatten
    sofort sichtbar sind (Startseiten-Liste, Player, etc.).

    Returns:
        Anzahl erfolgreich geladener Debatten.
    """
    loaded = 0
    if not settings.debates_dir.exists():
        return 0

    for debate_dir in settings.debates_dir.iterdir():
        if not debate_dir.is_dir():
            continue
        json_file = debate_dir / "debate.json"
        if not json_file.exists():
            continue
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            debate = Debate.from_dict(data)
            _debates[debate.id] = debate
            loaded += 1
        except Exception as e:
            print(f"  ⚠  Konnte Debatte {debate_dir.name} nicht laden: {e}")

    return loaded


def _length_hint(max_tokens: int, lang: str) -> str:
    """Erzeugt eine konkrete Längenvorgabe passend zum Token-Limit."""
    if lang == "de":
        if max_tokens <= 128:
            return "Antworte in maximal 2-3 Sätzen. Fasse dich extrem kurz."
        if max_tokens <= 256:
            return "Antworte in maximal 3-5 Sätzen (ein kurzer Absatz)."
        if max_tokens <= 512:
            return "Halte dich kurz und prägnant (max. 1-2 Absätze pro Runde)."
        return "Halte dich kurz und prägnant (max. 2-3 Absätze pro Runde)."
    else:
        if max_tokens <= 128:
            return "Reply in 2-3 sentences maximum. Be extremely brief."
        if max_tokens <= 256:
            return "Reply in 3-5 sentences maximum (one short paragraph)."
        if max_tokens <= 512:
            return "Keep it concise (max 1-2 paragraphs per round)."
        return "Keep it concise (max 2-3 paragraphs per round)."


def _build_system_prompt(debater: Debater, config: DebateConfig) -> str:
    """Baut den System-Prompt für einen Debattanten – sprachabhängig.

    Wenn debater.system_prompt gesetzt ist, wird er als vollständiger
    System-Prompt verwendet. Andernfalls wird der Standard-Prompt erzeugt.
    """
    if debater.system_prompt:
        return debater.system_prompt

    length = _length_hint(config.max_tokens_per_turn, config.language)

    if config.language == "de":
        return f"""Du bist {debater.name}, ein eloquenter Debattenteilnehmer.
Deine Position: {debater.position} zum Thema "{config.topic}".

Regeln:
- Argumentiere überzeugend und fundiert für deine Position.
- Beziehe dich auf Argumente deines Gegenübers, wenn vorhanden.
- Bleib sachlich, aber leidenschaftlich.
- {length}
- Antworte auf Deutsch.
- WICHTIG: Schließe deinen Beitrag IMMER mit einem vollständigen Satz ab. Brich niemals mitten im Satz ab.
- WICHTIG: Beginne DIREKT mit deinen Argumenten. Schreibe KEINE Überschriften, Rundennummern, Positionsbezeichnungen oder Meta-Informationen wie "Eröffnungsstatement", "Pro-Antwort", "Runde 1" etc. Kein einleitender Titel – nur deine Argumente."""
    else:
        return f"""You are {debater.name}, an eloquent debate participant.
Your position: {debater.position} on the topic "{config.topic}".

Rules:
- Argue convincingly and with solid evidence for your position.
- Address your opponent's arguments when available.
- Stay factual but passionate.
- {length}
- Respond in English.
- IMPORTANT: Always end with a complete sentence. Never stop mid-sentence.
- IMPORTANT: Start DIRECTLY with your arguments. Do NOT write any headers, round numbers, position labels, or meta-information like "Opening statement", "Pro response", "Round 1" etc. No introductory title – only your arguments."""


def _build_messages(debate: Debate, current_debater: Debater, round_num: int, config: DebateConfig) -> list[dict]:
    """Baut die Konversationshistorie aus Sicht des aktuellen Debattanten.

    Eigene bisherige Beiträge → role: "assistant"
    Gegnerische Beiträge → role: "user" (damit das LLM darauf reagiert)

    Wichtig: Die Anthropic API erwartet strikt abwechselnde user/assistant
    Messages. Deshalb wird der Aufforderungs-Prompt direkt ans Ende des
    letzten user-Blocks gehängt statt als separate Message.
    """
    is_de = config.language == "de"
    messages: list[dict] = []

    for turn in debate.turns:
        if turn.debater_name == current_debater.name:
            messages.append({"role": "assistant", "content": turn.content})
        else:
            messages.append({"role": "user", "content": f"[{turn.debater_name}]: {turn.content}"})

    if not messages:
        # Erster Beitrag überhaupt – Kick-off
        if is_de:
            messages.append({
                "role": "user",
                "content": f"Die Debatte beginnt. Thema: {config.topic}. Du eröffnest als {current_debater.position}. Lege los!",
            })
        else:
            messages.append({
                "role": "user",
                "content": f"The debate begins. Topic: {config.topic}. You open as {current_debater.position}. Go!",
            })
    else:
        # Folge-Runde: Wenn die letzte Message schon "user" ist (vom Gegner),
        # hängen wir den Runden-Hinweis an dieselbe Message an, um
        # keine zwei aufeinanderfolgenden user-Messages zu erzeugen.
        if is_de:
            continuation = f"\n\n[Moderator]: Runde {round_num}. Antworte auf die Argumente deines Gegenübers und bringe neue Punkte."
        else:
            continuation = f"\n\n[Moderator]: Round {round_num}. Respond to your opponent's arguments and bring new points."

        if messages[-1]["role"] == "user":
            messages[-1]["content"] += continuation
        else:
            # Letzte Message war eigene (assistant) → neue user-Message
            messages.append({"role": "user", "content": continuation.strip()})

    return messages


# Preferred moderator voices per language (neutral-sounding, distinct from typical debater choices)
_MODERATOR_VOICES = {
    "de": ["de-DE-KillianNeural", "de-AT-JonasNeural", "de-DE-KatjaNeural", "de-AT-IngridNeural"],
    "en": ["en-GB-RyanNeural", "en-US-DavisNeural", "en-GB-SoniaNeural", "en-US-AriaNeural"],
}


def _pick_moderator_voice(config: DebateConfig) -> str:
    """Pick a moderator voice that differs from both debaters' voices."""
    used = {config.debater_a.voice, config.debater_b.voice}
    candidates = _MODERATOR_VOICES.get(config.language, _MODERATOR_VOICES["de"])
    for voice in candidates:
        if voice not in used:
            return voice
    # Fallback: pick any curated voice for the language that's not used
    from app.services.tts import get_curated_voices
    for voice_id in get_curated_voices(config.language):
        if voice_id not in used:
            return voice_id
    # Last resort: just use debater A's voice
    return config.debater_a.voice


async def run_debate(
    config: DebateConfig,
    on_update: Callable[[Debate, str], Awaitable[None]] | None = None,
) -> Debate:
    """Run a full debate and return the completed Debate object."""
    debate = Debate(config=config)
    debate.output_dir.mkdir(parents=True, exist_ok=True)
    _debates[debate.id] = debate

    async def notify(msg: str):
        if on_update:
            await on_update(debate, msg)

    try:
        debate.status = DebateStatus.RUNNING
        await notify("debate_started")

        # --- Moderator Intro ---
        if config.moderator_intro:
            await notify("generating_intro")
            lang = "Deutsch" if config.language == "de" else "English"
            mod_system = config.moderator_system_prompt or f"Du bist ein professioneller Debattenmoderator. Formuliere eine knappe, spannende Einleitung für die folgende Debatte. Sprache: {lang}."
            intro_resp = await llm.generate(
                model=config.debater_a.model,  # use debater A's model for intro
                system=mod_system,
                messages=[{
                    "role": "user",
                    "content": f"Thema: {config.topic}\n\nTeilnehmer:\n- {config.debater_a.name} (Position: {config.debater_a.position})\n- {config.debater_b.name} (Position: {config.debater_b.position})\n\nAnzahl Runden: {config.num_rounds}",
                }],
                max_tokens=512,
            )
            debate.intro_text = intro_resp.content
            await notify("intro_generated")

        # --- Debate Rounds ---
        for round_num in range(1, config.num_rounds + 1):
            for debater in [config.debater_a, config.debater_b]:
                await notify(f"round_{round_num}_{debater.name}_thinking")

                system = _build_system_prompt(debater, config)
                messages = _build_messages(debate, debater, round_num, config)

                try:
                    resp = await llm.generate(
                        model=debater.model,
                        system=system,
                        messages=messages,
                        max_tokens=config.max_tokens_per_turn,
                    )
                    content = resp.content
                    tokens = resp.tokens_used
                except Exception as e:
                    # Einzelner LLM-Fehler: Debatte geht weiter mit Fehlermeldung
                    lang = config.language
                    if lang == "de":
                        content = f"[Fehler bei der Generierung: {type(e).__name__}: {str(e)[:100]}]"
                    else:
                        content = f"[Generation error: {type(e).__name__}: {str(e)[:100]}]"
                    tokens = 0
                    await notify(f"round_{round_num}_{debater.name}_error")

                turn = Turn(
                    round_num=round_num,
                    debater_name=debater.name,
                    model=debater.model,
                    position=debater.position,
                    content=content,
                    tokens_used=tokens,
                    timestamp=datetime.now().isoformat(),
                )
                debate.turns.append(turn)
                await notify(f"round_{round_num}_{debater.name}_done")

        # --- Moderator Summary ---
        if config.moderator_summary:
            await notify("generating_summary")
            all_arguments = "\n\n".join(
                f"[Runde {t.round_num} – {t.debater_name} ({t.position})]: {t.content}"
                for t in debate.turns
            )
            lang = "Deutsch" if config.language == "de" else "English"
            summary_system = config.moderator_system_prompt or f"Du bist ein neutraler Debattenmoderator. Fasse die Debatte zusammen und bewerte die Argumente beider Seiten fair. Sprache: {lang}."
            summary_resp = await llm.generate(
                model=config.debater_a.model,
                system=summary_system,
                messages=[{
                    "role": "user",
                    "content": f"Thema: {config.topic}\n\nDebattenverlauf:\n{all_arguments}\n\nBitte fasse zusammen.",
                }],
                max_tokens=1024,
            )
            debate.summary_text = summary_resp.content
            await notify("summary_generated")

        # --- TTS Audio Generation ---
        debate.status = DebateStatus.GENERATING_AUDIO
        await notify("generating_audio")

        # Pick a moderator voice that differs from both debaters
        moderator_voice = _pick_moderator_voice(config)

        # Intro audio
        if debate.intro_text:
            try:
                await tts.synthesize(
                    debate.intro_text,
                    moderator_voice,
                    debate.output_dir / "intro.mp3",
                )
                debate.intro_audio = "intro.mp3"
                debate.intro_subs = "intro.subs.json"
                await notify("intro_audio_done")
            except Exception as e:
                print(f"  ⚠  TTS-Fehler (Intro): {e}")
                await notify("intro_audio_skipped")

        # Turn audio
        for i, turn in enumerate(debate.turns):
            try:
                debater = config.debater_a if turn.debater_name == config.debater_a.name else config.debater_b
                filename = f"turn_{i:02d}_r{turn.round_num}_{debater.name.lower().replace(' ', '_')}.mp3"
                await tts.synthesize(
                    turn.content,
                    debater.voice,
                    debate.output_dir / filename,
                )
                turn.audio_file = filename
                turn.subs_file = filename.replace(".mp3", ".subs.json")
                await notify(f"audio_turn_{i}_done")
            except Exception as e:
                print(f"  ⚠  TTS-Fehler (Turn {i}): {e}")
                await notify(f"audio_turn_{i}_skipped")

        # Summary audio
        if debate.summary_text:
            try:
                await tts.synthesize(
                    debate.summary_text,
                    moderator_voice,
                    debate.output_dir / "summary.mp3",
                )
                debate.summary_audio = "summary.mp3"
                debate.summary_subs = "summary.subs.json"
                await notify("summary_audio_done")
            except Exception as e:
                print(f"  ⚠  TTS-Fehler (Summary): {e}")
                await notify("summary_audio_skipped")

        debate.status = DebateStatus.COMPLETED
        await notify("completed")

    except Exception as e:
        debate.status = DebateStatus.ERROR
        debate.error = str(e)
        await notify(f"error: {e}")

    # Immer speichern – auch bei Fehlern, damit Teilergebnisse erhalten bleiben
    try:
        metadata = debate.to_dict()
        (debate.output_dir / "debate.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as save_err:
        print(f"  ✗  Konnte Debatte {debate.id} nicht speichern: {save_err}")

    return debate
