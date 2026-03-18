"""API routes – debate management, models, voices."""
from __future__ import annotations

import asyncio
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from app.services.llm import get_available_models
from app.services.tts import get_curated_voices
from app.services.debate import (
    DebateConfig, DebateStatus, Debater, Debate, run_debate, get_debate, list_debates,
)

router = APIRouter(prefix="/api")


class StartDebateRequest(BaseModel):
    """Formular-Daten vom Konfigurator.

    Hinweis zu Checkboxen: HTML-Formulare senden bei deaktivierten
    Checkboxen keinen Wert. Deshalb werden moderator_intro/summary
    als Optional[str] empfangen – "true" wenn angehakt, None wenn nicht.
    """

    topic: str
    language: str = "de"
    num_rounds: int = 3
    max_tokens: int = 1024
    # Debater A
    a_name: str = "KI Alpha"
    a_model: str = ""
    a_voice: str = "de-DE-ConradNeural"
    a_position: str = "Pro"
    a_system_prompt: str = ""
    # Debater B
    b_name: str = "KI Beta"
    b_model: str = ""
    b_voice: str = "de-DE-AmalaNeural"
    b_position: str = "Contra"
    b_system_prompt: str = ""
    # Moderator
    moderator_system_prompt: str = ""
    # Options – Checkboxen: "true" wenn angehakt, None/fehlend wenn nicht
    moderator_intro: str | None = None
    moderator_summary: str | None = None

    @property
    def wants_intro(self) -> bool:
        return self.moderator_intro is not None

    @property
    def wants_summary(self) -> bool:
        return self.moderator_summary is not None


# Active WebSocket connections per debate
_ws_connections: dict[str, list] = {}


def register_ws(debate_id: str, ws):
    _ws_connections.setdefault(debate_id, []).append(ws)


def unregister_ws(debate_id: str, ws):
    conns = _ws_connections.get(debate_id, [])
    if ws in conns:
        conns.remove(ws)


async def _broadcast(debate: Debate, event: str):
    """Send update to all connected WebSockets for this debate."""
    debate_id = debate.id
    conns = _ws_connections.get(debate_id, [])
    data = {"event": event, "debate": debate.to_dict()}
    import json
    msg = json.dumps(data, ensure_ascii=False)
    for ws in conns[:]:
        try:
            await ws.send_text(msg)
        except Exception:
            conns.remove(ws)


@router.post("/debate/start")
async def start_debate(request: Request):
    form = await request.form()
    req = StartDebateRequest(**dict(form))
    # --- Server-side validation ---
    errors: list[str] = []
    if not req.topic or len(req.topic.strip()) < 10:
        errors.append("Das Thema muss mindestens 10 Zeichen lang sein.")
    if not req.a_model:
        errors.append("Bitte wähle ein Modell für Debattant A.")
    if not req.b_model:
        errors.append("Bitte wähle ein Modell für Debattant B.")
    if not req.a_name.strip() or not req.b_name.strip():
        errors.append("Beide Debattanten brauchen einen Namen.")
    if req.num_rounds < 1 or req.num_rounds > 10:
        errors.append("Anzahl Runden muss zwischen 1 und 10 liegen.")

    if errors:
        error_html = '<div class="notice notice-error">' + '<br>'.join(errors) + '</div>'
        return HTMLResponse(error_html, status_code=422)

    # --- Check that selected models are actually available ---
    from app.services.llm import get_available_models
    available = await get_available_models()
    for label, model_id in [("Debattant A", req.a_model), ("Debattant B", req.b_model)]:
        if model_id not in available:
            return HTMLResponse(
                f'<div class="notice notice-error">Modell <code>{model_id}</code> für {label} ist nicht verfügbar. '
                f'Prüfe deine API-Keys in <code>.env</code>.</div>',
                status_code=422,
            )

    config = DebateConfig(
        topic=req.topic.strip(),
        language=req.language,
        num_rounds=req.num_rounds,
        max_tokens_per_turn=req.max_tokens,
        moderator_intro=req.wants_intro,
        moderator_summary=req.wants_summary,
        moderator_system_prompt=req.moderator_system_prompt.strip(),
        debater_a=Debater(
            name=req.a_name.strip(),
            model=req.a_model,
            voice=req.a_voice,
            position=req.a_position.strip(),
            system_prompt=req.a_system_prompt.strip(),
        ),
        debater_b=Debater(
            name=req.b_name.strip(),
            model=req.b_model,
            voice=req.b_voice,
            position=req.b_position.strip(),
            system_prompt=req.b_system_prompt.strip(),
        ),
    )

    # Run debate in background
    async def run_and_broadcast():
        await run_debate(config, on_update=_broadcast)

    asyncio.create_task(run_and_broadcast())

    # Return debate ID immediately (HTMX will redirect)
    debate = None
    # Wait briefly for debate to be registered
    await asyncio.sleep(0.3)
    from app.services.debate import _debates
    # Find the latest debate with this topic
    for d in sorted(_debates.values(), key=lambda x: x.created_at, reverse=True):
        if d.config and d.config.topic == req.topic.strip():
            debate = d
            break

    if debate:
        return HTMLResponse(
            f'<div hx-redirect="/debate/{debate.id}"></div>',
            headers={"HX-Redirect": f"/debate/{debate.id}"},
        )
    return HTMLResponse(
        '<div class="notice notice-error">Debatte konnte nicht gestartet werden. Prüfe die Server-Logs.</div>',
        status_code=500,
    )


@router.get("/debate/{debate_id}/status")
async def debate_status(debate_id: str):
    debate = get_debate(debate_id)
    if not debate:
        return JSONResponse({"error": "not found"}, status_code=404)
    return JSONResponse(debate.to_dict())


@router.get("/debate/{debate_id}/turn-partial/{turn_idx}")
async def turn_partial(request: Request, debate_id: str, turn_idx: int):
    """Return a single turn as an HTMX partial."""
    debate = get_debate(debate_id)
    if not debate or turn_idx >= len(debate.turns):
        return HTMLResponse("")
    turn = debate.turns[turn_idx]
    return request.app.state.templates.TemplateResponse(
        "partials/debate_turn.html",
        {"request": request, "turn": turn, "debate": debate, "idx": turn_idx},
    )


@router.get("/models")
async def available_models():
    models = await get_available_models()
    return JSONResponse(models)


@router.delete("/debate/{debate_id}")
async def delete_debate(request: Request, debate_id: str):
    """Löscht eine Debatte (In-Memory + Dateien auf Disk).

    Verhalten je nach Kontext:
    - Aus der Debattenliste (HX-Target auf Element): Element wird entfernt
    - Aus der Detailseite (HX-Target="body"): Redirect zur Startseite
    """
    import shutil
    from app.services.debate import _debates

    debate = get_debate(debate_id)
    if not debate:
        return JSONResponse({"error": "not found"}, status_code=404)

    # Nicht löschen wenn noch aktiv
    if debate.status in (DebateStatus.RUNNING, DebateStatus.GENERATING_AUDIO):
        return HTMLResponse(
            '<div class="notice notice-error">Laufende Debatten können nicht gelöscht werden.</div>',
            status_code=409,
        )

    # Aus Memory entfernen
    _debates.pop(debate_id, None)

    # Dateien löschen
    if debate.output_dir.exists():
        shutil.rmtree(debate.output_dir, ignore_errors=True)

    # Wenn von der Liste: Element entfernen (leerer Response)
    hx_target = request.headers.get("hx-target", "")
    if hx_target and hx_target != "body":
        return HTMLResponse("")  # Element verschwindet aus der Liste

    # Sonst: Redirect zur Startseite
    return HTMLResponse("", headers={"HX-Redirect": "/"})


@router.get("/voices")
async def available_voices(lang: str | None = None):
    voices = get_curated_voices(lang)
    return JSONResponse(voices)
