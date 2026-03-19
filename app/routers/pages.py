"""
Seiten-Routes – rendert Jinja2 Templates für die Hauptnavigation.

Enthält:
- /            → Konfigurator (neue Debatte erstellen)
- /debate/{id} → Live-Ansicht einer laufenden/abgeschlossenen Debatte
- /player/{id} → Audio-Player mit Visualizer
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.config import settings
from app.services.llm import get_available_models
from app.services.tts import get_curated_voices
from app.services.debate import get_debate, list_debates

router = APIRouter()


@router.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    """Einrichtungsseite für API-Keys."""
    return request.app.state.templates.TemplateResponse(
        "setup.html",
        {
            "request": request,
            "current": {
                "anthropic_api_key": settings.anthropic_api_key,
                "openai_api_key": settings.openai_api_key,
                "ollama_base_url": settings.ollama_base_url,
            },
        },
    )


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, clone: str | None = None):
    """Startseite: Konfigurator und Debattenliste.

    Mit ?clone={debate_id} werden die Einstellungen einer
    bestehenden Debatte vorausgefüllt (Topic, Modelle, Stimmen, etc.).
    """
    models = await get_available_models()
    voices = get_curated_voices()
    debates = list_debates()

    # Clone: Einstellungen einer bestehenden Debatte übernehmen
    clone_config = None
    if clone:
        source = get_debate(clone)
        if source and source.config:
            clone_config = {
                "topic": source.config.topic,
                "language": source.config.language,
                "num_rounds": source.config.num_rounds,
                "max_tokens": source.config.max_tokens_per_turn,
                "a_name": source.config.debater_a.name,
                "a_model": source.config.debater_a.model,
                "a_voice": source.config.debater_a.voice,
                "a_position": source.config.debater_a.position,
                "b_name": source.config.debater_b.name,
                "b_model": source.config.debater_b.model,
                "b_voice": source.config.debater_b.voice,
                "b_position": source.config.debater_b.position,
                "a_system_prompt": source.config.debater_a.system_prompt,
                "b_system_prompt": source.config.debater_b.system_prompt,
                "moderator_system_prompt": source.config.moderator_system_prompt,
                "moderator_intro": source.config.moderator_intro,
                "moderator_summary": source.config.moderator_summary,
            }

    # Default system prompt templates for transparency in the UI
    default_prompts = {
        "de": {
            "debater_a": (
                'Du bist KI Alpha, ein eloquenter Debattenteilnehmer.\n'
                'Deine Position: Pro zum Thema "...".\n\n'
                'Regeln:\n'
                '- Argumentiere überzeugend und fundiert für deine Position.\n'
                '- Beziehe dich auf Argumente deines Gegenübers, wenn vorhanden.\n'
                '- Bleib sachlich, aber leidenschaftlich.\n'
                '- Halte dich kurz und prägnant (Länge abhängig von Einstellung).\n'
                '- Antworte auf Deutsch.\n'
                '- WICHTIG: Schließe deinen Beitrag IMMER mit einem vollständigen Satz ab. Brich niemals mitten im Satz ab.\n'
                '- WICHTIG: Beginne DIREKT mit deinen Argumenten. Schreibe KEINE Überschriften, '
                'Rundennummern, Positionsbezeichnungen oder Meta-Informationen wie '
                '"Eröffnungsstatement", "Pro-Antwort", "Runde 1" etc. Kein einleitender Titel – nur deine Argumente.'
            ),
            "debater_b": (
                'Du bist KI Beta, ein eloquenter Debattenteilnehmer.\n'
                'Deine Position: Contra zum Thema "...".\n\n'
                'Regeln:\n'
                '- Argumentiere überzeugend und fundiert für deine Position.\n'
                '- Beziehe dich auf Argumente deines Gegenübers, wenn vorhanden.\n'
                '- Bleib sachlich, aber leidenschaftlich.\n'
                '- Halte dich kurz und prägnant (Länge abhängig von Einstellung).\n'
                '- Antworte auf Deutsch.\n'
                '- WICHTIG: Schließe deinen Beitrag IMMER mit einem vollständigen Satz ab. Brich niemals mitten im Satz ab.\n'
                '- WICHTIG: Beginne DIREKT mit deinen Argumenten. Schreibe KEINE Überschriften, '
                'Rundennummern, Positionsbezeichnungen oder Meta-Informationen wie '
                '"Eröffnungsstatement", "Pro-Antwort", "Runde 1" etc. Kein einleitender Titel – nur deine Argumente.'
            ),
            "moderator": (
                '[Einleitung] Du bist ein professioneller Debattenmoderator. '
                'Formuliere eine knappe, spannende Einleitung für die folgende Debatte. Sprache: Deutsch.\n\n'
                '[Zusammenfassung] Du bist ein neutraler Debattenmoderator. '
                'Fasse die Debatte zusammen und bewerte die Argumente beider Seiten fair. Sprache: Deutsch.'
            ),
        },
        "en": {
            "debater_a": (
                'You are KI Alpha, an eloquent debate participant.\n'
                'Your position: Pro on the topic "...".\n\n'
                'Rules:\n'
                '- Argue convincingly and with solid evidence for your position.\n'
                '- Address your opponent\'s arguments when available.\n'
                '- Stay factual but passionate.\n'
                '- Keep it concise (length depends on setting).\n'
                '- Respond in English.\n'
                '- IMPORTANT: Always end with a complete sentence. Never stop mid-sentence.\n'
                '- IMPORTANT: Start DIRECTLY with your arguments. Do NOT write any headers, '
                'round numbers, position labels, or meta-information like "Opening statement", '
                '"Pro response", "Round 1" etc. No introductory title – only your arguments.'
            ),
            "debater_b": (
                'You are KI Beta, an eloquent debate participant.\n'
                'Your position: Contra on the topic "...".\n\n'
                'Rules:\n'
                '- Argue convincingly and with solid evidence for your position.\n'
                '- Address your opponent\'s arguments when available.\n'
                '- Stay factual but passionate.\n'
                '- Keep it concise (length depends on setting).\n'
                '- Respond in English.\n'
                '- IMPORTANT: Always end with a complete sentence. Never stop mid-sentence.\n'
                '- IMPORTANT: Start DIRECTLY with your arguments. Do NOT write any headers, '
                'round numbers, position labels, or meta-information like "Opening statement", '
                '"Pro response", "Round 1" etc. No introductory title – only your arguments.'
            ),
            "moderator": (
                '[Intro] You are a professional debate moderator. '
                'Write a concise, engaging introduction for the following debate. Language: English.\n\n'
                '[Summary] You are a neutral debate moderator. '
                'Summarize the debate and evaluate both sides\' arguments fairly. Language: English.'
            ),
        },
    }

    return request.app.state.templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "models": models,
            "voices": voices,
            "debates": debates[:10],
            "clone": clone_config,
            "default_prompts": default_prompts,
        },
    )


@router.get("/debate/{debate_id}", response_class=HTMLResponse)
async def debate_view(request: Request, debate_id: str):
    """Live-Ansicht einer Debatte mit WebSocket-Updates."""
    debate = get_debate(debate_id)
    if not debate:
        raise HTTPException(status_code=404, detail="Debatte nicht gefunden")
    return request.app.state.templates.TemplateResponse(
        "debate.html",
        {"request": request, "debate": debate},
    )


@router.get("/player/{debate_id}", response_class=HTMLResponse)
async def player_view(request: Request, debate_id: str):
    """Audio-Player: Sequenzielle Wiedergabe aller Debattenbeiträge."""
    debate = get_debate(debate_id)
    if not debate:
        raise HTTPException(status_code=404, detail="Debatte nicht gefunden")
    return request.app.state.templates.TemplateResponse(
        "player.html",
        {"request": request, "debate": debate},
    )
