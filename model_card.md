# Guess the Human — model card

## Purpose and model

A classroom guessing game, not an authorship detector. The server knows each
answer's source because it collected or generated it. Audience guesses are
recorded by the host. Gemini 3.5 Flash-Lite is accessed through Google's official
Gen AI SDK, using structured prompting and JSON output validation.

Basic receives only the question and uses the model’s ordinary default writing
style. Slang also receives no student answers; it explicitly uses recognizable
Gen Alpha / Gen Z vocabulary such as “cooked”, “chopped”, “no cap” or “fr”.
Chameleon receives **all** collected human answers as untrusted reference data,
with their original casing, punctuation and spelling. Its instructions match
their tone, length, sentence structure, abbreviations, missing punctuation,
inconsistent casing and recurring misspellings when present. It creates new
content in that style, rather than polishing the writing or inventing an
elaborate scenario. References are never treated as system instructions.
All generated answers are checked against human answers for near-copying,
including Basic and Slang outputs that never received the human references.

Gemini returns one short, first-person writing note per answer. Chameleon notes
identify the human style habits matched in that particular answer, Slang notes
name its slang, and Basic notes describe its ordinary direct wording. These are
generated descriptions of observable output features, not private reasoning
traces. Length, active voice and repeated-note checks replace the previous fixed
description per style. Notes stay hidden until results.

The controlled real examples in `evidence/style_comparison.json` compare the same
question with informal versus formal reference sets. Chameleon follows the
change in casing and punctuation while Basic remains ordinary AI writing and
Slang uses explicit internet vocabulary. A third set checks recurring
misspellings: Chameleon carries “agian” into fresh lowercase phrasing.
The earlier creative-angle prompt in
`evidence/writing_notes.json` is superseded; its generic Chameleon story notes
were not an adequate demonstration of style matching.

## Limitations and biases

Writing notes can misdescribe a response; distinct notes do not prove that every
answer faithfully follows the intended style.

Style control is probabilistic: slang can be mild, and Chameleon may miss local
writing patterns. Similarity filtering catches near copies, not all paraphrases.
Prompt isolation and model safety instructions are not comprehensive moderation;
human answers are length-validated and rendered as text, but inappropriate
content is still possible in a trusted classroom. Host review and ending/skipping
an unsuitable response remain available. No demographic identity is inferred.

Difficulty uses a deliberately simple heuristic: long AI answers are tier 1;
short answers starting lowercase are tier 3; others are tier 2. Correct AI guesses
raise the selection target; incorrect AI guesses lower it. Writing strategy is
separate. These tiers are not calibrated measures of detectability.

Anonymous browser receipts prevent accidental duplicates, not deliberate evasion.
Cleared/unavailable browser storage can defeat this convenience. Host cookies
last one day and have no account recovery. Firestore contention can still produce
a retriable error under load. Free Render hosting can sleep; no public deployment
has been performed. A generation interrupted by a process restart becomes
retryable after three minutes. Rate limits and provider outages remain possible.

## Misuse and mitigation

Do not use the game to accuse people of academic misconduct. Use anonymous,
non-sensitive answers; Gemini's free tier may use submitted content for product
improvement. Participants should not include private details. API keys and
service-account JSON remain server-side, outside Git and frontend assets. Public
student endpoints do not return other submissions or hidden source labels.
The backend enforces host permissions and checks the Origin of browser mutations.
No billing, paid infrastructure, public deployment or student accounts were enabled.

## Reliability observations

The first concurrent live test exposed a Firestore read conflict not retried by
the SDK's commit retry loop. A bounded whole-transaction retry fixed the repeated
live scenario. Accepted receipts and the count are committed together.
Gemini 2.5 Flash-Lite appeared in model listing but rejected generation for new
users. The provider recommended Gemini 3.5 Flash-Lite. A subsequent transient 503
led to one bounded server-error retry per generation batch. There is no canned
fallback and no model call during a guess.

The recorded real end-to-end example used five synthetic human inputs and five
real AI outputs. Always guessing Human produced exactly 5/10 correct (50%).
This verifies application arithmetic, not AI-detection performance.
See `evidence/live_examples.json`; mocked outputs appear only in automated tests.

## AI collaboration and decisions

AI assistance was used to inspect the original code, plan the architecture,
implement the endpoints and UI, design tests, and debug verified service failures.
Accepted: separate the existing HTML frontend from Python rules and use structured
AI output checks. This preserves the visual reference while testing game rules.
Rejected/revised: the earlier suggestion to preserve an extra `legacy/` app,
use SQLite/paid storage, and add preview navigation. The user chose Git history
for preservation, free Firestore, and a clean application UI instead. A fixed
nine-answer AI pool was also replaced with exactly the number needed for balanced
host-selected game length. No claims of staff approval of the redesign are made.

## Improvements

Rehearse with real devices, evaluate styles with humans, refine difficulty using
observed results, add proportionate moderation if needed, and review data retention
before public use. A small classroom's votes cannot establish general AI-detection
accuracy or bias measurements.
