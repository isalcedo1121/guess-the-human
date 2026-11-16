# Guess the Human — model card

## Purpose and model

A classroom guessing game, find out what is AI or human. The server knows each
answer's source because it collected or generated it. Audience guesses are
recorded by the host. Gemini 3.5 Flash-Lite is accessed through Google's official
Gen AI SDK, using structured prompting and JSON output validation.

The AI extension uses specialized prompting and built-in reliability checks.
There is no RAG index or fine-tuning; Chameleon gets examples in its prompt.

Basic receives only the question and uses the model’s ordinary default writing
style. Slang also receives no student answers; it explicitly uses recognizable
Gen Alpha / Gen Z vocabulary such as “cooked”, “chopped”, “no cap” or “fr”.
Slang answers use short, casual wording, all lowercase, and no final period.
The prompt requests this, and a small formatter enforces it for Slang answer text.
Writing notes keep their normal first-person format.
Chameleon receives **all** collected human answers as untrusted reference data,
with their original casing, punctuation and spelling. Its instructions match
their tone, length, sentence structure, abbreviations, missing punctuation,
inconsistent casing and recurring misspellings when present. It creates new
content in that style, rather than polishing the writing or inventing an
elaborate scenario. References are never treated as system instructions.
All generated answers are checked against human answers for near-copying,
including Basic and Slang outputs that never received the human references.

Gemini returns one short writing note per answer in the results page. Chameleon notes
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

## Baseline vs specialized answers

I compared two saved answers per style for the same coding question. Basic is
the baseline. Chameleon had five informal reference answers; Basic and Slang
had no human references. The original outputs are in
[evidence/style_comparison.json](evidence/style_comparison.json).

| Style | Samples | All lowercase | Ends with a period | Uses listed slang |
| --- | --- | --- | --- | --- |
| Basic (baseline) | 2 | 0/2 | 2/2 | 0/2 |
| Chameleon | 2 | 2/2 | 0/2 | 0/2 |
| Slang | 2 | 2/2 | 0/2 | 2/2 |

Basic example: “If a program malfunctions, I inspect the logs, check recent changes for unintended side effects, and apply targeted debugging techniques to restore correct behavior.”

Chameleon example: “google the error message word for word”

Slang example: “my debugging rizz is completely chopped when syntax errors show up so i just restart the laptop no cap”

The Slang counts include the current formatter applied to the saved model text;
the original capitalized versions are kept in the evidence. “Listed slang” checks
for cooked, chopped, no cap, fr, rizz or aura. These are small format/tone checks,
not a measurement of how often people are fooled.

Run `python scripts/evaluate.py` to reproduce the counts and 13 offline pass/fail
checks. The latest results are in
[evidence/style_evaluation.json](evidence/style_evaluation.json). This supports
the specialization and evaluation-script stretch items without adding new game
screens or services.

## Limitations and biases

Style control is probabilistic: slang can be mild, and Chameleon may miss local
writing patterns. Similarity filtering catches near copies, not all paraphrases.
Student answers and host samples pass a local profanity/obfuscation and text-art
filter before storage. Ambiguous words with benign uses (for example given names
or animal terms) are delegated to the contextual AI screen. Before gameplay,
Gemini classifies collected human text using strict, complete per-answer
decisions. The question is supplied as context rather than a strict relevance
rule. The screen uses context to allow respectful feedback, harmless humor and
unconventional writing while checking for innuendo and targeted harassment. Standalone
ASCII/Unicode art is excluded while inline emojis, punctuation and code remain
valid. Flagged records are removed with transactional
count corrections, and only accepted original text reaches generation. Missing,
invalid or unavailable screening fails closed. Generated answers and writing
notes also pass the local filter. Games predating the current screening rules cannot expose their
old answers. Real evidence is in `evidence/moderation_flow.json` and
`evidence/deployment_readiness.json`.

This is not exhaustive moderation: new encodings and ambiguous context can be
missed, and conservative checks can reject benign text. Prompt isolation and
normalization reduce risks but cannot eliminate them. Host skip/end controls
remain available. No demographic identity is inferred.

Difficulty uses a deliberately simple heuristic: long AI answers are tier 1;
short answers starting lowercase are tier 3; others are tier 2. Correct AI guesses
raise the selection target; incorrect AI guesses lower it. Writing strategy is
separate. These tiers are not calibrated measures of detectability.

Anonymous browser receipts prevent accidental duplicates, not deliberate evasion.
Cleared/unavailable browser storage can defeat this convenience. Host cookies
last one day and have no account recovery. Firestore contention can still produce
a retriable error under load. The app is hosted on Render’s Free service, which can sleep when idle. A generation interrupted by a process restart becomes
retryable after three minutes. Rate limits and provider outages remain possible.

## Misuse and mitigation

Do not use the game to accuse people of academic misconduct. Use anonymous,
non-sensitive answers; Gemini's free tier may use submitted content for product
improvement. Participants should not include private details. API keys and
service-account JSON remain server-side, outside Git and frontend assets. Public
student endpoints do not return other submissions or hidden source labels.
The backend enforces host permissions and checks the Origin of browser mutations.
The setup uses free-tier services, and students do not need accounts.

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

I used coding assistants for planning, code, tests and
troubleshooting. My biggest input was the visual design: I kept pushing for a
simple game that matched my mockup instead of adding more stuff to the screen.

**One idea I accepted:** keeping the HTML frontend separate from the Python
backend. That let me keep the design I wanted and test the game rules separately.

**One idea I changed:** the extra preview banners and temporary navigation. I
had those removed because they made the game feel unfinished and cluttered. I
also revised the Chameleon prompts so they matched student writing habits,
including casing and misspellings, instead of just inventing funny scenarios.

## Rehearsal and portfolio

I rehearsed the game with about 10 CodePath staff members, and it worked well. One person mentioned cold starts, so I’ll open the app before class.
That is my informal rehearsal report; the automated test evidence is separate.

My [portfolio reflection in the README](README.md#my-part-in-the-project) explains
my design contribution and how I worked with AI tools. The
[code](https://github.com/isalcedo1121/guess-the-human) and
[live game](https://guess-the-human.onrender.com/) are public.

## Improvements

Keep testing with more groups, use real feedback to improve difficulty, add
moderation tests when something slips through, and make the data-retention rules
clearer. One classroom game doesn’t tell us how well people can spot AI in every setting.
