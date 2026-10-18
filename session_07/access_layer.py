"""Food Session 07 access layer: English questions become SPARQL queries.

Components:
    schema_text    describe the RDF graph using its VoID metadata
    pick_examples  select three relevant natural-language/SPARQL examples
    ask_model      query Gemini live, record responses, or replay cached responses
    check_query    validate SPARQL and check the Food vocabulary
    answer         generate, check, optionally repair, execute, or refuse

Configuration (project-root .env):
    GOOGLE_API_KEY    Gemini API key (required in live/record mode)
    LLM_MODEL         Gemini model, default gemini-3.8-flash
    LLM_MODE          live (default), record, or replay
    LLM_DELAY         seconds to wait before each new model request (default 4)
    LLM_TIMEOUT       request timeout in seconds (default 180)
    LLM_MAX_ATTEMPTS maximum attempts for transient API errors (default 3)
    SPARQL_ENDPOINT   optional external SPARQL endpoint instead of local N-Triples
"""

import hashlib
import json
import os
import re
import time
from pathlib import Path

import pyoxigraph as ox
import requests
from dotenv import load_dotenv
from rdflib import RDF, Graph, Namespace, URIRef
from rdflib.plugins.sparql import prepareQuery

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
load_dotenv(ROOT / ".env")
GRAPH = ROOT / "session_05" / "output" / "food-mapped.nt"
VOID_FILE = HERE / "void.ttl"
EXAMPLES = HERE / "examples.ttl"
CACHE = HERE / "reference-outputs" / "llm-cache.json"
DATASET = URIRef("https://example.org/food-kr/void")
UL = "https://example.org/food-kr/schema#"
VOID = Namespace("http://rdfs.org/ns/void#")
VEXT = Namespace("http://ldf.fi/void-ext#")
SH = Namespace("http://www.w3.org/ns/shacl#")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
GEMINI = "https://generativelanguage.googleapis.com/v1beta/openai"
PREFIXES = (
    "PREFIX food: <https://example.org/food-kr/schema#>\n"
    "PREFIX ul: <https://example.org/food-kr/schema#>\n"
    "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
)


# ---------------------------------------------------------------- the graph

def open_store(path=GRAPH):
    """Return an endpoint URL or a local in-memory Oxigraph RDF store."""
    endpoint = os.environ.get("SPARQL_ENDPOINT")
    if endpoint:
        return endpoint
    store = ox.Store()
    store.bulk_load(path=str(path), format=ox.RdfFormat.N_TRIPLES)
    return store


def with_prefixes(query):
    return PREFIXES + query


def run(store, query):
    """Execute SELECT or ASK; return a list of dictionaries or a boolean."""
    if isinstance(store, str):
        r = requests.post(
            store,
            data={"query": with_prefixes(query)},
            timeout=60,
            headers={"Accept": "application/sparql-results+json"},
        )
        r.raise_for_status()
        res = r.json()
        if "boolean" in res:
            return res["boolean"]
        return [
            {key: val["value"] for key, val in binding.items()}
            for binding in res["results"]["bindings"]
        ]

    res = store.query(with_prefixes(query))
    if isinstance(res, bool):
        return res
    names = [v.value for v in res.variables]
    return [
        {name: row[name].value for name in names if row[name] is not None}
        for row in res
    ]


# ---------------------------------------------------------------- schema, from VoID

def load_void(path=VOID_FILE):
    """Return class counts and property domain/target descriptions from VoID."""
    g = Graph().parse(path)
    classes, props = {}, {}
    for part in g.objects(DATASET, VOID.classPartition):
        cls = str(g.value(part, VOID["class"]))
        classes[cls] = int(g.value(part, VOID.entities))
        for pp in g.objects(part, VOID.propertyPartition):
            targets = [
                str(g.value(o, VOID["class"]))
                for o in g.objects(pp, VOID.classPartition)
            ]
            targets += [
                str(g.value(o, VEXT.datatype))
                for o in g.objects(pp, VEXT.datatypePartition)
            ]
            props.setdefault(str(g.value(pp, VOID.property)), {})[cls] = targets
    return classes, props


def short(iri):
    return iri.replace(UL, "food:").replace(
        "http://www.w3.org/2001/XMLSchema#", "xsd:"
    )


def schema_text(path=VOID_FILE):
    classes, props = load_void(path)
    lines = [
        f"{short(cls)} ({count:,} things)"
        for cls, count in sorted(classes.items(), key=lambda x: (-x[1], x[0]))
    ]
    for prop, by_class in sorted(props.items()):
        for cls, targets in sorted(by_class.items()):
            lines.append(
                f"{short(cls)} {short(prop)} {' or '.join(short(t) for t in targets)}"
            )
    return "\n".join(lines)


# ---------------------------------------------------------------- example queries

def load_examples(path=EXAMPLES):
    g = Graph().parse(path)
    examples = [
        {
            "id": str(ex).rsplit("/", 1)[-1],
            "question": str(g.value(ex, RDFS.comment)),
            "query": str(g.value(ex, SH.select)),
        }
        for ex in g.subjects(RDF.type, SH.SPARQLExecutable)
    ]
    return sorted(examples, key=lambda ex: ex["id"])


STOP = {
    "the", "a", "an", "of", "is", "are", "which", "what", "how", "many",
    "does", "do", "did", "in", "by", "to", "there", "with", "their",
    "each", "and",
}


def words(text):
    return set(re.findall(r"[a-z0-9_]+", text.lower())) - STOP


def pick_examples(question, examples, k=3):
    qwords = words(question)
    return sorted(
        examples, key=lambda ex: -len(qwords & words(ex["question"]))
    )[:k]


# ---------------------------------------------------------------- prompt and model

RULES = """You write one SPARQL 1.1 SELECT or ASK query for the Food Knowledge Representation graph.
Use only the classes and properties listed in the schema.
The prefix food: is <https://example.org/food-kr/schema#>.
Food resources use IRIs under <https://example.org/food-kr/id/food/usda/>.
Do not invent property names, class names, facts, or ingredient relations absent from the schema.
An ingredient name mentioned in declaration text is a textual match, NOT confirmed ingredient presence.
If a question asks for products declaring an ingredient, search the relevant ingredient declaration text
property using a case-insensitive CONTAINS(LCASE(STR(?text)), "ingredient") filter, only if the schema
actually provides such a property. Never assume a substring match proves an allergen is present.
Use COUNT, DISTINCT, GROUP BY, ORDER BY, LIMIT, OPTIONAL, FILTER as needed.
If the graph lacks the required facts or property, reply exactly:
REFUSE: <the kind of fact the graph is missing>
Otherwise reply with the SPARQL query only."""
RULES_ID = hashlib.sha256(RULES.encode()).hexdigest()[:8]


def build_prompt(question, schema, examples, hints=None):
    parts = [RULES, "", "Schema (the classes, then: class property target):", schema, ""]
    if examples:
        parts.append("Examples:")
        for ex in examples:
            parts += [f"Question: {ex['question']}", ex["query"].strip(), ""]
    if hints:
        parts += ["Your previous query had these problems. Write it again without them:"]
        parts += [f"- {hint}" for hint in hints] + [""]
    parts.append(f"Question: {question}")
    return "\n".join(parts)


def model_name():
    # Honor both the professor's LLM_MODEL setting and the previously used
    # GEMINI_MODEL variable; LLM_MODEL takes precedence when both are set.
    return os.environ.get("LLM_MODEL") or os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")


def prompt_key(prompt):
    return hashlib.sha256(f"{model_name()}\n{prompt}".encode()).hexdigest()[:16]


def _is_daily_quota_error(response):
    """Detect quota-exhaustion responses that waiting a few seconds cannot fix."""
    body = response.text.lower()
    return response.status_code == 429 and any(
        phrase in body for phrase in (
            "perday", "per day", "daily limit", "daily quota", "requests_per_day",
        )
    )


def ask_model(prompt, mode=None):
    """Ask Gemini, record the reply, or replay a previously recorded reply.

    Transient failures (503, 502, 504, 500, 429 minute quotas, timeouts,
    connection errors) use bounded exponential backoff. Daily quota exhaustion
    and non-retryable client errors fail immediately.
    """
    mode = mode or os.environ.get("LLM_MODE", "live")
    if mode not in ("live", "record", "replay"):
        raise ValueError(f"Unknown LLM_MODE: {mode}")

    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    key = prompt_key(prompt)
    if mode == "replay":
        if key not in cache:
            raise SystemExit(
                f"No recorded answer for this prompt (key {key}). "
                "Replay only works for previously recorded prompts with this model."
            )
        return cache[key]["reply"]

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise SystemExit(
            "No key: put GOOGLE_API_KEY in the project root .env, "
            "or run with LLM_MODE=replay."
        )

    delay = max(0.0, float(os.environ.get("LLM_DELAY", "4")))
    timeout = max(1.0, float(os.environ.get("LLM_TIMEOUT", "180")))
    max_attempts = max(1, int(os.environ.get("LLM_MAX_ATTEMPTS", "3")))
    time.sleep(delay)

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.post(
                f"{GEMINI}/chat/completions",
                timeout=timeout,
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model_name(),
                    "temperature": 0,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            if attempt == max_attempts:
                raise SystemExit(
                    f"Gemini request failed after {max_attempts} attempts "
                    f"({type(exc).__name__}). Check your connection or retry later."
                ) from exc
            wait = min(60, 10 * (2 ** (attempt - 1)))
            print(
                f"  (Gemini connection/timeout problem; "
                f"retry {attempt + 1}/{max_attempts} in {wait}s)",
                flush=True,
            )
            time.sleep(wait)
            continue

        if _is_daily_quota_error(response):
            raise SystemExit(
                "Gemini daily quota is exhausted for this project/model. "
                "Wait for the provider's quota reset or use an available model. "
                "Do not retry repeatedly."
            )

        if response.status_code in (429, 500, 502, 503, 504):
            if attempt == max_attempts:
                raise SystemExit(
                    f"Gemini API error ({response.status_code}) after "
                    f"{max_attempts} attempts:\n{response.text[:1500]}"
                )
            wait = min(60, 10 * (2 ** (attempt - 1)))
            print(
                f"  (Gemini temporarily unavailable: HTTP {response.status_code}; "
                f"retry {attempt + 1}/{max_attempts} in {wait}s)",
                flush=True,
            )
            time.sleep(wait)
            continue

        if response.status_code in (400, 401, 403):
            raise SystemExit(
                f"Gemini rejected the request (HTTP {response.status_code}):\n"
                f"{response.text[:1500]}\n"
                "Check model access and GOOGLE_API_KEY; do not share the key."
            )

        if not response.ok:
            raise SystemExit(
                f"Gemini API error ({response.status_code}):\n{response.text[:1500]}"
            )

        try:
            reply = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise SystemExit(
                "Gemini returned an unexpected response format; "
                f"cannot extract a query. Details: {type(exc).__name__}"
            ) from exc

        if not isinstance(reply, str):
            raise SystemExit("Gemini returned no text content for the query.")

        if mode == "record":
            cache[key] = {"model": model_name(), "reply": reply}
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            CACHE.write_text(
                json.dumps(cache, indent=1, sort_keys=True), encoding="utf-8"
            )
        return reply

    raise RuntimeError("Unexpected end of Gemini retry loop")


def clean(reply):
    """Remove Markdown code fences, if any, from generated SPARQL."""
    match = re.search(r"```(?:sparql|SPARQL)?\s*(.*?)```", reply, re.S)
    return (match.group(1) if match else reply).strip()


# ---------------------------------------------------------------- query validation

def ul_terms(query):
    """Local names of food: or ul: terms, prefixed or written as full IRIs."""
    return (
        set(re.findall(r"\b(?:food|ul):([A-Za-z_]\w*)", query))
        | set(re.findall(r"<https://example\.org/food-kr/schema#(\w+)>", query))
    )


def unknown_properties(query, classes, props):
    known = {prop.split("#")[-1] for prop in props}
    used = {term for term in ul_terms(query) if term[0].islower()}
    listed = ", ".join(sorted("food:" + term for term in known))
    return [
        f"food:{term} is not a property of this graph. The properties are: {listed}"
        for term in sorted(used - known)
    ]


CHECKS = [unknown_properties]  # Part B adds unknown_classes (my_access.py)


def check_query(query, void_path=VOID_FILE, checks=None):
    """Return problems with SPARQL syntax or vocabulary (empty means valid)."""
    try:
        prepareQuery(with_prefixes(query))
    except Exception as exc:
        return [f"not valid SPARQL: {str(exc).splitlines()[0][:150]}"]
    classes, props = load_void(void_path)
    return [
        problem
        for check in (CHECKS if checks is None else checks)
        for problem in check(query, classes, props)
    ]


# ---------------------------------------------------------------- answer/repair loop

def answer(question, store, examples, use_examples=True, repair=True,
           checks=None, mode=None, tries=3):
    """Return {query, rows, refused, attempts} for a natural-language question.

    repair=False runs a single query without validation; repair=True validates
    and permits up to two corrected attempts (three attempts total by default).
    """
    schema = schema_text()
    shots = pick_examples(question, examples) if use_examples else []
    hints, attempts = None, []

    for _ in range(tries if repair else 1):
        reply = ask_model(build_prompt(question, schema, shots, hints), mode)
        if reply.strip().upper().startswith("REFUSE"):
            return {
                "query": None, "rows": None,
                "refused": reply.strip(), "attempts": attempts,
            }

        query = clean(reply)
        problems = check_query(query, checks=checks) if repair else []
        if not problems:
            try:
                rows = run(store, query)
                attempts.append({"query": query, "problems": []})
                return {
                    "query": with_prefixes(query), "rows": rows,
                    "refused": None, "attempts": attempts,
                }
            except Exception as exc:
                problems = [
                    f"the endpoint rejected it: {str(exc).splitlines()[0][:150]}"
                ]

        attempts.append({"query": query, "problems": problems})
        hints = problems

    if not repair:
        return {
            "query": with_prefixes(attempts[-1]["query"]),
            "rows": None, "refused": None, "attempts": attempts,
        }
    return {
        "query": None, "rows": None, "attempts": attempts,
        "refused": f"REFUSE: no valid query after {len(attempts)} tries",
    }
