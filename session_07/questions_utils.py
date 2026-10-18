
"""Read Food Knowledge Representation evaluation questions.

Supports the TEXT2SPARQL layout plus the course's
gold SPARQL queries and refusal labels.
"""

from pathlib import Path
import yaml


def load_questions(path):
    data = yaml.safe_load(
        Path(path).read_text(encoding="utf-8")
    )

    prefix = (data.get("dataset") or {}).get("prefix", "")

    out = []

    for q in data["questions"]:
        out.append({
            "id": q["id"],
            "question": q["question"]["en"],
            "gold": (
                prefix + "\n" + q["gold"]
                if q.get("gold")
                else None
            ),
            "refuse": q.get("refuse"),
        })

    return out
