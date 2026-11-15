# Guess the Human

A host-led classroom game: Students anonymously answer a question, while AI generates its own responses. Each round, an answer is revealed, and everyone votes Human or AI in Zoom chat. The host locks in the majority vote before revealing the truth. Can the class tell humans and AI apart?

[Live game](https://guess-the-human.onrender.com/) · [Code on GitHub](https://github.com/isalcedo1121/guess-the-human)

## Running a session

Open the live game as the host, create a room, and copy the room link from the
lobby. Send **that room link** to students so they join the same game. They can
write an answer without making an account. The GitHub link is for viewing code.

Open the app a few minutes before class and wait for setup to load. Render’s Free
service can sleep after 15 minutes without traffic and take about a minute to
wake up ([Render docs](https://render.com/docs/free)). If it has been idle for a
while, reload it before people join. For a 5–7-minute demo, choose 10 rounds or
end early.

## Original project

This started as **Game Glitch Investigator**, my Module 1 Streamlit number-guessing
game. The original checked guesses against a secret number and showed hints,
attempts, scores and history. Guess the Human is a major redesign: it keeps the
guessing and scoring idea, but rebuilds the interface and backend around human
answers and real AI generation.

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
The localhost link is for testing on your own computer. For a session with other
people, use the live Render app linked above.

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
not hidden model reasoning. Word hover and confetti follow the reference and
respect reduced-motion settings. The original six sound effects play on the host
page: a correct-answer sound, three wrong-answer sounds in rotation, and a win
or loss sound on results (70% accuracy to win). They follow successful actions,
so polling and page reloads do not replay them. Blocked audio does not interrupt
the game. The files are served locally from `frontend/static/sounds/`.

## Render setup

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

The code is pushed to GitHub, and the app is hosted on Render. These settings are
here so the setup can be repeated. Later local edits still need review and a push
before they can be included in a deployment.

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
and “Scunthorpe” are covered by tests. Standalone text art, symbol-only responses
and recognized hate symbols are rejected. Ordinary punctuation, code fragments,
language names and inline emojis remain valid. Words with legitimate alternate
meanings are assessed in context by Gemini rather than blanket-blocked locally.

**Start game** also runs a structured Gemini screening pass over collected human
answers for offensive content, sexual innuendo (including disguised or ambiguous
sexualized remarks about minors), harassment, explicit sexual content, threats,
and text art. It allows innocent childcare references, respectful criticism,
harmless jokes and unusual or off-topic answers. The question supplies context
without imposing a strict relevance test.
Flagged records (including records collected before this feature) are deleted
with their count adjustments in retry-safe Firestore transactions. Only accepted,
unmodified text reaches sampling and Chameleon. This adds one AI screening pass
before generation rather than a model request for every student submission.
If screening fails, the room returns to closed and no game is prepared. If all
answers are rejected, the host is asked to create a new room. Generated answers
and writing notes also pass the local profanity filter.

Games generated before the current screening rules return 409 instead of exposing
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

Actual results: **80 Python tests passed**, **8 JavaScript tests passed**, syntax
checks passed. Python tests use explicitly mocked AI data for scoring and failures.
The JS tests execute the actual host and submission scripts with DOM/network
doubles, checking preset/custom room creation against the real HTML element IDs,
retained submission text, stable retry IDs, completion only after acknowledgement,
safe rendering of individual writing notes, sound selection/rotation, silent
audio priming and harmless playback rejection.
These automated checks use DOM/network doubles. I also rehearsed the game with
about 10 CodePath staff members; see the rehearsal notes below.

Run the live example against your configured free-tier services:

```sh
python scripts/run_examples.py
```

This creates a temporary room and five independent simulated participant HTTP
sessions, retries submissions, closes, generates real Gemini outputs, plays and
scores all rounds, and removes only its own test room. It writes
[evidence/live_examples.json](evidence/live_examples.json). It uses your service
quotas and model wording may vary. No credentials or host cookies are recorded.

### Three input/output examples

The app uses all three styles automatically. These are real saved Gemini outputs
from [the style comparison](evidence/style_comparison.json), with the question
and model inputs shown together. Wording can change from game to game.

```text
Example 1 — Basic
Question: What do you do when your code doesn't work?
Model input: the question and Basic instructions; no student answers.
AI output: When my code fails, I systematically review error messages, isolate the problematic function with unit tests, and trace the execution step by step to identify the root cause.
```

```text
Example 2 — Chameleon
Question: What do you do when your code doesn't work?
Model input: the question, Chameleon instructions, and these human references:
  "i usally look thru it agian bc i miss stuff"
  "i usally ask someone bc the error looks wierd"
  "i check the console agian bc i dont get it"
  "i usally walk away bc i get annoyed"
  "i check stackoverflow agian bc thats easier"
AI output: i restart my computer agian bc it fixes it
Writing note: I used all lowercase letters, repeated the misspelling agian, and kept the short phrasing without any ending punctuation.
```

```text
Example 3 — Slang
Question: What do you do when your code doesn't work?
Model input: the question and Gen Alpha / Gen Z slang instructions; no student answers.
AI output: My debugging rizz is completely chopped when syntax errors show up so I just restart the laptop no cap.
```

Here is the full-game result from `python scripts/run_examples.py`, recorded in
[evidence/live_examples.json](evidence/live_examples.json):

```text
Input: "What do you do when your code doesn't work?"
Human inputs: 5 written answers, including "print every variable until the bug confesses"
Create room: 201
Submit 5 answers: 200 each; repeat requests kept the count at 5
Generate answers: 200
Play all 10 rounds, guessing Human each time
Result: 5 correct, 5 incorrect, 50% accuracy
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
### Rehearsal with people

| Check | What happened | Source |
| --- | --- | --- |
| Group rehearsal | About 10 CodePath staff joined the game. It worked well in that rehearsal. | My rehearsal report |
| Feedback | One person pointed out possible cold starts. I’ll open the app before the session. | My rehearsal report |
| Public page check | The live homepage and `/health` both returned 200; health returned `{"status":"ok"}`. | Read-only HTTPS check |

The group rehearsal is informal feedback. The automated results and saved outputs
above give separate, repeatable evidence.

## Deployment-readiness verification

The current checks are recorded in
[evidence/deployment_readiness.json](evidence/deployment_readiness.json).
A separate clean source copy and virtual environment used only `requirements.txt`,
with `APP_ENV=production`, inline Firebase JSON, and the Gemini key provided in
process environment variables. No `.env` or local credential file was copied.
Runtime imports, Uvicorn startup with the Render flags, `/health`, room creation,
host access, participant page/assets, and secure host cookies passed. An HTTPS
browser-origin test verified participant links use that origin rather than a
hardcoded localhost URL. All temporary verification rooms were deleted and the
verification server stopped.

Twenty live screening cases passed using the local filter and Gemini, preserving
benign childcare, names,
animal terms, respectful instructor feedback, humor, code and inline emojis while
rejecting the tested unsafe cases and drawings. Automated tests separately cover
fail-closed screening, original writing preservation, count updates and rejected
content exclusion. Tracked files and reachable Git history were scanned for
actual local secrets and private-key patterns; none were found.

That report records the checks done before deployment. The app is now on Render:
a later HTTPS check confirmed the homepage and `/health` respond. I also
rehearsed it with staff, as noted above. Shared data lives in Firestore, so a Render restart
doesn’t depend on keeping a local database file.

## My part in the project

My biggest contribution was definitely the visual design and keeping the game simple. I
wanted people to know where to look and what to click without a bunch of clutter.
I used coding assistants to work through ideas, code and bugs,
while I made the calls on the design and what belonged in the MVP. This ended up
being a big redesign of the old number game. It shows that I can guide AI tools,
question their output, and test something with real people!

## Assignment coverage and reflection

The required AI extension is specialized behavior through structured prompting,
plus AI screening and reliability checks built into the game. The rubric allows
these options; RAG and fine-tuning are not required. Chameleon uses examples in
its prompt, without training the model or searching a retrieval index.

The original project is named above. The app includes real AI generation and
screening, a [Mermaid diagram](diagrams/architecture.mmd), setup steps, three
input/output examples, and saved test results. My AI collaboration, decisions,
limitations and misuse concerns are in [model_card.md](model_card.md).

What I learned: passing tests is a good start, but real API calls and people
playing the game catch things that small tests miss. A rehearsal with staff here at CodePath helped
me check the experience, and the cold-start feedback gave me something practical
to prepare for.
