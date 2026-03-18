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

from app.services.llm import get_available_models
from app.services.tts import get_curated_voices
from app.services.debate import get_debate, list_debates

router = APIRouter()


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
                "moderator_intro": source.config.moderator_intro,
                "moderator_summary": source.config.moderator_summary,
            }

    return request.app.state.templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "models": models,
            "voices": voices,
            "debates": debates[:10],
            "clone": clone_config,
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
