# Guess the Human

A host-led classroom game where participants submit anonymous written answers
and an audience guesses which answers came from humans or AI. Audience voting
happens in Zoom chat; the host records the majority choice in the application.

## Current status

Development is proceeding one stage at a time. The FastAPI foundation is in
place. Rooms, submissions, Firestore, gameplay, and LLM generation are not yet
implemented. The health endpoint checks only the web process.

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

## Local setup

Use Python 3.12 or newer. The initial foundation was tested with Python 3.14.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m uvicorn app:app --reload
```

The server runs at <http://127.0.0.1:8000>. API documentation is available at
<http://127.0.0.1:8000/docs>.

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

The health response is `{"status":"ok"}`. Tests currently cover startup,
configuration, and the absence of simulated room creation. There are no real
LLM outputs or end-to-end game results to report yet.

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
