import json
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from backend.config import Settings
from backend.game import act, prepare, view
from backend.generation import Batch, GeneratedAnswer, generate, validate_notes, validate_outputs


def test_generation_pairs_each_answer_with_its_own_note_and_isolates_references():
    batches = [
        [
            {"text": "I misunderstood the deadline and submitted the assignment late.", "explanation": "I used a complete sentence and a direct explanation of a missed deadline."},
            {"text": "I forgot to upload the file before class.", "explanation": "I went with a brief, straightforward statement about forgetting the upload."},
        ],
        [
            {"text": "i submitted my grocery list instead", "explanation": "I matched the human responses' lowercase opening and missing final punctuation."},
            {"text": "my upload didnt go thru lol", "explanation": "I used the students' short phrasing and informal spellings 'didnt' and 'thru'."},
        ],
        [{"text": "the deadline speedran past me fr", "explanation": "I combined a gaming verb with the casual shorthand 'fr'."}],
    ]
    client = Mock()
    client.models.generate_content.side_effect = [Mock(text=json.dumps({"answers": batch})) for batch in batches]
    humans = ["i cant get this to work lol", "it didnt upload i guess"] + [f"reference {i}" for i in range(100)] + ["LAST ref didnt go thru"]
    with patch("backend.generation.genai.Client") as provider:
        provider.return_value.__enter__.return_value = client
        rows = generate(Settings(_env_file=None, gemini_api_key="test-placeholder"), "Why?", humans, 5)

    assert [row["explanation"] for row in rows] == [item["explanation"] for batch in batches for item in batch]
    prompts = [call.kwargs["contents"] for call in client.models.generate_content.call_args_list]
    assert ["Human reference data:" in prompt for prompt in prompts] == [False, True, False]
    assert json.loads(prompts[1].split('\nHuman reference data: ', 1)[1]) == humans
    assert "usual default AI writing style" in prompts[0]
    assert "capitalization" in prompts[1] and "misspellings" in prompts[1]
    assert "missing punctuation" in prompts[1] and "rather than correcting" in prompts[1]
    assert "Gen Alpha and Gen Z slang" in prompts[2] and '"cooked"' in prompts[2] and '"chopped"' in prompts[2]
    assert "at least one clear slang expression in EACH answer" in prompts[2]
    assert len({row["explanation"] for row in rows if row["style"] == "Chameleon"}) == 2

    state = {"status": "ready", "game": prepare(["one", "two", "three", "four", "five"], rows)}
    act(state, "start")
    while state["status"] == "playing":
        assert "explanation" not in view(state)["current"]
        answer = state["game"]["current"]
        act(state, "guess", answer["id"], "human")
        assert "explanation" not in view(state)["current"]
        act(state, "next", answer["id"])
    assert {row["explanation"] for row in view(state)["history"] if row["actual"] == "ai"} == {row["explanation"] for row in rows}


@pytest.mark.parametrize("note", ["", "x" * 201])
def test_schema_rejects_missing_or_long_writing_notes(note):
    with pytest.raises(ValidationError):
        Batch.model_validate({"answers": [{"text": "An answer", "explanation": note}]})


@pytest.mark.parametrize("note", ["I was asked to sound casual.", "I was given some human examples.", "The answer uses humor."])
def test_notes_reject_passive_instructions_and_generic_third_person(note):
    with pytest.raises(ValueError):
        validate_notes([GeneratedAnswer(text="An answer", explanation=note)], set())


def test_repeated_notes_and_near_duplicate_answers_are_rejected():
    answer = GeneratedAnswer(text="An answer", explanation="I used a calendar joke to describe the missed deadline.")
    with pytest.raises(ValueError):
        validate_notes([answer, answer], set())
    with pytest.raises(ValueError):
        validate_outputs(["My assignment went on a long trip.", "My assignment went on a long trip!"], [], set())
