
"""Check Session 07 Part B exercises for the Food Knowledge Graph.

Run:
    python session_07/check_my_access.py

No Gemini API calls are made.
"""

import importlib.util
from pathlib import Path

from access_layer import (
    check_query,
    load_examples,
    load_void,
    open_store,
    run,
)
from questions_utils import load_questions
from score_utils import answer_set

HERE = Path(__file__).resolve().parent


def taken_questions():
    examples = {
        e["question"].strip().lower()
        for e in load_examples()
    }

    questions = {
        q["question"].strip().lower()
        for q in load_questions(HERE / "questions.yaml")
    }

    return examples | questions


def check_y1(path, store):
    try:
        mine = load_examples(path)
    except Exception as e:
        return f"Invalid Turtle: {e}"

    if not mine:
        return "Add at least one SPARQL example."

    for example in mine:
        if example["query"] == "None":
            return "Missing sh:select query."

        if example["question"].strip().lower() in taken_questions():
            return "Question already exists in examples.ttl or questions.yaml."

        problems = check_query(example["query"])

        if problems:
            return f"Invalid SPARQL: {problems[0]}"

        rows = run(store, example["query"])

        if not rows:
            return "SPARQL query returned no results."

    return None


def check_y2(path):
    spec = importlib.util.spec_from_file_location(
        "my_access", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    classes, props = load_void()
    unknown_classes = module.unknown_classes

    # Unknown class, known property
    query1 = """
    SELECT ?product WHERE {
        ?product a food:UnknownFoodClass ;
                 food:brandName ?brand .
    }
    """

    result1 = unknown_classes(query1, classes, props)

    if len(result1) != 1 or "UnknownFoodClass" not in result1[0]:
        return "UnknownFoodClass should be detected."

    # Known class and property
    query2 = """
    SELECT ?product WHERE {
        ?product a food:BrandedFood ;
                 food:brandName ?brand .
    }
    """

    if unknown_classes(query2, classes, props):
        return "BrandedFood is a valid class and should not be reported."

    # Unknown class using its full IRI
    query3 = """
    SELECT ?product WHERE {
        ?product a
        <https://example.org/food-kr/schema#UnknownProductType> .
    }
    """

    result3 = unknown_classes(query3, classes, props)

    if not result3 or not any("UnknownProductType" in x for x in result3):
        return "Full-IRI unknown classes must also be detected."

    return None


def check_y3(path, store):
    try:
        mine = load_questions(path)
    except Exception as e:
        return f"Invalid questions YAML: {e}"

    if not mine:
        return "Add at least one evaluation question."

    for q in mine:
        if q["id"] in range(1, 16):
            return "Question ID already used. Start at 101."

        if q["question"].strip().lower() in taken_questions():
            return "Question already exists in the training or test set."

        if not q["gold"]:
            return "Missing gold SPARQL query."

        problems = check_query(q["gold"])

        if problems:
            return f"Invalid gold query: {problems[0]}"

        rows = run(store, q["gold"])

        if not answer_set(rows):
            return "Gold SPARQL query returned no results."

    return None


def main():
    store = open_store()

    exercises = [
        ("Y1", lambda: check_y1(HERE / "my_examples.ttl", store)),
        ("Y2", lambda: check_y2(HERE / "my_access.py")),
        ("Y3", lambda: check_y3(HERE / "my_questions.yaml", store)),
    ]

    right = 0

    for name, check in exercises:
        try:
            problem = check()
        except Exception as e:
            problem = f"{type(e).__name__}: {e}"

        if problem is None:
            print(f"{name}  right.")
            right += 1
        else:
            print(f"{name}  not yet: {problem}")

    print(f"\n{right} of 3 right.")


if __name__ == "__main__":
    main()
