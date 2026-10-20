# Food Knowledge Representation — Overall Project Report

**Project:** Food Knowledge Representation (Food KR)  
**Course:** Knowledge Representation — M2 Artificial Intelligence  
**Domain:** Food safety, ingredient declarations, and data quality  
**Coverage:** Sessions 01–07, with final demonstration guidance  
**Status:** Project-level documentation based on the team's recorded workflow and results. Exact command-line interfaces should be checked against the current repository.

---

## 1. Executive summary

This project explores how knowledge representation techniques can support **food ingredient-declaration screening**. Starting from a subset of USDA FoodData Central data, the team profiled and checked source tables, represented food data as an RDF knowledge graph, added ontology semantics, validated graph constraints with SHACL, mapped relational data to RDF, evaluated graph-learning methods, and built a natural-language-to-SPARQL question-answering workflow.

The motivating question is:

> **A food safety agency flags a specific ingredient for review. Which branded products declare that ingredient, which food categories are affected, and how many products have incomplete ingredient declarations that prevent a reliable assessment?**

The example screening term is **sesame**. The system detects *textual mentions in ingredient declarations*; it does **not** establish laboratory-confirmed ingredient presence, contamination, regulatory noncompliance, or clinical allergen risk.

### Key recorded findings

| Measure | Recorded result | Interpretation |
|---|---:|---|
| Branded products in the prepared subset | 20,000 | Scope of the selected data |
| Products with usable ingredient declarations | 19,932 | Text available for screening |
| Missing or blank ingredient declarations | 68 | Cannot reliably screen from declaration text |
| Products whose declarations mention `sesame` | 523 | Candidate text matches, **not confirmed hazards** |
| Distinct category labels among flagged products | 76 | Categories touched by text matches |
| Distinct brand-owner labels among flagged products | 336 | Owner labels represented among matches |
| Session 02 RDF graph | ~1,200,721 triples | RDF conversion output |
| Session 05 mapped RDF | 1,206,451 triples | Relational-to-RDF materialization |

The two triple counts come from **different graph-generation approaches** and should not be interpreted as a simple measure of improvement.

---

## 2. Data sources and preparation

The working dataset is a **20,000-product subset** of USDA FoodData Central food records. Four CSV files are used:

| File | Recorded rows | Role |
|---|---:|---|
| `food.csv` | 20,000 | Food identifiers, descriptions, and food-level metadata |
| `branded_food.csv` | 20,000 | Branded-product metadata and ingredient declarations |
| `food_nutrient.csv` | 261,255 | Links between foods and nutrient values |
| `nutrient.csv` | 477 | Nutrient definitions |

The principal join key is the food identifier (`fdc_id`) where applicable. Product descriptions, categories, brands, and ingredient declarations may be incomplete or inconsistently populated. These properties motivate explicit data-quality rules and cautious interpretation of missing values.

### Core interpretation rules

- A declaration containing the word **sesame** is a **text match** and a screening candidate, not definitive evidence of ingredient content.
- A missing declaration means **unknown**, not “sesame-free.”
- Product-category and brand-owner names are labels from source data; apparent similarity does not automatically establish identity.
- Results depend on the selected subset, text-matching logic, and graph/mapping version.

---

## 3. End-to-end project architecture

```text
USDA FoodData Central source files
                 |
                 v
SESSION 01 — Prepare subset, profile tables, define and test rules
                 |
                 v
SESSION 02 — Convert CSV records to RDF; named graphs; SPARQL
                 |
                 v
SESSION 03 — Add OWL ontology semantics and reasoning
                 |
                 v
SESSION 04 — Validate RDF using SHACL; record provenance
                 |
                 v
SESSION 05 — Load relational data; map with R2RML/Ontop;
             compare materialized and virtual RDF; entity resolution
                 |
                 +-------------------------------+
                 |                               |
                 v                               v
SESSION 06 — Graph learning,              SESSION 07 — VoID schema,
             link prediction                           examples, Gemini,
             and evaluation                            NL-to-SPARQL,
                                                       validation, execution
                 |                               |
                 +---------------+---------------+
                                 v
                       FINAL DEMONSTRATION
                    Findings, limitations, Q&A
```

**Important:** This is a conceptual learning pipeline, not a claim that every session literally consumes the previous session's final output. For example, Session 07's observed access-layer configuration loads the **Session 05** materialized RDF file by default.

---

## 4. Session 01 — Environment, data profiling, and constraints

### Objective

Prepare a reproducible food-data subset, understand its columns and missing values, and turn the main research question into **testable data-quality and screening checks**.

### Main files

| File | Purpose |
|---|---|
| `prepare_subset.py` | Create a manageable, consistent subset of source food data |
| `profiling.py` | Inspect table size, columns, missingness, and distributions |
| `rule_checks.py` | Run project-specific screening and data-quality checks |
| `constraint_inventory_template.csv` | Record rules, counts, meanings, and implications |
| `food.csv`, `branded_food.csv`, `food_nutrient.csv`, `nutrient.csv` | Prepared source tables |

### Workflow

1. Prepare the local Python environment and required packages.
2. Run `prepare_subset.py` to create the four subset CSV files.
3. Run `profiling.py` to understand schemas, row counts, and missing values.
4. Define rules relevant to the central food-safety question.
5. Run `rule_checks.py` with a screening ingredient such as `sesame`.
6. Record the results and interpretation in the constraint inventory.

A previously used screening invocation was:

```powershell
python rule_checks.py --ingredient sesame
```

Run it from the folder containing that script, or supply its full relative path.

### Recorded findings

- **20,000** branded food records selected.
- **19,932** records had usable ingredient declarations.
- **68** declarations were missing or blank.
- **523** usable declarations mentioned `sesame`.
- The screening output included **76** distinct food-category labels and **336** brand-owner labels among matches.
- Earlier checks reported **0** broken food links and **0** missing barcodes, while **10** flagged rows shared barcodes. These counts are specific to the corresponding checks and subset.

### Why this session matters

Without profiling and explicit constraints, later SPARQL queries can return technically valid but misleading results. Session 01 defines what a trustworthy answer should mean and exposes unknown data early.

---

## 5. Session 02 — RDF knowledge graph and SPARQL

### Objective

Transform relational/CSV food data into **RDF triples** with stable identifiers, organize statements into graphs, and query the result using **SPARQL**.

### Main files

| File | Purpose |
|---|---|
| `food_iri.py` | Centralize resource identifier / IRI construction |
| `convert_to_rdf.py` | Transform food tables into RDF statements |
| `named_graphs.py` | Organize and report named-graph content |
| `load_fuseki.py` | Load RDF into Apache Jena Fuseki |
| `queries.sparql` | Store representative SPARQL queries |
| `run_queries.py` | Execute queries and inspect results/timing |
| `check_my_queries.py` | Check student query exercises |
| `neo4j_comparison.py` | Compare graph representations/query approaches |
| `rdfs_entailment_demo.py` | Demonstrate RDFS entailment behavior |
| `lab_walkthrough.py` | Guided session workflow |

### Workflow

1. Read the prepared CSV tables and define namespaces/IRIs.
2. Represent foods, brands, categories, nutrient relationships, and declarations as RDF resources and properties.
3. Serialize the graph as Turtle (`.ttl`), and organize named graphs in TriG (`.trig`) where applicable.
4. Inspect graph sizes and named-graph summaries.
5. Load the RDF data into Fuseki.
6. Run SPARQL queries for filtering, joins, counts, and aggregations.
7. Explore the RDFS entailment and Neo4j comparison exercises.

### Recorded output

- `food_knowledge_graph.ttl`: approximately **1,200,721 triples**.
- A `.trig` representation and named-graph/query reports were also produced.

### Why this session matters

RDF converts disconnected tables into a connected semantic graph. SPARQL can traverse relationships without requiring users to manually reconstruct each SQL join, while the use of IRIs makes entities and predicates explicit.

---

## 6. Session 03 — OWL ontology and reasoning

### Objective

Move beyond raw triples by defining **domain classes, properties, logical relationships, and inference rules** in an OWL ontology.

### Main artifacts and concepts

- `food-reasoning-clean.ttl`: the recorded ontology/reasoning graph.
- Classes such as `Food`, `BrandedFood`, `Ingredient`, and `SesameIngredient`.
- A relation such as `hasDeclaredIngredient`.
- An equivalent-class construct for `SesameDeclarationCandidate`.
- A disjointness demonstration in `domain-mistake.ttl`.
- Reasoner scripts and outputs used to explore entailments and contradictions.

### Workflow

1. Define the important domain classes and properties.
2. Add class hierarchies, domain/range statements, and selected OWL restrictions.
3. Model declaration-based candidate concepts using the ontology vocabulary.
4. Run reasoning to inspect inferred class membership or relationships.
5. Introduce a deliberate modeling mistake to see how disjointness/inconsistency can be exposed.
6. Compare explicitly asserted statements with inferred statements.

### Why this session matters

An ontology makes **meaning** machine-readable. Reasoning can derive facts that were not written as explicit triples, but only within the semantics actually modeled. Inferred membership in a declaration-based candidate class does **not** prove laboratory-confirmed allergen presence.

**Ontology note:** The team used a project-specific ontology and reused standard RDF/OWL vocabulary; it was not documented as a wholesale import of a single complete external food ontology.

---

## 7. Session 04 — SHACL validation and provenance

### Objective

Use **SHACL** to check whether RDF data satisfies structural and business constraints, and document the origin of important information.

### Main files

| File | Purpose |
|---|---|
| `food-shapes.ttl` | Core SHACL constraints for the food graph |
| `my_shapes.ttl` | Student-authored or extended shapes |
| `validate.py` | Execute SHACL validation |
| Validation report outputs | Record conforms/violations and affected nodes |
| Provenance-related artifacts | Track data origin or derivation context |

### Workflow

1. Identify constraints suggested by Session 01 profiling and checks.
2. Express suitable constraints as SHACL node/property shapes.
3. Validate the RDF graph.
4. Inspect violations, severity, paths, and focus nodes.
5. Test a deliberately broken sample to show that validation catches defects.
6. Record validation timing and provenance information.

### Why this session matters

OWL and SHACL solve different problems: **OWL describes and reasons about meaning**, while **SHACL checks data against specified expectations**. Missing declarations can be flagged for review without being incorrectly interpreted as negative ingredient evidence.

**Result availability:** This report does not assert a final SHACL violation count because the exact latest validation report was not provided in the recorded project summary.

---

## 8. Session 05 — Relational-to-RDF mapping and entity resolution

### Objective

Show how existing **PostgreSQL** tables can be exposed as a knowledge graph using **R2RML**, and compare materialized RDF with the earlier direct CSV-to-RDF graph. Explore **Ontop** virtual knowledge graph querying and entity resolution.

### Main files and components

| File/component | Purpose |
|---|---|
| `load_database.py` | Load food tables into PostgreSQL |
| `food-mapping.ttl` | Define relational-to-RDF mapping rules (R2RML) |
| `materialize.py` | Produce RDF triples from relational tables |
| `compare_with_session2.py` | Compare mapped RDF against Session 02 RDF |
| `ontop/run_ontop.py` | Exercise Ontop virtual graph querying |
| `food.properties` | Ontop/database configuration |
| `er/make_teaching_set.py` | Prepare entity-resolution teaching/evaluation data |
| `er/match_brands.py` | Explore brand matching |
| `output/food-mapped.nt` | Materialized RDF output used later by Session 07 |

### Workflow

1. Create/populate the relational database from prepared food CSVs.
2. Define how rows, keys, and columns map to RDF subjects, predicates, and objects.
3. Materialize the mapping to N-Triples (`food-mapped.nt`).
4. Run representative SPARQL queries and SHACL checks on mapped data.
5. Compare the mapped RDF with the Session 02 RDF graph.
6. Test Ontop's virtual knowledge graph approach, which answers queries through mappings rather than requiring all RDF to be pre-generated.
7. Investigate brand-name/entity-resolution examples and report uncertainties.

### Recorded comparison

| Comparison measure | Triple count |
|---|---:|
| Session 02 direct RDF | 1,200,721 |
| Session 05 materialized RDF | 1,206,451 |
| Shared triples | 1,200,682 |
| Only in Session 02 | 39 |
| Only in Session 05 | 5,769 |

The counts reconcile: 1,200,682 + 39 = 1,200,721; 1,200,682 + 5,769 = 1,206,451.

### Important data-quality finding

Some mapped values appeared as the **literal string `"None"`** rather than a genuinely absent value:

| Mapped field | Recorded `"None"` string count |
|---|---:|
| `brandName` | 5,434 |
| `brandOwner` | 172 |
| `foodCategory` | 94 |
| `ingredientDeclaration` | 68 |

This matters because `"None"` is an RDF literal and can be mistakenly counted as a real declaration or category. It must be handled explicitly in mappings and queries.

### Why this session matters

Most organizational data lives in relational systems. Session 05 demonstrates a path from operational tables to semantic queries, while the graph comparison reveals that two reasonable transformation pipelines can produce **nonidentical RDF**. Entity resolution also shows why matching names is not equivalent to proving two entities are the same.

---

## 9. Session 06 — Graph learning and link prediction

### Objective

Evaluate whether machine-learning methods can discover or rank graph links and compare their results against a **simple, meaningful baseline**.

### Main files

| File | Purpose |
|---|---|
| `build_graph.py` | Construct the learning graph/data structures |
| `learning_utils.py` | Shared training/evaluation helpers |
| `baseline.py` | Baseline model experiments |
| `gnn.py` | Graph neural network experiment |
| `link_prediction.py` | Link-prediction workflow |
| `link_prediction_colab.py` | Colab-friendly link-prediction run, including TransE experiment |
| `my_learning.py`, `check_my_learning.py` | Student exercises and checking |
| `SESSION_06_REPORT.md` | Session-specific experimental report |
| `data/food-graph.pt` | Saved graph-learning artifact |
| `transe_results.csv` | Recorded link-prediction scores |

### Workflow

1. Build a machine-learning-ready graph from the KR data.
2. Define a train/test setup with hidden links to be ranked.
3. Train and evaluate graph-learning methods.
4. Compare TransE link prediction with a **Popularity** ranking baseline.
5. Repeat the experiment using **three random seeds** (`0`, `1`, `2`) to check stability.
6. Report ranking metrics and acknowledge cold-start exclusions.

### Recorded link-prediction results

| Seed | Method | MRR | Hits@1 | Hits@10 |
|---:|---|---:|---:|---:|
| 0 | TransE | 0.091 | 0.037 | 0.178 |
| 0 | Popularity | 0.133 | 0.043 | 0.317 |
| 1 | TransE | 0.076 | 0.026 | 0.161 |
| 1 | Popularity | 0.136 | 0.046 | 0.312 |
| 2 | TransE | 0.082 | 0.030 | 0.168 |
| 2 | Popularity | 0.135 | 0.045 | 0.305 |

**Across-seed means (rounded):**

| Method | Mean MRR | Mean Hits@1 | Mean Hits@10 |
|---|---:|---:|---:|
| TransE | 0.083 | 3.1% | 16.9% |
| Popularity | 0.135 | 4.5% | 31.1% |

- **MRR (Mean Reciprocal Rank)** rewards ranking the correct target near the top. It is **not classification accuracy**.
- **Hits@1** is the fraction of evaluated cases with the correct answer ranked first.
- **Hits@10** is the fraction with the correct answer among the top ten.
- The **Popularity baseline outperformed TransE in all three seeds** on these recorded metrics.
- Seed 1 scored **1,984** hidden links and excluded **6** cold-start cases; seed 2 scored **1,985** and excluded **5**. These exclusions should be disclosed when discussing evaluation scope.

### Why this session matters

A more complex model is not automatically better. The comparison gives an evidence-based reason to retain strong baselines and evaluate learning systems with the correct metric. The results above describe **link prediction only**; they should not be presented as performance scores for every Session 06 baseline or GNN task.

---

## 10. Session 07 — Natural language to SPARQL using Gemini

### Objective

Allow a user to ask a question in **ordinary English**, generate a SPARQL query grounded in the graph's vocabulary, validate the query, execute it against the graph, and return an answer or a refusal.

### Main files

| File | Role in the workflow |
|---|---|
| `access_layer.py` | Core access layer: graph connection, schema context, examples, LLM call, query checking, execution, and repair/refusal flow |
| `make_void.py` | Generate VoID-style graph/schema description |
| `examples.ttl` | Example English questions paired with SPARQL queries |
| `ask.py` | Command-line entry point for a question |
| `serve.py` | Service-oriented entry point; exact route/UI behavior should be checked in source |
| `questions.yaml` | Evaluation questions/reference material |
| `questions_utils.py` | Helpers for evaluation questions |
| `check_gold.py` | Check reference/gold evaluation material |
| `evaluate.py` | Run evaluation variants |
| `score_utils.py` | Scoring utilities |
| `my_access.py` | Student extension of access-layer checks |
| `check_my_access.py` | Checker for the student extension |
| `my_examples.ttl`, `my_questions.yaml` | Student-authored examples and evaluation questions |
| `SESSION07_REPORT.md` | Session-specific analysis/report |

### Observed configuration and behavior

From a previously shared `access_layer.py` version:

- If `SPARQL_ENDPOINT` is configured, the system can use a Fuseki SPARQL endpoint.
- Otherwise, it loads `session_05/output/food-mapped.nt` into a local **pyoxigraph** store.
- `void.ttl` supplies a compact schema/graph description.
- `examples.ttl` contains SPARQL examples (using `sh:SPARQLExecutable`-style resources), and the system selects examples relevant to a question.
- Gemini generates SPARQL using the available schema and instructions.
- Query checks include SPARQL parsing and restrictions on unknown properties; the student extension adds unknown-class checks.
- Invalid or unsupported generations may trigger repairs or a refusal. Validation does **not** guarantee that every syntactically valid query is semantically correct.
- The implementation supports `LLM_MODE` settings such as `live`, `record`, and `replay` in the observed version; confirm the current environment configuration before the defense.

### Conceptual runtime flow

```text
English question
      |
      v
Read schema summary (VoID) + select relevant examples
      |
      v
Gemini generates candidate SPARQL
      |
      v
Parse/check SPARQL and allowed graph vocabulary
      |
      +-- invalid --> feedback/repair attempt --> retry or refuse
      |
      v
Execute SELECT/ASK query against RDF store
      |
      v
Return results (or a justified refusal)
```

### Example presentation questions

1. **How many branded foods mention sesame in their ingredient declarations?**
2. **Which food categories have the most branded foods whose ingredient declarations mention sesame?**
3. **How many branded foods have missing ingredient declarations?**

A useful boundary-testing question is:

> Which products have been laboratory-confirmed to contain sesame contamination?

The dataset does not establish laboratory confirmation. A reliable answer should state that limitation rather than inventing a result. **Test the actual refusal behavior before demonstrating it.**

### Recorded evaluation summary

An earlier Session 07 summary reported **15 questions** and three evaluation configurations:

| Configuration | Reported mean F1 |
|---|---:|
| Schema-only | 0.833 |
| Schema + examples | 0.672 |
| Repair configuration | 0.672 |

It also reported **3/3 correct refusals** for each configuration. These are *recorded summary values*, not freshly verified against the latest `SESSION07_REPORT.md`. They should be rechecked before inclusion in a graded final presentation. The example-assisted configuration did **not** improve mean F1 in that run; additional examples are not guaranteed to help.

### Observed command-line usage

From the project root, the following invocation pattern was used:

```powershell
python .\session_07\ask.py "How many branded foods have missing ingredient declarations?"
```

**Note:** In the observed version, `python .\session_07\ask.py --help` did **not** display usage instructions; it treated `--help` as a question and returned an LLM refusal. Do not rely on a standard argparse-style help option unless the script is updated.

### Why this session matters

Session 07 makes the graph accessible to nontechnical users while preserving a structured SPARQL execution path. Its most important feature is **not simply generating queries**; it is trying to constrain answers to the actual graph schema and to distinguish supported questions from unsupported ones.

---

## 11. Cross-session traceability

| Project requirement | Where addressed | Evidence/artifact |
|---|---|---|
| Prepare usable data | Session 01 | Four subset CSV files |
| Identify missing declarations | Session 01; Sessions 04/07 | Rule counts; validation; natural-language queries |
| Identify ingredient text matches | Sessions 01/02/07 | Screening rule; RDF/SPARQL; natural-language query |
| Model linked entities | Session 02 | RDF graph and named graphs |
| Define domain meaning | Session 03 | OWL ontology and reasoning examples |
| Enforce graph expectations | Session 04 | SHACL shapes and reports |
| Integrate relational data | Session 05 | PostgreSQL, R2RML, Ontop |
| Compare representations | Session 05 | Triple-set comparison |
| Investigate entity matching | Session 05 | Brand entity-resolution exercises |
| Evaluate predictive graph methods | Session 06 | Link-prediction metrics and baseline comparison |
| Ask English questions | Session 07 | Gemini → SPARQL access layer |
| Refuse unsupported claims | Session 07 | Query checks and refusal evaluation |

---

## 12. Recommended final demonstration

A concise live demonstration should show **three pretested questions** through `session_07/ask.py`. Display the question, generated SPARQL (if the script prints it), and resulting answer. Explain that the result comes from the RDF graph rather than from Gemini's general knowledge.

A PowerShell script can run multiple prepared questions sequentially from the project root:

```powershell
$questions = @(
    "How many branded foods mention sesame in their ingredient declarations?"
    "Which food categories have the most branded foods whose ingredient declarations mention sesame?"
    "How many branded foods have missing ingredient declarations?"
)

foreach ($question in $questions) {
    Write-Host "`n========================================"
    Write-Host "QUESTION: $question"
    Write-Host "========================================"
    python .\session_07\ask.py "$question"
    Read-Host "Press Enter to continue"
}
```

This is **presentation guidance**, not an assertion that the script was already saved to the repository. A short screen recording is a useful backup if API access or the local graph environment fails.

### Suggested oral-defense explanation

> We began with food records that were incomplete and distributed across tables. We profiled the data and made our screening rules explicit. We then represented the information as RDF, defined ontology semantics, and validated the graph using SHACL. We also connected relational data to RDF using mappings, tested graph-learning approaches against a baseline, and finally added a natural-language interface that generates and checks SPARQL. The system supports investigation of ingredient declarations, but it does not prove contamination or allergen presence.

---

## 13. Limitations and responsible interpretation

1. **Ingredient mention ≠ verified ingredient or contamination.** The source is declaration text, not laboratory evidence.
2. **Missing information ≠ absence.** The 68 blank declarations are unresolved for text-based screening.
3. **Subset limitation.** Results refer to the prepared 20,000-product subset, not all foods in FoodData Central.
4. **Mapping differences.** Session 02 and Session 05 RDF graphs are not identical; Session 05 includes unwanted literal `"None"` values.
5. **Entity resolution uncertainty.** Similar brand names do not automatically denote the same entity.
6. **Ontology/reasoning scope.** Inferences depend on the assertions and axioms encoded, not on real-world facts that are absent from the data.
7. **LLM reliability.** Generated SPARQL can be syntactically valid yet semantically wrong; repairs and examples do not guarantee accuracy.
8. **Evaluation scope.** Link-prediction ranking metrics are not overall system accuracy, and LLM evaluation values require confirmation against the final report.
9. **Operational dependencies.** Live Gemini calls may require a valid API key and internet access; graph execution also depends on the configured store.

---

## 14. Main achievements

The project demonstrates a complete **knowledge representation lifecycle**:

- Data understanding and explicit constraints.
- RDF conversion and SPARQL query execution.
- OWL-based domain modeling and reasoning.
- SHACL data validation and provenance awareness.
- Relational-to-RDF mapping and graph comparison.
- Experimental graph learning with transparent baseline evaluation.
- Natural-language access to structured graph data with validation and refusal behavior.

A particularly important result is that **simpler methods sometimes performed better**: the Popularity baseline beat TransE on the recorded link-prediction metrics across all three seeds. Another important finding is that **the way data is mapped matters**: the Session 05 graph differed from Session 02 and included missing values incorrectly serialized as strings.

---

## 15. Recommended next steps

- Reconcile `"None"` strings with truly missing RDF values in Session 05 mappings and re-run key counts.
- Re-run and archive the latest SHACL validation report.
- Verify Session 07 evaluation figures against the current `SESSION07_REPORT.md` and `evaluate.py` outputs.
- Test and save exact live-demo queries and outputs, including one unsupported question.
- Add a small `demo.ps1` and a recorded fallback demo if desired.
- Include environment/setup instructions and dependency versions in the project root documentation.
- Document any differences between Session 01 text-screening logic and Session 07 SPARQL screening logic.

---

## 16. Repository documentation note

This report is intended to be saved at the **project root** as:

```text
Food_Knowledge_Representation/
├── FOOD_KR_OVERALL_PROJECT_REPORT.md
├── session_01/
├── session_02/
├── session_03/
├── session_04/
├── session_05/
├── session_06/
└── session_07/
```

The directory names above represent the **conceptual session organization**. Use the actual names in your repository if they differ. File roles are based on the recorded project work; where exact latest code or output was unavailable, the report identifies the need for verification rather than claiming an unverified execution result.

---

**End of report.**
