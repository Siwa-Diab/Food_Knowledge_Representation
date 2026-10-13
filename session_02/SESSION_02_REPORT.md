# Session 2 Report — RDF, SPARQL, and Property Graph Comparison

**Project:** Food Knowledge Representation — USDA Branded Food Safety Screening  
**Course:** Knowledge Representation, Session 2 — From Tables to a Graph You Can Query  
**Status:** Core Session 2 implementation and optional RDFS/walkthrough demonstrations completed and tested  
**Date:** Updated 13 October 2026

## 1. Research question and scope

> A food safety agency flags a specific ingredient for review. Which branded products declare that ingredient, which food categories are affected, and how many products have incomplete ingredient declarations that prevent a reliable assessment?

The demonstrator uses the keyword **sesame**. A case-insensitive text match in an ingredient declaration identifies a *candidate for review*, not independently verified ingredient presence, allergen exposure, contamination, or a regulatory violation. Products without a usable ingredient declaration remain **UNKNOWN**, not sesame-free.

This is an analysis of a **processed subset of USDA FoodData Central Branded Foods**, not of every food product in the complete USDA database.

## 2. Input data

Four CSV tables in `data/processed/` were converted and analyzed:

| Source table | Rows | Identity and relevant fields |
|---|---:|---|
| `food.csv` | 20,000 | `fdc_id`, `description`, `data_type` |
| `branded_food.csv` | 20,000 | `fdc_id`, `ingredients`, `branded_food_category`, `brand_owner`, `brand_name`, `gtin_upc` |
| `food_nutrient.csv` | 261,255 | `id`, `fdc_id`, `nutrient_id`, `amount` |
| `nutrient.csv` | 477 | `id`, `name`, `unit_name` |

`fdc_id` joins branded-food attributes to food descriptions; `food_nutrient.fdc_id` refers to a food, and `food_nutrient.nutrient_id` refers to a nutrient definition. The measurement table has its own stable source identifier, `id`, so measurement resources need not be anonymous blank nodes.

## 3. IRI naming and RDF model

The project created its own IRI functions in `session_02/food_iri.py`, separate from the professor's Brunel IRI module.

| Resource | IRI pattern or example |
|---|---|
| Vocabulary | `https://example.org/food-kr/schema#` |
| Food product | `https://example.org/food-kr/id/food/usda/1002189` |
| Nutrient | `https://example.org/food-kr/id/nutrient/usda/1003` |
| Source graph | `https://example.org/food-kr/id/graph/usda/branded_food` |

The resource IRIs incorporate **kind**, **source**, and **source key**, limiting accidental identity collisions. The `example.org` namespace is a demonstrator placeholder; a published system should adopt an institution-controlled persistent namespace.

The RDF representation includes `Food`, `BrandedFood`, `Nutrient`, and `NutrientMeasurement`. `BrandedFood` is modeled as a specialization of `Food`, using the **same food IRI** for shared `fdc_id`. Food and branded-food attributes are RDF literals; food-to-measurement and measurement-to-nutrient links are RDF object relationships. Numeric amounts are measurements, not ingredient-presence assertions.

**Missing information:** When an ingredient declaration is absent, the model omits the declaration property rather than writing a fabricated `0`, `false`, or `sesame-free` fact. RDFS domain/range statements describe semantics and potential entailments; they are not integrity constraints.

## 4. RDF conversion and named graphs

`session_02/convert_to_rdf.py` generated a Turtle serialization for loading the union of triples and a TriG serialization preserving source-specific named graphs. `named_graphs.py` checked the named graph counts with Oxigraph.

| Named graph | Triples |
|---|---:|
| `food_nutrient` | 1,045,020 |
| `branded_food` | 114,232 |
| `food` | 40,000 |
| `nutrient` | 1,431 |
| `schema` | 38 |
| **Total** | **1,200,721** |

The named graphs preserve **which source table supplied each assertion**. The `NutrientMeasurement` instances were found in the `food_nutrient` named graph. The converter also reported a 21-triple sample.

**Files:** `session_02/output/food_knowledge_graph.ttl`, `session_02/output/food_knowledge_graph.trig`, and `session_02/output/named_graphs_report.txt`.

## 5. Fuseki deployment and SPARQL verification

Apache Jena Fuseki 5.5.0 ran in Docker, exposed locally at `http://localhost:3031`, with a persistent TDB2 dataset named `foodkr`. The Python loader uploaded `food_knowledge_graph.ttl` using HTTP and confirmed:

> **Fuseki contains 1,200,721 triples. SUCCESS: Triple count matches the RDF conversion.**

The upload took **28.0 seconds** in the recorded run. A SPARQL query in the Fuseki web UI also counted **20,000 `BrandedFood` resources**.

Oxigraph independently loaded and queried the graph without requiring the Fuseki service.

## 6. Food-safety questions and verified answers

| Query | Question | Observed answer |
|---|---|---|
| Q1 | Show sample products whose declarations mention sesame | 10 displayed (query `LIMIT 10`) |
| Q2 | Count sesame candidates by category | 75 category groups |
| Q3 | Count sesame candidates by brand owner | 335 brand-owner groups |
| Q4 | Does any sesame candidate lack nutrient measurements? | `true` |
| Q5 | How many declarations are usable or missing? | 20,000 total; 19,932 usable; 68 missing |
| Q6 | Show products with unknown ingredient declarations | 10 displayed (query `LIMIT 10`) |
| Q7 | Construct product-to-category statements for candidates with categories | 520 RDF triples |

An additional aggregate query in the Fuseki interface confirmed:

| Sesame candidates | With category | With brand owner |
|---:|---:|---:|
| **523** | **520** | **520** |

The later Cypher count confirmed **523 candidates**, **520 with category**, and **3 without category**. The Q7 result of 520 is **not** the total candidate count: it excludes three candidates with no category information. The 68 missing ingredient declarations constitute **0.34%** of the 20,000 branded-food records; these are *unknown* with respect to the sesame screening question.

The first category groups in the recorded result included Dips & Salsa (64), Breads & Buns (54), and Popcorn, Peanuts, Seeds & Related Snacks (32). Counts reflect declaration text matching, not verified ingredient composition.

### 6.1. Research findings and handling incomplete declarations

For the selected ingredient **sesame**, the 20,000 branded-food records divide into three **text-screening states**, not three verified safety classifications:

| Screening state | Definition | Number of products | Interpretation |
|---|---|---:|---|
| **Candidate for review** | Usable ingredient declaration contains the case-insensitive substring `sesame` | **523** | A textual match warrants investigation; it is not independent confirmation of composition or contamination |
| **No textual match** | Usable declaration exists, but does not contain that substring | **19,409** | No match under this specific keyword rule; **not** proof that the product is sesame-free |
| **Unknown** | No usable ingredient declaration is available | **68** | Insufficient declaration data to apply the screening rule |
| **Total** | All processed branded foods | **20,000** | 523 + 19,409 + 68 = 20,000 |

The **68 unknown records represent 0.34%** of the subset. The other 19,932 records have usable declarations (99.66%). Of the 523 sesame candidates, **520 have category information and three do not**. Therefore, the 520 category-linked triples returned by Q7 should never be presented as the complete number of sesame candidates.

**Knowledge-representation interpretation.** Missing declaration data must not be turned into a fabricated negative ingredient assertion. Under RDF's usual open-world interpretation, failure to find an assertion does not, by itself, establish its negation. The project uses an explicit, application-level **Unknown** screening status to communicate that the ingredient-declaration evidence is insufficient. Conversely, a usable declaration with no substring match is only a **negative result of this text-search method**, not a logically established or independently verified absence of sesame.

**Practical agency workflow.** A food-safety reviewer can prioritize 523 candidate records for label investigation, separately request or verify the 68 incomplete declarations, and avoid automatically labeling the 19,409 nonmatching declarations as safe. This is a screening workflow, not a regulatory determination.


## 7. Neo4j property-graph implementation

Neo4j 5 Community ran in Docker with browser port `7475` and Bolt port `7688`. `session_02/neo4j_comparison.py` imported the same processed CSV records in batches of 1,000, using stable IDs, uniqueness constraints, and `MERGE` to avoid duplicating records on reruns.

| Neo4j label or relationship | Verified count |
|---|---:|
| `Food` nodes | 20,000 |
| `BrandedFood` label | 20,000 (on the same Food nodes) |
| `Nutrient` nodes | 477 |
| `NutrientMeasurement` nodes | 261,255 |
| `HAS_MEASUREMENT` relationships | 261,255 |

The observed total of distinct nodes represented by these labels is **281,732** (20,000 foods + 477 nutrients + 261,255 measurements). Each measurement was also linked to a nutrient through `OF_NUTRIENT`; the run did not separately print a count of those relationships, so their total is not asserted here as independently verified.

The measurement import took **57.9 seconds**. The script generated `session_02/output/neo4j-comparison.txt`.

A Neo4j Browser graph visualized the path:

```text
(BrandedFood)-[:HAS_MEASUREMENT]->(NutrientMeasurement)
             -[:OF_NUTRIENT]->(Nutrient)
```

For example, product `1002189` (PREMIUM SESAME OIL, RICH & TOASTY) displayed measurements linked to Protein, Total Sugars, Sodium, and other nutrients. A numeric `0.0` is a recorded amount, **not a missing value**; interpretation requires the nutrient's `unit_name` and the source's measurement basis.

## 8. Query execution-time comparison

Observed timings are in milliseconds. These are individual runs from the user's environment, **not a controlled or statistically replicated benchmark**.

| Query | Fuseki / SPARQL | Oxigraph / SPARQL | Neo4j / Cypher |
|---|---:|---:|---:|
| Q1 | 4,658.7 | 115.5 | 210.9 |
| Q2 | 2,394.9 | 109.9 | 184.4 |
| Q3 | 2,438.0 | 115.7 | 116.6 |
| Q4 | 2,107.1 | 1.4 | 132.0 |
| Q5 | 2,286.5 | 81.1 | 65.6 |
| Q6 | 2,214.4 | 104.1 | 27.7 |
| Q7 | 2,281.9 | 117.9 | 100.5 |

**Interpretation:** Oxigraph and Neo4j were generally faster than Fuseki in these recorded runs. This does not establish a universal ranking: the engines have different deployment architectures, caching, query planning, and workload characteristics. Q7 is not a directly equivalent timing comparison: the RDF query **constructs and serializes 520 triples**, whereas the Cypher query **returns a single count**. Query ordering also differs in tie cases.

## 9. RDF versus property graphs: project decision

| Criterion | RDF + SPARQL | Neo4j + Cypher |
|---|---|---|
| Representation | Standard subject–predicate–object statements | Nodes, relationships, and properties |
| Ontology and semantics | Native RDF/RDFS/OWL ecosystem | Application-defined labels and relationship semantics |
| Provenance | Named graphs retain source-table context | Provenance requires explicit modeling |
| Queries | SPARQL supports graph patterns, aggregation, optional data, graph construction | Cypher offers intuitive property-graph traversals and aggregations |
| Visualization | Can be visualized using RDF tooling | Convenient interactive Neo4j Browser graph |

**Decision:** Use **RDF/SPARQL as the primary model** for the final food-safety project because the research problem emphasizes semantic distinctions, missing information, source provenance, and future ontology-based reasoning. Retain **Neo4j as a comparison implementation**, demonstrating that the same underlying records can be modeled and queried as a property graph.

## 10. Limitations and safeguards

1. **Text match is not confirmed ingredient identity.** A case-insensitive substring search for `sesame` returns candidates for investigation. It does not prove contamination, quantify risk, or replace label review.
2. **Missing declaration is unknown, not negative.** The 68 records with no usable ingredient declaration must not be counted as sesame-free.
3. **Category and brand data can be incomplete.** Three of 523 sesame candidates lacked category information, so a category-focused result is smaller than the candidate total.
4. **Nutrition is not an ingredient inventory.** Nutrient measurement nodes support additional graph traversals but do not establish sesame presence or absence.
5. **Subset and provenance constraints.** The 20,000 branded foods are a processed subset; the results cannot be generalized to all USDA products without further sampling and validation.
6. **Performance claims are limited.** Timings are single-run observations; a formal comparison would use repeated runs, equivalent query outputs, warm/cold cache controls, and documented resource usage.
7. **Identity and namespace governance.** Stable source IDs are used; `example.org` is a placeholder namespace and should be replaced before publication.

## 11. RDFS entailment and validation demonstration

The optional instructor-style demonstration was adapted in `session_02/rdfs_entailment_demo.py` and executed successfully after installing `owlrl` (version **7.6.2**). It loaded the Turtle graph and selected type/schema statements for RDFS reasoning rather than reasoning over every statement in the 1.2-million-triple graph.

| Experiment | Before reasoning | After reasoning | Outcome |
|---|---|---|---|
| `BrandedFood rdfs:subClassOf Food` | A selected branded product was not explicitly typed `Food` in the demo graph | `Food` type inferred | **True** |
| Deliberately misused `hasNutrientMeasurement` with `rdfs:domain Food` | Nutrient `1003` not typed `Food` | Nutrient incorrectly inferred to be `Food` | **True** |

The experiment took **121.48 seconds** in the recorded run and raised no validation error. The second result illustrates the distinction between **RDFS entailment** (adding consequences of declarations) and **integrity checking** (rejecting or reporting unwanted data patterns). The demonstration deliberately adds a domain declaration and an erroneous example statement to a temporary in-memory graph; it does **not** change the saved Turtle file or the Fuseki dataset. SHACL is a possible technology for explicit data-shape validation in a later session.

## 12. Lab walkthrough verification

The optional `session_02/lab_walkthrough.py` was also created and executed successfully. This project-specific walkthrough **reads existing results**, rather than repeating the expensive RDF conversion, Fuseki upload, or Neo4j import. Its stages verified:

- **RDF serializations:** Turtle present (**77.25 MiB** reported by the script) and TriG present (**83.59 MiB**).
- **Named graphs:** five source-specific graphs, totaling **1,200,721 triples**.
- **SPARQL timings:** seven previously recorded queries for each of Fuseki and Oxigraph, presented in a table and chart.
- **Neo4j comparison:** seven previously recorded Cypher query results read from `output/neo4j-comparison.txt`.

The script printed **`Session 2 walkthrough completed.`** with no reported error. This is confirmation that the generated files and reports are accessible and consistent with the earlier runs; it is **not** a new independent query benchmark.

## 13. Deliverables and reproducibility

| Artifact | Role |
|---|---|
| `session_02/food_iri.py` | Project-specific IRI naming |
| `session_02/convert_to_rdf.py` | CSV-to-RDF converter |
| `session_02/named_graphs.py` | Named graph verification |
| `session_02/load_fuseki.py` | Load Turtle into the `foodkr` Fuseki dataset |
| `session_02/queries.sparql` | Seven SPARQL questions |
| `session_02/run_queries.py` | Query execution and timing in Fuseki/Oxigraph |
| `session_02/neo4j_comparison.py` | Neo4j import and Cypher comparison |
| `session_02/rdfs_entailment_demo.py` | RDFS subclass inference and reasoning-versus-validation experiment |
| `session_02/lab_walkthrough.py` | Read and visualize existing Session 2 outputs and timings |
| `session_02/SESSION_02_REPORT.md` | This technical report |
| `session_02/output/` | RDF serializations, named graph report, and query timing reports |
| Project-root `docker-compose.yml` | Local Fuseki and Neo4j services |

Commands used in the project:

```powershell
# From the project root
docker compose up -d fuseki neo4j

# From session_02
python convert_to_rdf.py
python named_graphs.py
python load_fuseki.py
python run_queries.py
python run_queries.py oxigraph
python neo4j_comparison.py

# Optional demonstrations (run after generating the outputs)
python -m pip install owlrl matplotlib pandas
python rdfs_entailment_demo.py
python lab_walkthrough.py
```

The project uses the processed files already present under `data/processed/`. Neo4j import is idempotent for the same source IDs; the loader replaces the Fuseki default graph when rerun. Preserve the recorded outputs and screenshots alongside this report for reproducibility.

## 14. Conclusion and next steps

The Session 2 pipeline successfully transformed four relational-style USDA CSV tables into **1,200,721 RDF triples** across five named graphs, loaded them into Fuseki, and answered food-safety screening questions in both Fuseki and Oxigraph. The same source data was imported into a Neo4j property graph and queried in Cypher, with consistent substantive results.

The optional RDFS demonstration additionally showed that a schema can infer a new type from a mistaken relationship without flagging it as an error; the optional walkthrough verified the saved output files and timings. The core pipeline and both optional demonstrations have therefore been completed. The professor's separate guided Part B query exercises have not been independently verified in this report.

The key knowledge-representation insight is not merely that a graph can be queried: **a correct model must preserve identity, distinguish source facts from inferred interpretations, and represent incomplete information without turning uncertainty into false certainty**.

**Next: Session 3 — Ontology.** Formalize the meanings of branded foods, ingredient declarations, flagged-ingredient candidates, nutrients, and uncertainty; then explore appropriate RDFS/OWL entailment and validation boundaries. Do not treat ontology inference as automatic proof of ingredient presence.

---

**Evidence basis:** User-recorded console outputs from the RDF converter, named graph checker, Fuseki loader, Fuseki/Oxigraph SPARQL runners, Neo4j import and Cypher runner, the successful RDFS entailment run, the completed lab walkthrough, plus screenshots of both database interfaces. No unprovided source-code execution or independent dataset audit is claimed.
