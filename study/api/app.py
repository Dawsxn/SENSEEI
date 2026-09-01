"""The running trial: a proctor console and the participant-facing screens.

Server-rendered HTML rather than a single-page app. The SENSEE-I application is
a React SPA because it is a long-lived product; this is a lab instrument used by
45 people on one afternoon, and a build toolchain would be machinery to maintain
for no benefit the participants would ever notice. Templates and a little vanilla
JavaScript are enough, and the whole thing starts with one command.

Two routes into the system:

- ``/`` is the **proctor console**: check people in, watch the roster and the
  engagement measures Section 4.6.3 will be applied to, log an incident.
- ``/p/{code}`` is the **participant flow**. One URL for the whole session; what
  it renders depends on the phase they are in, so nobody has to be told where to
  go next and nobody can navigate somewhere they should not be.

The 40 minutes are a ceiling: a participant who finishes early continues to the
post-test rather than waiting for the room. The clock's only job is to end a
session still running when time is up, and it is enforced on the server from its
own timestamps, so the countdown a participant sees is display only.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ..arms import Arm
from ..exclusion import build_engagement_record, median_of, summarise
from ..instruments import load_all, readiness, score
from ..interventions.unguided import build_chat_backend
from ..phases import (
    Phase,
    PhaseError,
    is_expired,
    seconds_remaining,
    utcnow,
)
from ..phases import advance as advance_phase
from ..senseei_link import FakeSenseeiLink
from ..trial_config import load_trial_config
from .store import TrialStore

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

#: Which template renders each phase. The instrument phases share one placeholder
#: until their content lands; the intervention screens are real.
PHASE_TEMPLATES = {
    Phase.DEMOGRAPHICS: "instrument.html",
    Phase.PRE_TEST: "instrument.html",
    Phase.POST_TEST_A: "instrument.html",
    Phase.SBA: "instrument.html",
    Phase.SUS: "instrument.html",
    Phase.DONE: "done.html",
}

INTERVENTION_TEMPLATES = {
    Arm.SENSEEI: "intervention_senseei.html",
    Arm.UNGUIDED_LLM: "intervention_unguided.html",
    Arm.PASSIVE: "intervention_passive.html",
}


def create_app(config=None, store: TrialStore | None = None) -> FastAPI:
    config = config or load_trial_config()

    if store is None:
        backend_error = ""
        backend = None
        try:
            backend = build_chat_backend(config.llm)
        except Exception as exc:  # missing key, unknown provider, SDK absent
            # Surfaced on the console rather than raised: the passive and
            # SENSEE-I arms are still runnable, and a proctor needs to be told
            # what is broken rather than met with a stack trace at start-up.
            backend_error = str(exc)
        store = TrialStore(config, chat_backend=backend)
        store.backend_error = backend_error

    app = FastAPI(title="SENSEE-I trial harness")
    app.state.config = config
    app.state.store = store
    app.state.instruments = load_all()
    app.state.link = FakeSenseeiLink(
        base_url=config.senseei_base_url or "https://senseei.example/session"
    )

    def participant_or_404(code: str):
        participant = store.by_code(code)
        if participant is None:
            raise HTTPException(status_code=404, detail="Unknown access code.")
        return participant

    def render(request: Request, template: str, **context) -> HTMLResponse:
        return TEMPLATES.TemplateResponse(
            request=request, name=template, context={"config": config, **context}
        )

    def _advance(participant):
        """Move a participant on, closing whatever their arm had open."""
        now = utcnow()
        if participant.state.phase is Phase.INTERVENTION:
            store.end_intervention(participant, now)
        participant.state = advance_phase(participant.state, now, config.timing)
        if participant.state.phase is Phase.INTERVENTION:
            store.begin_intervention(participant, now)

    def _expire_if_due(participant) -> None:
        """End an intervention whose time is up.

        Applied whenever a participant's page is served, so the clock is enforced
        even if their browser never fired the countdown — a closed laptop lid, a
        stalled tab, a page left on a phone.
        """
        if participant.state.phase is Phase.INTERVENTION and is_expired(
            participant.state, utcnow(), config.timing
        ):
            _advance(participant)

    # --- proctor console --------------------------------------------------

    @app.get("/", response_class=HTMLResponse)
    def console(request: Request, new: str = ""):
        now = utcnow()
        rows = []
        records = []
        for participant in store.all():
            record = build_engagement_record(participant, now, app.state.link)
            records.append(record)
            rows.append(
                {
                    "participant": participant,
                    "record": record,
                    "in_phase": now - participant.state.entered_at,
                    "remaining": seconds_remaining(
                        participant.state, now, config.timing
                    ),
                }
            )
        return render(
            request,
            "console.html",
            rows=rows,
            store=store,
            counts=store.counts_by_arm(),
            new_participant=store.get(new) if new else None,
            warnings=_preflight(config, store, app.state.instruments),
            summary=summarise(records),
            medians={
                key: median_of(records, key)
                for key in (
                    "session_seconds",
                    "turn_count",
                    "word_count",
                    "intervention_seconds",
                    "time_on_text_seconds",
                )
            },
        )

    @app.post("/check-in")
    def check_in(name: str = Form(""), consent_form_serial: str = Form("")):
        try:
            participant = store.check_in(
                utcnow(),
                name=name.strip(),
                consent_form_serial=consent_form_serial.strip(),
            )
        except IndexError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return RedirectResponse(f"/?new={participant.participant_id}", status_code=303)

    @app.post("/participants/{participant_id}/incident")
    def incident(participant_id: str, note: str = Form(...)):
        participant = store.get(participant_id)
        if participant is None:
            raise HTTPException(status_code=404, detail="Unknown participant.")
        participant.incidents.append(f"{utcnow().isoformat(timespec='seconds')} {note}")
        return RedirectResponse("/", status_code=303)

    # --- the participant flow --------------------------------------------

    @app.get("/p/{code}", response_class=HTMLResponse)
    def participant_view(request: Request, code: str):
        participant = participant_or_404(code)
        _expire_if_due(participant)

        now = utcnow()
        phase = participant.state.phase
        template = (
            INTERVENTION_TEMPLATES[participant.arm]
            if phase is Phase.INTERVENTION
            else PHASE_TEMPLATES[phase]
        )

        return render(
            request,
            template,
            participant=participant,
            phase=phase,
            remaining=seconds_remaining(participant.state, now, config.timing),
            reading=_reading(config),
            senseei_url=app.state.link.session_url(participant.participant_id),
            store=store,
            instrument=app.state.instruments.get(phase.value),
            answers=participant.draft_answers(phase),
            missing=participant.missing_answers(phase),
        )

    @app.post("/p/{code}/submit")
    async def submit(request: Request, code: str):
        """Record an instrument submission and move on.

        A required item left blank re-renders the form rather than advancing.
        The answers already given are kept and shown back, because losing them
        to a validation bounce is the fastest way to make someone answer the
        second time less carefully than the first.
        """
        participant = participant_or_404(code)
        instrument = app.state.instruments.get(participant.state.phase.value)
        if instrument is None or instrument.is_placeholder:
            return RedirectResponse(f"/p/{code}", status_code=303)

        form = await request.form()
        answers = {
            key[len("item_"):]: str(value)
            for key, value in form.items()
            if key.startswith("item_")
        }

        result = score(instrument, answers)
        participant.record(participant.state.phase, result)

        if not result.is_complete:
            return RedirectResponse(f"/p/{code}", status_code=303)

        try:
            _advance(participant)
        except PhaseError:
            pass
        return RedirectResponse(f"/p/{code}", status_code=303)

    @app.post("/p/{code}/advance")
    def participant_advance(code: str):
        """Move on. Available whenever the session is running.

        A participant who has finished the reading proceeds straight to the
        post-test; nobody waits for the room.
        """
        participant = participant_or_404(code)
        try:
            _advance(participant)
        except PhaseError:
            # Already finished, or a double-submitted form. Re-render rather
            # than error: the participant did nothing wrong.
            pass
        return RedirectResponse(f"/p/{code}", status_code=303)

    @app.post("/p/{code}/chat")
    def chat(code: str, message: str = Form(...)):
        participant = participant_or_404(code)
        _expire_if_due(participant)

        if participant.arm is not Arm.UNGUIDED_LLM:
            raise HTTPException(status_code=403, detail="Not this participant's arm.")
        if participant.state.phase is not Phase.INTERVENTION:
            raise HTTPException(status_code=409, detail="The period is not running.")
        if participant.unguided is not None and message.strip():
            participant.unguided.send(message, utcnow())
        return RedirectResponse(f"/p/{code}", status_code=303)

    @app.post("/p/{code}/reading-event")
    def reading_event(code: str, kind: str = Form(...), depth: float = Form(0.0)):
        """Tab-away, return, and scroll depth from the passive arm's reader.

        Phase duration cannot tell whether the text was open, so the page reports
        what the phase engine cannot see (§4.6.3).
        """
        participant = participant_or_404(code)
        session = participant.passive
        if session is None:
            return {"ok": False}

        now = utcnow()
        if kind == "away":
            session.went_away(now)
        elif kind == "back":
            session.came_back(now)
        elif kind == "scroll":
            session.scrolled(max(0.0, min(1.0, depth)), now)
        return {"ok": True}

    return app


def _reading(config) -> dict:
    """The trial text, or an explanation of why there is not one yet."""
    try:
        return {
            "title": config.reading.title or config.reading.path.name,
            "text": config.reading.text(),
            "missing": False,
        }
    except OSError:
        return {
            "title": "",
            "text": "",
            "missing": True,
            "path": str(config.reading.path),
        }


def _preflight(config, store, instruments=None) -> list[str]:
    """What would stop this being real data collection.

    Shown on the console rather than only raised at start-up, so a proctor can
    see at a glance whether they are looking at a rehearsal or the real thing.
    """
    warnings: list[str] = []
    if not store.is_durable:
        warnings.append(
            "Participants are held in memory only — restarting the server loses "
            "every record. Not usable for real collection."
        )
    if getattr(store, "backend_error", ""):
        warnings.append(f"The unguided arm cannot reach a model: {store.backend_error}")
    try:
        config.validate()
    except Exception as exc:
        warnings.append(str(exc))

    outstanding = readiness(instruments or {})
    if outstanding:
        warnings.append("Instruments not ready: " + "; ".join(outstanding))
    return warnings


app = create_app()
