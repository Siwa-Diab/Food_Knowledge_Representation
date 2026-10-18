# Session 07

**Natural Language to SPARQL, Query Validation & Evaluation**

Project: Food Knowledge Representation  |  Course: Knowledge Representation  |  Model: Gemini 3.5 Flash Lite

## Executive summary

Session 07 implemented and tested a natural-language question answering layer over the Food RDF knowledge graph. The system supplies graph/schema context to a Gemini model, receives a SPARQL query or refusal, validates the query, executes accepted queries against a local RDF store, and evaluates results against gold-standard answers. All three evaluation settings completed and the three Part B checker exercises passed.

Key result: schema-only prompting achieved the highest mean F1 (0.833), compared with 0.672 for both examples and repair. All settings correctly refused three questions requiring information outside the graph. These are observed outcomes from the supplied terminal logs, not claims of broader model performance.

## 1. Research question and data context

Main project question: A food safety agency flags a specific ingredient for review. Which branded products declare that ingredient, which food categories are affected, and how many products have incomplete ingredient declarations that prevent a reliable assessment?

The project subset contains 20,000 branded food records. Earlier rule checks found 19,932 usable ingredient declarations and 68 missing or blank declarations; 523 declarations mentioned “sesame” as text. Ingredient-name text matches should not be interpreted as independently verified ingredient presence.

The mapped Food RDF graph was previously generated as session_05/output/food-mapped.nt (approximately 1.20 million triples). The ontology namespace is https://example.org/food-kr/schema#. Relevant classes include Food, BrandedFood, Nutrient and NutrientMeasurement. Relevant predicates include ingredientDeclaration, foodCategory, brandOwner, hasNutrientMeasurement, measuresNutrient and nutrientName.

## 2. System architecture and implementation

### Graph access

The Python access layer opens a local RDF store using pyoxigraph, executes SPARQL and formats returned rows.

### Context and prompt construction

VoID metadata and ontology/schema descriptions provide graph vocabulary. SHACL-encoded example question/query pairs support few-shot prompting.

### Language model integration

Gemini 3.5 Flash Lite generates SPARQL or declines questions judged unanswerable. The API model was changed after Gemini 2.5 Flash Lite returned a 404 availability error.

### Validation and repair

The access layer checks generated queries; the evaluation output identifies the active check as unknown_properties. The repair setting can attempt correction when its configured checks detect problems.

### Interface and testing

A command-line interface (ask.py), an evaluation runner (evaluate.py) and an HTTP service (serve.py) were implemented. CLI query execution is verified by the logs; a successful end-to-end HTTP response was not demonstrated in the supplied evidence.

## 3. Experimental design

Fifteen evaluation questions were used: twelve answerable using the knowledge graph and three deliberately unanswerable from the available data (recent recalls, current Lebanon supermarket prices, and confirmed food-poisoning incidents). Gold queries were checked separately: 12 passed, 0 failed. The three settings were run with the same Gemini model.

Schema: Provide schema information without few-shot query examples.

Examples: Provide schema information and selected example natural-language/SPARQL pairs.

Repair: Use the examples-based pipeline with validation and an opportunity to repair detectable query problems.

The evaluation reports mean F1 across the twelve answerable questions, refusal correctness for the three unanswerable questions, incorrect refusals, and answers obtained after repair. The project’s value-set F1 scoring does not fully preserve row/column relationships for multi-column results.

## 4. Quantitative results

| Metric | Schema | Examples | Repair |
| --- | --- | --- | --- |
| Mean F1 (12 answerable) | 0.833 | 0.672 | 0.672 |
| Questions with F1 = 1.00 | 10 / 12 | 8 / 12 | 8 / 12 |
| Correct refusals | 3 / 3 | 3 / 3 | 3 / 3 |
| Incorrect refusals | 2 | 3 | 3 |
| Answered after repair | 0 | 0 | 0 |

Schema-only prompting exceeded the other settings by 0.161 F1 points (16.1 percentage points on a 0–1 scale). Examples and repair produced the same per-question scores in the recorded run.

## 5. Question-level analysis

| Question | Schema | Examples | Repair | Observation |
| --- | --- | --- | --- | --- |
| Q2 — Food but not BrandedFood | 1.00 | 0.00 | 0.00 | Refused with examples and repair |
| Q4 — Peanut declaration count | 0.00 | 1.00 | 1.00 | Improved with examples |
| Q6 — Missing/blank declarations | 0.00 | 0.00 | 0.00 | Refused in all settings |
| Q8 — Soy-related brand owners | 1.00 | 0.06 | 0.06 | Substantial answer mismatch |
| Q11 — Sodium-related products | 1.00 | 0.00 | 0.00 | Refused with examples and repair |

Interpretation: few-shot examples helped Q4 but coincided with incorrect refusals on Q2 and Q11 and a poor result on Q8. Q6 was refused in every setting despite being answerable. These results show that additional prompt context did not reliably improve this run. The logs alone do not establish why each refusal or incorrect answer occurred.

Repair produced no answers after a repair. This does not prove the repair implementation is faulty: the failed cases were either refusals before query generation or a query with a low F1 score. A property-name checker need not detect a syntactically valid but logically incorrect query. No specific repair-triggering error is documented in the provided output.

## 6. Functional verification and Part B

A CLI smoke test successfully answered “How many branded products are represented in the graph?” using a generated COUNT(DISTINCT ?product) query over food:BrandedFood. The query passed validation (“problems: none”) and returned count = 20000.

Part B checker output: Y1 right; Y2 right; Y3 right; 3 of 3 right. These correspond to the custom example, custom access-layer check and held-out evaluation question exercises. The result confirms the local checker passed all three exercises.

## 7. Limitations and responsible interpretation

- The experiment is small (12 answerable questions), so conclusions are specific to this benchmark and run.
- Only one recorded run per setting is available; model variability was not assessed.
- An executable SPARQL query can still be logically incorrect; unknown-property validation is not a semantic correctness guarantee.
- The benchmark’s value-set F1 may mask row-level errors for queries returning multiple columns.
- Ingredient-declaration searches identify textual mentions, not verified allergens, recalls, or clinical safety outcomes.
- The provided logs confirm CLI execution and checker results, but do not confirm a successful HTTP response from serve.py.
## 8. Reproducibility and commands

```powershell
python .\session_07\ask.py "How many branded products are represented in the graph?"
```powershell
python .\session_07\evaluate.py --setting schema
```powershell
python .\session_07\evaluate.py --setting examples
```powershell
python .\session_07\evaluate.py --setting repair
```powershell
python .\session_07\check_my_access.py
Environment: Windows PowerShell, project virtual environment .venv-s07. Keep GOOGLE_API_KEY in an untracked .env file; use GEMINI_MODEL=gemini-3.5-flash-lite (or the setting read by the installed access layer). API rate limits should be checked before repeating the evaluation.

## 9. Conclusion and recommended follow-up

Session 07 implementation and evaluation are complete based on the supplied CLI and checker evidence. The strongest observed configuration was schema-only prompting (mean F1 0.833). Adding examples lowered mean F1 to 0.672; repair yielded the same result and no repaired answers. All three unanswerable questions were correctly refused under every setting, and all Part B exercises passed (3/3).

For final submission, retain the evaluation logs, inspect the generated queries for Q2, Q6, Q8 and Q11, verify one successful HTTP service request if required by the instructor, and confirm secrets are excluded from version control. These are quality-assurance follow-ups, not evidence that the completed evaluation failed.

## Evidence basis

This report is based on the user-provided terminal outputs for ask.py, evaluate.py (schema, examples, repair), check_my_access.py, and the project details previously established in this conversation. It does not claim independent inspection of the local source files or dataset.
