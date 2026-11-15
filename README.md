# Guess the Human

A host-led classroom game where participants submit anonymous written answers
and an audience guesses which answers came from humans or AI. Audience voting
happens in Zoom chat; the host records the majority choice in the application.

## Current status

The FastAPI foundation and responsive frontend are in place. The initial page
shows game setup with question selection, custom question entry, and game-length
selection. The other game screens are retained for the real game flow and remain
hidden. The participant form includes an answer field and character counter.

Rooms, submissions, Firestore, gameplay, and LLM generation are not yet
implemented. Room creation, submission, guessing, and generation controls remain
disabled; nothing entered is submitted or saved. The health endpoint checks only
the web process.

## Original project

This project extends **Game Glitch Investigator**, the Module 1 number-guessing
game. That Streamlit application compared numeric guesses with a secret number
and displayed hints, attempts, score, and history. Guess the Human redesigns
guessing, feedback, scoring, difficulty, and progression around Human/AI
authorship; unrelated numeric rules are not reused.

The original code and tests remain in Git history, including commit `02afa3b`.
There is no separate legacy application. `reflection.md` and the original
entries in `ai_interactions.md` document the earlier project.

| Original component | Current treatment |
| --- | --- |
| Streamlit `app.py` | Replaced with a FastAPI entry point. |
| Numeric `logic_utils.py` and its tests | Removed from the active application; preserved in history. |
| Git history and pytest configuration | Retained. |
| Guessing, scoring, feedback, difficulty | Concepts retained; new rules will be implemented in Python. |

The final visual mockup was adapted into separate frontend files. Its colors,
cards, large Human/AI buttons, responsive layout, and reveal/results design are
retained. Fake room links, sample answers, browser-owned game logic, generation
timers, embedded sounds, and confetti are not part of this foundation.
Both pages explicitly declare a light-only color scheme to preserve the original
lavender background, white cards, dark purple text, and pastel panels rather
than opting into automatic browser darkening.

## Structure

```text
app.py                    FastAPI entry point and page/static routes
backend/config.py         Environment settings; no service connections
frontend/host.html        Game setup and inactive game screens
frontend/participant.html Anonymous answer form
frontend/static/          CSS, JavaScript, favicon, and five preset questions
tests/                    HTTP, configuration, and static-file checks
```

## Local setup

Use Python 3.12 or newer. The initial foundation was tested with Python 3.14.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m uvicorn app:app --reload
```

Open <http://127.0.0.1:8000> for game setup. The participant form is currently
served at <http://127.0.0.1:8000/participant-preview>; shared room links will be
implemented with submissions. API documentation is available at
<http://127.0.0.1:8000/docs>.

No Node.js build step is required. The frontend uses browser JavaScript modules
and local assets, without external fonts, scripts, or CDNs. Local preview binds
to your own computer; public student links will be implemented in a later stage.

Environment configuration is optional:

```sh
cp .env.example .env
```

Leave the Firebase and LLM values blank. They are reserved configuration fields,
not working integrations. Never commit `.env`, service-account credentials, or
API keys. Configuration is read on startup; restart after changing `.env`.

## Checks

```sh
python -m pytest
curl http://127.0.0.1:8000/health
```

The health response is `{"status":"ok"}`. Tests cover startup, environment
configuration, both pages and their assets (including when launched from another
working directory), the question bank, and keeping source/environment files
outside the public static directory. Room creation is intentionally unavailable.
There are no real LLM outputs or end-to-end game results to report yet.

Optional JavaScript syntax checks, if Node.js is installed:

```sh
node --check frontend/static/host.js
node --check frontend/static/participant.js
```

Foundation verification on Python 3.14.6:

- **12 tests passed**, including in a fresh virtual environment installed from
  `requirements-dev.txt`.
- Both JavaScript files passed the syntax checks above.
- Live HTTP requests returned 200 for both pages, the health endpoint, CSS,
  JavaScript, and the question bank.
- The served palette was compared with the original mockup, including page,
  card, input, Human/AI button, and success/error panel colors. Both served pages
  include light-only rendering metadata.

## Planned hosting

One FastAPI application will serve the frontend and API on Render's free tier.
Shared room data will use Firebase Cloud Firestore's free tier. One real LLM
provider will be connected after gameplay is implemented. No cloud service,
billing, deployment, database connection, or LLM request is enabled by this
foundation.

The official assignment, planning context, and standalone HTML mockup remain
outside this repository. Later documentation will add the model card, actual
architecture diagram, and reproducible AI/guardrail evidence when those
components exist.
