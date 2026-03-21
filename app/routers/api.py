"""API routes – debate management, models, voices, setup."""
from __future__ import annotations

import asyncio
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from app.config import settings, save_env, reload_settings
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

    # Separate text fields from file uploads
    text_fields = {}
    a_files = []
    b_files = []
    mod_files = []

    for key, value in form.multi_items():
        if key == "a_files" and hasattr(value, "read"):
            a_files.append(value)
        elif key == "b_files" and hasattr(value, "read"):
            b_files.append(value)
        elif key == "mod_files" and hasattr(value, "read"):
            mod_files.append(value)
        else:
            text_fields[key] = value

    req = StartDebateRequest(**text_fields)

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

    from app.services.documents import MAX_FILES_PER_ROLE
    for label, files in [("Debattant A", a_files), ("Debattant B", b_files), ("Moderator", mod_files)]:
        if len(files) > MAX_FILES_PER_ROLE:
            errors.append(f"{label}: Maximal {MAX_FILES_PER_ROLE} Dateien erlaubt.")

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

    # --- Process file uploads ---
    from app.services.documents import process_uploads, build_context_block, get_image_attachments

    a_docs = await process_uploads(a_files, req.language) if a_files else []
    b_docs = await process_uploads(b_files, req.language) if b_files else []
    mod_docs = await process_uploads(mod_files, req.language) if mod_files else []

    # Check for processing errors
    for docs, label in [(a_docs, "Debattant A"), (b_docs, "Debattant B"), (mod_docs, "Moderator")]:
        doc_errors = [f"{label}: {d.filename} – {d.error}" for d in docs if d.error]
        errors.extend(doc_errors)

    if errors:
        error_html = '<div class="notice notice-error">' + '<br>'.join(errors) + '</div>'
        return HTMLResponse(error_html, status_code=422)

    config = DebateConfig(
        topic=req.topic.strip(),
        language=req.language,
        num_rounds=req.num_rounds,
        max_tokens_per_turn=req.max_tokens,
        moderator_intro=req.wants_intro,
        moderator_summary=req.wants_summary,
        moderator_system_prompt=req.moderator_system_prompt.strip(),
        moderator_document_context=build_context_block(mod_docs, req.language),
        moderator_image_attachments=get_image_attachments(mod_docs),
        debater_a=Debater(
            name=req.a_name.strip(),
            model=req.a_model,
            voice=req.a_voice,
            position=req.a_position.strip(),
            system_prompt=req.a_system_prompt.strip(),
            document_context=build_context_block(a_docs, req.language),
            image_attachments=get_image_attachments(a_docs),
        ),
        debater_b=Debater(
            name=req.b_name.strip(),
            model=req.b_model,
            voice=req.b_voice,
            position=req.b_position.strip(),
            system_prompt=req.b_system_prompt.strip(),
            document_context=build_context_block(b_docs, req.language),
            image_attachments=get_image_attachments(b_docs),
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


# ---------------------------------------------------------------------------
# Setup endpoints
# ---------------------------------------------------------------------------

@router.post("/setup/test")
async def test_provider(request: Request):
    """Testet die Verbindung zu einem einzelnen LLM-Provider."""
    data = await request.json()
    provider = data.get("provider", "")

    if provider == "anthropic":
        key = data.get("anthropic_api_key", "").strip()
        if not key:
            return JSONResponse({"ok": False, "error": "Kein API-Key angegeben"})
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=key)
            client.models.list(limit=1)
            return JSONResponse({"ok": True})
        except Exception as e:
            return JSONResponse({"ok": False, "error": str(e)[:150]})

    elif provider == "openai":
        key = data.get("openai_api_key", "").strip()
        if not key:
            return JSONResponse({"ok": False, "error": "Kein API-Key angegeben"})
        try:
            import openai
            client = openai.OpenAI(api_key=key)
            client.models.list()
            return JSONResponse({"ok": True})
        except Exception as e:
            return JSONResponse({"ok": False, "error": str(e)[:150]})

    elif provider == "ollama":
        url = data.get("ollama_base_url", "http://localhost:11434").strip()
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{url}/api/tags")
                models = resp.json().get("models", [])
                return JSONResponse({"ok": True, "models": len(models)})
        except Exception as e:
            return JSONResponse({"ok": False, "error": f"Nicht erreichbar: {str(e)[:100]}"})

    return JSONResponse({"ok": False, "error": "Unbekannter Provider"})


@router.post("/setup")
async def save_setup(request: Request):
    """Speichert API-Keys in ~/.ki-arena/.env und lädt Settings neu."""
    data = await request.json()

    keys_to_save = {}
    if data.get("anthropic_api_key"):
        keys_to_save["ANTHROPIC_API_KEY"] = data["anthropic_api_key"].strip()
    if data.get("openai_api_key"):
        keys_to_save["OPENAI_API_KEY"] = data["openai_api_key"].strip()
    if data.get("ollama_base_url"):
        keys_to_save["OLLAMA_BASE_URL"] = data["ollama_base_url"].strip()

    if not keys_to_save:
        return JSONResponse({"ok": False, "error": "Keine Konfiguration angegeben."})

    try:
        save_env(keys_to_save)
        new_settings = reload_settings()

        # Prüfen ob jetzt mindestens ein Provider verfügbar ist
        has_llm = bool(new_settings.anthropic_api_key or new_settings.openai_api_key)
        if not has_llm:
            # Ollama-Check
            try:
                import httpx
                async with httpx.AsyncClient(timeout=3) as client:
                    resp = await client.get(f"{new_settings.ollama_base_url}/api/tags")
                    if resp.json().get("models"):
                        has_llm = True
            except Exception:
                pass

        if has_llm:
            request.app.state.needs_setup = False

        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"Fehler beim Speichern: {str(e)[:200]}"})
