"""Offline checks of real saved AI outputs and application guardrails; no API calls."""

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.generation import format_answer, validate_outputs
from backend.moderation import require_clean
from backend.storage import RoomError

SLANG = re.compile(r'\b(cooked|chopped|no cap|fr|rizz|aura)\b', re.I)


def evaluate():
    saved = json.loads((ROOT / 'evidence/style_comparison.json').read_text())
    case = saved['cases']['informal']
    checks, comparisons = [], []

    def check(name, passed):
        checks.append({'case': name, 'passed': bool(passed)})
        print(f"{'PASS' if passed else 'FAIL'}  {name}")

    # These are new inputs to the same formatter used by the actual game.
    for i, (style, raw, expected) in enumerate((
        ('Slang', 'BRO IM COOKED.', 'bro im cooked'),
        ('Slang', 'ChatGPT saved me fr...', 'chatgpt saved me fr'),
        ('Basic', 'I read the error message.', 'I read the error message.'),
        ('Chameleon', 'i try agian bc idk', 'i try agian bc idk'),
    ), 1):
        check(f'{style}: format case {i}', format_answer(style, raw) == expected)

    for name, text, expected in (
        ('disguised profanity', 'B-1-T-C-H', False),
        ('standalone text art', '(=^..^=)', False),
        ('ordinary words and slang', 'my assignment is cooked fr', True),
    ):
        try:
            require_clean(text)
            accepted = True
        except RoomError:
            accepted = False
        check(f'local intake: {name}', accepted == expected)

    for style in ('Basic', 'Chameleon', 'Slang'):
        rows = [row for row in case['generated_answers'] if row['style'] == style]
        outputs = [format_answer(style, row['text']) for row in rows]
        for i, text in enumerate(outputs, 1):
            try:
                validate_outputs([text], case['human_references'], set())
                valid = style != 'Slang' or (text == text.lower() and not text.endswith('.') and bool(SLANG.search(text)))
            except (ValueError, RoomError):
                valid = False
            check(f'saved {style} answer {i}: safety and format', valid)
        comparisons.append({
            'style': style, 'samples': len(outputs),
            'all_lowercase': sum(text == text.lower() for text in outputs),
            'final_period': sum(text.endswith('.') for text in outputs),
            'recognized_slang': sum(bool(SLANG.search(text)) for text in outputs),
            'examples': [{'raw_model_output': row['text'], 'app_output': text}
                         for row, text in zip(rows, outputs)],
        })

    passed = sum(row['passed'] for row in checks)
    print(f"\nSummary: {passed}/{len(checks)} passed; {len(checks)-passed} failed")
    print('Saved-output comparison:')
    for row in comparisons:
        n = row['samples']
        print(f"{row['style']}: lowercase {row['all_lowercase']}/{n}; "
              f"final period {row['final_period']}/{n}; slang {row['recognized_slang']}/{n}")
    return {
        'mode': 'Offline application checks and recorded real Gemini outputs; no live AI calls',
        'source': 'evidence/style_comparison.json, informal reference set',
        'slang_processing': 'Current application formatter applied to the recorded model text',
        'checks': checks, 'passed': passed, 'total': len(checks),
        'comparison': comparisons,
    }


if __name__ == '__main__':
    report = evaluate()
    (ROOT / 'evidence/style_evaluation.json').write_text(json.dumps(report, indent=2) + '\n')
    sys.exit(0 if report['passed'] == report['total'] else 1)
