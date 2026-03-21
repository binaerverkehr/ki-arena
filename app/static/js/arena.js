/**
 * KI Arena – Frontend Utilities
 *
 * Handles:
 * - Client-side form validation before HTMX submission
 * - Dynamic voice filtering based on language selection
 * - Duration estimate calculator
 * - Loading state on form submit
 */

document.addEventListener('DOMContentLoaded', function () {

    // ─── Form Validation ─────────────────────────────────────────
    // Prevents HTMX from firing if the form is incomplete.
    // Shows inline error messages to guide the user.

    const form = document.getElementById('debateForm');
    const topicEl = document.getElementById('topic');
    const msgEl = document.getElementById('validation-msg');

    if (form) {
        form.addEventListener('htmx:configRequest', function (e) {
            if (!topicEl) return;
            const topic = topicEl.value.trim();

            if (!topic) {
                e.preventDefault();
                showValidation('Bitte gib ein Debattenthema ein.');
                topicEl.focus();
                return;
            }
            if (topic.length < 10) {
                e.preventDefault();
                showValidation('Das Thema sollte mindestens 10 Zeichen lang sein – formuliere es etwas konkreter.');
                topicEl.focus();
                return;
            }

            hideValidation();
        });
    }

    // Hide validation on input
    topicEl?.addEventListener('input', hideValidation);

    function showValidation(msg) {
        if (!msgEl) return;
        msgEl.textContent = msg;
        msgEl.style.display = 'block';
    }

    function hideValidation() {
        if (msgEl) msgEl.style.display = 'none';
    }

    // ─── Loading State ───────────────────────────────────────────
    // Disables the submit button and shows a spinner while
    // the HTMX request is in flight.

    document.addEventListener('htmx:beforeRequest', function (e) {
        const btn = document.getElementById('submitBtn');
        if (!btn || !e.detail.elt.closest('#debateForm')) return;

        btn.disabled = true;
        btn.innerHTML = [
            '<span class="spinner" style="width:18px;height:18px;border-width:2px;',
            'display:inline-block;vertical-align:middle;margin-right:8px"></span>',
            'Debatte wird gestartet…'
        ].join('');
    });

    // Re-enable button if the request fails
    document.addEventListener('htmx:afterRequest', function (e) {
        const btn = document.getElementById('submitBtn');
        if (!btn || !e.detail.elt.closest('#debateForm')) return;

        if (e.detail.failed || e.detail.xhr?.status >= 400) {
            btn.disabled = false;
            btn.innerHTML = '<span class="btn-icon">⚔</span> Debatte starten';
            showValidation('Fehler beim Starten der Debatte. Prüfe deine API-Keys und versuche es erneut.');
        }
    });

    // ─── Voice Filtering ─────────────────────────────────────────
    // When the language changes, fetches matching voices from the
    // API and updates both voice dropdowns.

    const langSelect = document.getElementById('language');

    langSelect?.addEventListener('change', async function () {
        const lang = this.value;

        try {
            const resp = await fetch(`/api/voices?lang=${lang}`);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const voices = await resp.json();

            document.querySelectorAll('.voice-select').forEach(function (sel) {
                const current = sel.value;
                sel.innerHTML = '';

                for (const [key, v] of Object.entries(voices)) {
                    const opt = document.createElement('option');
                    opt.value = key;
                    opt.textContent = v.label;
                    if (key === current) opt.selected = true;
                    sel.appendChild(opt);
                }

                // If the current selection is no longer valid, pick the first
                if (!voices[current] && sel.options.length > 0) {
                    sel.selectedIndex = 0;
                }
            });
        } catch (err) {
            console.warn('Stimmen konnten nicht geladen werden:', err);
        }
    });

    // ─── Duration Estimate ───────────────────────────────────────
    // Shows a rough time estimate based on rounds × tokens.
    // Helps users understand how long the debate will take.

    const roundsEl = document.getElementById('num_rounds');
    const tokensEl = document.getElementById('max_tokens');
    const estimateEl = document.getElementById('estimateText');

    function updateEstimate() {
        if (!roundsEl || !tokensEl || !estimateEl) return;

        const rounds = parseInt(roundsEl.value) || 3;
        const tokens = parseInt(tokensEl.value) || 1024;

        // Rough model: each turn takes ~10-20s for LLM + ~10s for TTS
        // Longer token limits = slower generation
        const tokenFactor = tokens > 2048 ? 1.5 : tokens > 1024 ? 1.2 : 1;
        const turnsTotal = rounds * 2;                      // 2 debaters per round
        const llmSec = turnsTotal * 15 * tokenFactor;       // ~15s per LLM call
        const ttsSec = turnsTotal * 10 * tokenFactor;       // ~10s per TTS
        const overheadSec = 30;                             // intro + summary + overhead
        const totalSec = llmSec + ttsSec + overheadSec;

        const minMin = Math.max(1, Math.floor(totalSec / 60));
        const maxMin = Math.ceil(totalSec * 1.5 / 60);

        estimateEl.textContent =
            `Geschätzte Dauer: ~${minMin}–${maxMin} Minuten (${rounds} Runden, ${turnsTotal} Beiträge + TTS)`;
    }

    roundsEl?.addEventListener('change', updateEstimate);
    tokensEl?.addEventListener('change', updateEstimate);

    // Initial estimate on page load
    updateEstimate();

    // ─── System Prompt Preview ────────────────────────────────────
    // Shows the actual default system prompt as placeholder text,
    // dynamically updated when name, position, topic, or language change.

    const promptTemplates = {
        de: {
            debater: (name, position, topic) =>
`Du bist ${name}, ein eloquenter Debattenteilnehmer.
Deine Position: ${position} zum Thema "${topic}".

Regeln:
- Argumentiere überzeugend und fundiert für deine Position.
- Beziehe dich auf Argumente deines Gegenübers, wenn vorhanden.
- Bleib sachlich, aber leidenschaftlich.
- Halte dich kurz und prägnant (Länge abhängig von Einstellung).
- Antworte auf Deutsch.
- WICHTIG: Schließe deinen Beitrag IMMER mit einem vollständigen Satz ab. Brich niemals mitten im Satz ab.
- WICHTIG: Beginne DIREKT mit deinen Argumenten. Schreibe KEINE Überschriften, Rundennummern, Positionsbezeichnungen oder Meta-Informationen wie "Eröffnungsstatement", "Pro-Antwort", "Runde 1" etc. Kein einleitender Titel – nur deine Argumente.`,
            moderator:
`[Einleitung] Du bist ein professioneller Debattenmoderator. Formuliere eine knappe, spannende Einleitung für die folgende Debatte. Sprache: Deutsch.

[Zusammenfassung] Du bist ein neutraler Debattenmoderator. Fasse die Debatte zusammen und bewerte die Argumente beider Seiten fair. Sprache: Deutsch.`,
        },
        en: {
            debater: (name, position, topic) =>
`You are ${name}, an eloquent debate participant.
Your position: ${position} on the topic "${topic}".

Rules:
- Argue convincingly and with solid evidence for your position.
- Address your opponent's arguments when available.
- Stay factual but passionate.
- Keep it concise (length depends on setting).
- Respond in English.
- IMPORTANT: Always end with a complete sentence. Never stop mid-sentence.
- IMPORTANT: Start DIRECTLY with your arguments. Do NOT write any headers, round numbers, position labels, or meta-information like "Opening statement", "Pro response", "Round 1" etc. No introductory title – only your arguments.`,
            moderator:
`[Intro] You are a professional debate moderator. Write a concise, engaging introduction for the following debate. Language: English.

[Summary] You are a neutral debate moderator. Summarize the debate and evaluate both sides' arguments fairly. Language: English.`,
        },
    };

    function updatePromptPlaceholders() {
        const lang = langSelect?.value || 'de';
        const templates = promptTemplates[lang] || promptTemplates.de;
        const topicVal = topicEl?.value.trim() || '...';

        // Debater A
        const aPrompt = document.getElementById('a_system_prompt');
        const aName = document.querySelector('[name="a_name"]')?.value || 'KI Alpha';
        const aPos = document.querySelector('[name="a_position"]')?.value || 'Pro';
        if (aPrompt) aPrompt.placeholder = templates.debater(aName, aPos, topicVal);

        // Debater B
        const bPrompt = document.getElementById('b_system_prompt');
        const bName = document.querySelector('[name="b_name"]')?.value || 'KI Beta';
        const bPos = document.querySelector('[name="b_position"]')?.value || 'Contra';
        if (bPrompt) bPrompt.placeholder = templates.debater(bName, bPos, topicVal);

        // Moderator
        const modPrompt = document.getElementById('moderator_system_prompt');
        if (modPrompt) modPrompt.placeholder = templates.moderator;
    }

    // Update on relevant field changes
    ['a_name', 'a_position', 'b_name', 'b_position'].forEach(name => {
        document.querySelector(`[name="${name}"]`)?.addEventListener('input', updatePromptPlaceholders);
    });
    topicEl?.addEventListener('input', updatePromptPlaceholders);
    langSelect?.addEventListener('change', updatePromptPlaceholders);

    // Initial update
    updatePromptPlaceholders();

    // ─── File Upload Preview ────────────────────────────────────
    // Shows selected filenames and sizes, validates limits.

    const MAX_FILES = 5;
    const MAX_SIZE_MB = 10;

    document.querySelectorAll('.file-input').forEach(function (input) {
        input.addEventListener('change', function () {
            const zone = this.closest('.file-upload-zone');
            const listEl = zone?.querySelector('.file-list');
            if (!listEl) return;

            listEl.innerHTML = '';
            const files = this.files;

            if (files.length > MAX_FILES) {
                listEl.innerHTML = `<div class="file-item file-error">Maximal ${MAX_FILES} Dateien erlaubt (${files.length} ausgewählt)</div>`;
                return;
            }

            for (const file of files) {
                const item = document.createElement('div');
                item.className = 'file-item';
                const sizeMB = (file.size / 1024 / 1024).toFixed(1);

                if (file.size > MAX_SIZE_MB * 1024 * 1024) {
                    item.classList.add('file-error');
                    item.textContent = `${file.name} (${sizeMB} MB) – zu groß!`;
                } else {
                    item.textContent = `${file.name} (${sizeMB} MB)`;
                }

                listEl.appendChild(item);
            }
        });
    });
});
