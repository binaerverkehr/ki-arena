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
});
