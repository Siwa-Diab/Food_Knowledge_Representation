"""Food KR TEXT2SPARQL HTTP access layer.

Run from the project root:
    python session_07/serve.py

Example:
    GET /?question=How%20many%20branded%20products%20are%20there%3F&dataset=https%3A%2F%2Fexample.org%2Ffood-kr%2F

The response contains the generated SPARQL query (not its result rows).
"""

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from access_layer import answer, load_examples, open_store

DATASET = "https://example.org/food-kr/"
STORE, EXAMPLES = open_store(), load_examples()


def query_for(question):
    result = answer(question, STORE, EXAMPLES)
    if result["refused"]:
        reason = str(result["refused"]).replace("\r", " ").replace("\n", " ")
        return f"# {reason}\nSELECT * WHERE {{ FILTER(false) }}"
    return result["query"]


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path not in ("", "/"):
            self.send_json(404, {"error": "Unknown path. Use /?question=..."})
            return

        args = parse_qs(parsed.query)
        question = args.get("question", [""])[0].strip()
        dataset = args.get("dataset", [DATASET])[0]

        if not question or dataset != DATASET:
            self.send_json(400, {
                "error": "Provide a nonempty question and the Food dataset identifier.",
                "dataset": DATASET,
                "example": "/?question=How%20many%20branded%20products%20are%20there%3F",
            })
            return

        try:
            query = query_for(question)
        except (SystemExit, Exception) as exc:
            # A failed provider request is not a refusal about missing graph facts.
            self.send_json(503, {"error": str(exc)})
            return

        self.send_json(200, {"dataset": dataset, "question": question, "query": query})

    def log_message(self, fmt, *args):
        print("  " + fmt % args)


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    print(f"Serving Food TEXT2SPARQL at http://{host}:{port}/", flush=True)
    print(f"Dataset: {DATASET}", flush=True)
    HTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
