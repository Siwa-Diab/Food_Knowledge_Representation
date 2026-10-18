"""Display the exact Food text-to-SPARQL prompt without calling the LLM.

Run from the project root:
    python session_07/show_prompt.py "Which products declare sesame?"
"""
import sys
from access_layer import build_prompt, load_examples, pick_examples, schema_text


def main():
    question = " ".join(sys.argv[1:]) or "Which branded products mention sesame in their ingredient declarations?"
    examples = pick_examples(question, load_examples())
    prompt = build_prompt(question, schema_text(), examples)
    print(prompt)
    print("\n" + "-" * 60)
    print(f"examples picked: {', '.join(e['id'] for e in examples)}  ({', '.join(e['question'] for e in examples)})")
    print(f"prompt: {len(prompt):,} characters, {len(prompt.splitlines())} lines")


if __name__ == "__main__":
    main()
