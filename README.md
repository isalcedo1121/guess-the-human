# Guess the Human

A host-led classroom game: Students anonymously answer a question, while AI generates its own responses. Each round, an answer is revealed, and everyone votes Human or AI in Zoom chat. The host locks in the majority vote before revealing the truth. Can the class tell humans and AI apart?

## Original project

This extends **Game Glitch Investigator**, the Module 1 Streamlit number game.
It compared numeric guesses with a secret and displayed hints, attempts, scores,
and history. The redesign preserves guessing, feedback, scoring, difficulty,
and progression while changing the hidden target to answer authorship.

| Original component | Evolution |
| --- | --- |
| Streamlit entry point | FastAPI serving separate HTML/CSS/JS |
| Numeric parsing, ranges and hints | Replaced with text validation and Human/AI rules |
| Browser session state | Shared Firestore room and game records |
| Difficulty and score concepts | Adaptive response selection and accuracy |
| Pytest configuration and Git history | Retained; original source at `02afa3b` |

No unrelated numeric logic or legacy application is kept. Historical reflection
files describe the original project. Current AI reflection is in [model_card.md](model_card.md).

## Setup

Python 3.12+ (verified with 3.14.6):

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
```

In the ignored `.env`, configure `FIREBASE_PROJECT_ID`,
`GOOGLE_APPLICATION_CREDENTIALS` (an absolute path to a service-account JSON
outside the repository), and `GEMINI_API_KEY`. Alternatively, provide
`FIREBASE_SERVICE_ACCOUNT_JSON` through the server environment instead of the
credential file path. `GEMINI_MODEL` defaults to `gemini-3.5-flash-lite`.
Use Firestore's default Standard database with production rules denying browser
access; the Python service account accesses it. Keep the Firebase Spark plan and
Gemini free tier; do not enable billing. No Firebase web SDK or student login is
required. Provider availability and free quotas can change.

```sh
python -m uvicorn app:app --reload
```

Open http://127.0.0.1:8000. Create a room, copy its participant link, collect
answers, then click **Start game**. It closes submissions, generates AI answers,
and enters the first round automatically. You can also close submissions manually. Guess Human/AI,
advance, skip, or end early. Host sessions survive reload via an HTTP-only cookie.
A local loopback link works only on that computer. Public access requires a later,
separately approved deployment; nothing has been pushed or deployed.

The five presets are rendered into the initial host page, with custom entry last.
HTML, scripts and API responses use `Cache-Control: no-store` to prevent stale
frontend versions and private responses from being cached.

The lobby’s **+ Sample answers** button opens an editable list using the human
examples supplied for each preset question. Enter one answer per line, then add
them together; repeated additions of identical samples do not inflate the count.
Custom questions use the same editor with an empty list. AI-generated answers
keep their AI classification. Fewer unique human answers shorten the game as
usual: five human answers are needed for a ten-round game.

Results retain the mockup’s expandable AI strategy details, source chips and
correct/incorrect markers. Gemini returns a short, active first-person writing note for each AI answer,
describing how that answer uses its assigned writing style. Notes are checked for
repetition and appear only on results; they are descriptions of the finished text,
not hidden model reasoning. Older games use brief style summaries. Word hover and confetti follow the reference and
respect reduced-motion settings. The original six sound effects play on the host
page: a correct-answer sound, three wrong-answer sounds in rotation, and a win
or loss sound on results (70% accuracy to win). They follow successful actions,
so polling and page reloads do not replay them. Blocked audio does not interrupt
the game. The files are served locally from `frontend/static/sounds/`.

## Render configuration (deployment is separate)

The repository root contains `requirements.txt` and `app.py`. Use Python 3,
branch `main`, a blank Root Directory, Oregon, the Free instance, and build command
`pip install -r requirements.txt`.

For Render’s HTTPS proxy, use this start command so the application’s same-origin
checks see the public HTTPS scheme:

```sh
uvicorn app:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"
```

Trust all forwarded IPs only behind the platform’s proxy. Set `APP_ENV=production`,
`FIREBASE_PROJECT_ID=guess-the-human`, and your existing `GEMINI_API_KEY`.
`GEMINI_MODEL=gemini-3.5-flash-lite` is the current default. For Firestore, remove
the imported local `GOOGLE_APPLICATION_CREDENTIALS` path and set
`FIREBASE_SERVICE_ACCOUNT_JSON` to the complete service-account JSON in Render’s
private environment settings. The application already supports this format.
Keep the JSON and API key outside Git and do not paste them into chat.
Use `/health` as the health-check path; this checks the web process, not providers.

These instructions do not deploy the app. Local amendments are not available to
Render until the repository is pushed separately.

## Architecture and rules

The three AI versions have separate generation instructions:

- **Basic:** the model’s ordinary response to the question, with no student answers in its prompt.
- **Slang:** a modern Gen Alpha / Gen Z internet voice with recognizable terms such as “cooked” or “chopped”; no student answers in its prompt.
- **Chameleon:** all collected human answers as style references, preserving their tone, length, casing, punctuation, abbreviations and recurring misspellings in new content. It does not polish away informal habits or invent mistakes absent from the references.

Each writing note describes that version’s approach in the individual answer.
Chameleon notes identify matched human writing habits; Slang notes name the slang
used; Basic notes describe ordinary direct wording.

[Mermaid source](diagrams/architecture.mmd) shows browsers, FastAPI, validation,
Firestore, Gemini, human involvement and testing. Backend modules separate room
endpoints, storage, game rules, generation and configuration. Firestore stores
room status, host-token hashes, submission receipts, accepted answers and game
state. Student endpoints expose only the question, status and their own receipt.

The host counter polls one room document every five seconds while visible;
manual refresh appears only on failure. Submission and count changes use one
transaction. The browser persists a retry ID before posting, but marks completion
only after server acknowledgement. Failed requests leave the typed text intact.

For N requested rounds, sample up to N/2 unique human answers and generate the
same number of AI answers. Too few humans reduce the total. Basic, Chameleon,
and Slang counts differ by at most one. Answers are shuffled and never repeated.
Difficulty selects the closest available AI tier independently of writing style;
no new LLM requests occur during rounds. See the model card for the heuristic
and its limitations. Ending early scores only assessed answers.

## Classroom content screening

A server-side filter rejects common profanity and obfuscations before saving a
student answer or host sample. It handles leetspeak, separated letters, common
Unicode lookalikes, accents, zero-width characters and masked spellings. Rejected
requests return 422, leave the count unchanged and let the student edit and retry
with the same browser receipt. Harmless substrings such as “class”, “assignment”
and “Scunthorpe” are covered by tests.

**Start game** also runs a structured Gemini screening pass over collected human
answers for offensive content, harassment, explicit sexual content and threats.
Flagged records (including records collected before this feature) are deleted
with their count adjustments in retry-safe Firestore transactions. Only accepted,
unmodified text reaches sampling and Chameleon. This adds one AI screening pass
before generation rather than a model request for every student submission.
If screening fails, the room returns to closed and no game is prepared. If all
answers are rejected, the host is asked to create a new room. Generated answers
and writing notes also pass the local profanity filter.

Games generated before screening was introduced return 409 instead of exposing
old unscreened answers; reload and create a new room. Moderation is imperfect:
novel obfuscations or context may be misclassified. Host skip/end controls remain
available. [The real moderation check](evidence/moderation_flow.json) records
rejections, a corrected submission, removal/count consistency, and the old-game
access guard. All temporary test data was removed.

## Tests and real execution evidence

```sh
python -m pytest -p no:cacheprovider
node --test tests/*.test.cjs
node --check frontend/static/host.js
node --check frontend/static/participant.js
node --check frontend/static/sounds.js
```

Actual results: **65 Python tests passed**, **8 JavaScript tests passed**, syntax
checks passed. Python tests use explicitly mocked AI data for scoring and failures.
The JS tests execute the actual host and submission scripts with DOM/network
doubles, checking preset/custom room creation against the real HTML element IDs,
retained submission text, stable retry IDs, completion only after acknowledgement,
safe rendering of individual writing notes, sound selection/rotation, silent
audio priming and harmless playback rejection.
These are not rendered-browser tests. Browser preview access was unavailable;
audible playback and the final results layout still need a manual browser check.

Run the live example against your configured free-tier services:

```sh
python scripts/run_examples.py
```

This creates a temporary room and five independent simulated participant HTTP
sessions, retries submissions, closes, generates real Gemini outputs, plays and
scores all rounds, and removes only its own test room. It writes
[evidence/live_examples.json](evidence/live_examples.json). It uses your service
quotas and model wording may vary. No credentials or host cookies are recorded.

Actual execution excerpts from that run (the style examples below were refreshed
from the later verified comparison):

```text
Example 1 — create and submit
POST /api/rooms -> 201
5 independent participants -> 200 each
Duplicate retry for each participant -> 200
submission_count -> 5
Unrelated participant requesting host controls -> 403
Late submission after closing -> 409
```

```text
Example 2 — real generation
POST /api/rooms/{id}/generate -> 200
model: gemini-3.5-flash-lite
Basic: "When my code fails, I systematically review error messages, isolate the problematic function with unit tests, and trace the execution step by step to identify the root cause."
Chameleon (lowercase, unpunctuated references): "google the error message word for word"
Slang: "My debugging rizz is completely chopped when syntax errors show up so I just restart the laptop no cap."
```

```text
Example 3 — guessing and scoring
10 rounds: 5 human + 5 AI
Guess Human on every answer
correct: 5
incorrect: 5
accuracy: 50
end_to_end: passed
```

| Guardrail input/scenario | Verified behavior |
| --- | --- |
| Empty/whitespace or >280-character answer | 422; no accepted submission |
| Profanity or `B-1-T-C-H` | 422; no receipt or count increase; text remains editable |
| AI flags an already collected answer | Record removed; count adjusted; excluded from game and references |
| Screening unavailable or incomplete decisions | 503; closed room; no unscreened game |
| Old unscreened game | 409; create a new room |
| Cross-origin mutation or missing host cookie | 403 |
| Duplicate submission receipt | Count remains unchanged |
| Empty, duplicate, long or near-copy AI output | Rejected before play |
| Mocked provider failure | 502; room returns to closed, no fake answers |
| Stale answer ID or next before guessing | 409 |

The newer combined-flow check is recorded in
[evidence/review_flow.json](evidence/review_flow.json): three manually supplied
samples, duplicate-safe addition, one Start request, three real AI answers,
six completed rounds, 3/6 correct, 50% accuracy, and three AI explanations.
A later live check also verified preset and custom room creation and authenticated
lobby access against the running server and Firestore; both temporary rooms were removed.

The current [style comparison](evidence/style_comparison.json) records real
Gemini outputs against contrasting synthetic reference sets. Chameleon switches
from lowercase, unpunctuated answers to capitalized, complete sentences when the
human examples change. A third reference set verifies that Chameleon preserves
recurring nonstandard spelling: “i restart my computer agian bc it fixes it”.
Slang uses recognizable expressions including “cooked”,
“chopped” and “no cap”. Tests also verify that every reference, including entries
past the former 100-answer limit, reaches Chameleon alone. Near-duplicate AI
answers and repeated notes are rejected before play.

The earlier [writing-note check](evidence/writing_notes.json) verifies individual
notes, but its style prompting is superseded by the current comparison above.

Earlier live checks revealed a Firestore transaction conflict and a provider 404;
those were addressed before the passing run. Provider 503s receive one retry.
No full rendered-browser or phone rehearsal has been completed; do that before
presentation. No screenshots substitute for the text evidence above.

## Assignment coverage and reflection

The local official assignment and the full seven-category rubric supplied in the
conversation were reviewed. Base project: above. Integrated specialization:
three structured generation strategies. Architecture: Mermaid source. End-to-end:
three examples above. Reliability: validators, failure tests and real checks.
Setup: commands above. AI collaboration/limitations: `model_card.md`. This is an
implementation/evidence mapping, not a claim of awarded points or staff approval.

The original debugging lesson carries forward: passing helper tests alone is
insufficient. Concurrent requests and real provider calls found failures that
isolated tests missed. Optional RAG and agent infrastructure were deliberately
excluded. Before the 5–7-minute presentation, rehearse on separate devices and
check the provider quota. Public publishing remains a user-controlled release
step. Render free services may cold-start; Firestore persists data separately.
