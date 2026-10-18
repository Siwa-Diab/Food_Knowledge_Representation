
"""Ask the Food Knowledge Graph one question in English.

Examples:
    python ask.py "Which branded products mention sesame in their ingredient declarations?"
    python ask.py "How many branded products mention sesame?"
    python ask.py --no-repair "Which food categories mention sesame?"

Displays the generated SPARQL queries, validation problems,
and the answer rows or refusal.
"""

import sys

from access_layer import answer, load_examples, model_name, open_store


def show(question, result):
    print(f"question: {question}")

    for i, attempt in enumerate(result["attempts"], 1):
        print(f"\ntry {i}:\n{attempt['query']}")

        problems = attempt["problems"]

        print(
            "  problems: "
            + (
                "none"
                if not problems
                else "; ".join(str(p)[:110] for p in problems)
            )
        )

    if result["refused"]:
        print(f"\nrefused: {result['refused']}")
        return

    rows = result["rows"]

    if isinstance(rows, bool):
        print(f"\nanswer: {rows}")
        return

    print(f"\nanswer: {len(rows)} row{'s' if len(rows) != 1 else ''}")

    for row in rows[:10]:
        print(
            "  "
            + "  ".join(
                f"{key}={str(value).rsplit('/', 1)[-1]}"
                for key, value in row.items()
            )
        )

    if len(rows) > 10:
        print(f"  ... {len(rows) - 10} more")


def main():
    args = sys.argv[1:]

    repair = "--no-repair" not in args

    question = " ".join(
        arg for arg in args if arg != "--no-repair"
    ) or "Which branded products mention sesame in their ingredient declarations?"

    print(f"model: {model_name()}")

    store = open_store()
    examples = load_examples()

    result = answer(
        question,
        store,
        examples,
        repair=repair,
    )

    show(question, result)


if __name__ == "__main__":
    main()
