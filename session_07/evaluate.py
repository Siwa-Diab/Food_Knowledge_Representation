
"""Evaluate the Food Knowledge Graph natural-language access layer.

Examples:
    python evaluate.py
    python evaluate.py --setting repair
    python evaluate.py --quiet
    python evaluate.py --questions my_questions.yaml
    python evaluate.py --add-class-check
"""

import argparse
import importlib.util
import statistics
from pathlib import Path

from access_layer import CHECKS, answer, load_examples, model_name, open_store, run
from questions_utils import load_questions
from score_utils import answer_set, set_f1


HERE = Path(__file__).resolve().parent

SETTINGS = {
    "schema": dict(use_examples=False, repair=False),
    "examples": dict(use_examples=True, repair=False),
    "repair": dict(use_examples=True, repair=True),
}


def evaluate(questions, store, examples, setting, checks, verbose=True):
    f1s = []
    refused_right = 0
    refused_wrong = 0
    repaired = 0
    lines = []

    for q in questions:
        r = answer(
            q["question"],
            store,
            examples,
            checks=checks,
            **SETTINGS[setting],
        )

        tries = len(r["attempts"])
        repaired += tries > 1 and r["refused"] is None

        if q["refuse"]:
            ok = r["refused"] is not None
            refused_right += ok

            lines.append(
                f"  {q['id']:>2}  "
                f"{'refused, right' if ok else 'answered, should refuse':24} "
                f"{q['question']}"
            )
            continue

        if r["refused"]:
            refused_wrong += 1
            f1 = 0.0
        else:
            predicted = answer_set(r["rows"])
            expected = answer_set(run(store, q["gold"]))
            f1 = set_f1(predicted, expected)

        f1s.append(f1)

        lines.append(
            (
                f"  {q['id']:>2}  F1 {f1:.2f}  tries {tries}"
                f"{'  refused' if r['refused'] else ''}"
            ).ljust(33) + q["question"]
        )

    n_refuse = sum(1 for q in questions if q["refuse"])
    mean_f1 = statistics.fmean(f1s) if f1s else 0.0

    summary = (
        f"{setting:9} mean F1 {mean_f1:.3f} "
        f"on {len(f1s)} answerable questions; "
        f"refused {refused_right} of {n_refuse} it should; "
        f"refused {refused_wrong} it should not; "
        f"{repaired} answered after a repair"
    )

    if verbose:
        print("\n".join(lines))

    print(summary)
    return mean_f1


def main():
    ap = argparse.ArgumentParser()

    ap.add_argument("--setting", choices=list(SETTINGS))
    ap.add_argument("--add-class-check", action="store_true")
    ap.add_argument(
        "--class-check-from",
        default=str(HERE / "my_access.py"),
        help=argparse.SUPPRESS,
    )
    ap.add_argument("--questions", action="append", default=[])
    ap.add_argument("--quiet", action="store_true")

    a = ap.parse_args()

    checks = list(CHECKS)

    if a.add_class_check:
        spec = importlib.util.spec_from_file_location(
            "my_access", a.class_check_from
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        checks.append(mod.unknown_classes)

    questions = load_questions(str(HERE / "questions.yaml"))

    for extra in a.questions:
        questions += load_questions(extra)

    store = open_store()
    examples = load_examples()

    print(
        f"model: {model_name()}; "
        f"{len(questions)} questions; "
        f"checks: {', '.join(c.__name__ for c in checks)}"
    )

    for setting in (
        [a.setting] if a.setting else list(SETTINGS)
    ):
        print(f"\n{setting}:")
        evaluate(
            questions,
            store,
            examples,
            setting,
            checks,
            verbose=not a.quiet,
        )


if __name__ == "__main__":
    main()
