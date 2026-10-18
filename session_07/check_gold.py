
"""Check gold SPARQL queries without contacting Gemini."""

from pathlib import Path

from access_layer import open_store, run
from questions_utils import load_questions

HERE = Path(__file__).resolve().parent

questions = load_questions(HERE / "questions.yaml")
store = open_store()

passed = 0
failed = 0

for q in questions:
    if q["refuse"]:
        print(f"Question {q['id']}: REFUSAL TEST — skipped")
        continue

    try:
        result = run(store, q["gold"])

        if isinstance(result, bool):
            summary = str(result)
        else:
            summary = f"{len(result)} row(s)"
            if len(result) == 1:
                summary += f" — {result[0]}"

        print(f"Question {q['id']}: PASS — {summary}")
        passed += 1

    except Exception as error:
        print(f"Question {q['id']}: FAIL — {error}")
        failed += 1

print(f"\nGold queries: {passed} passed, {failed} failed")
