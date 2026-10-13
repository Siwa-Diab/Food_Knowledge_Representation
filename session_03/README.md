# Session 3 Lab — Food Ontology Reasoning and Validation

## Why this lab exists

This lab applies OWL ontology concepts to the Food Knowledge Representation project.

It demonstrates:

- OWL classes, object properties, domains, and ranges.
- `SubClassOf` versus `EquivalentTo`.
- Existential (`some`) and universal (`only`) restrictions.
- Disjoint classes and ontology inconsistency.
- Open-world versus closed-world reasoning.
- Automated reasoning with HermiT and ROBOT/ELK.
- Competency questions and ontology quality reporting.
- Reproducible offline ontology imports.

**The central goal:** understand how a reasoner can infer new food-product classifications and detect contradictory ontology statements.

Read [OVERVIEW.md](OVERVIEW.md) before beginning the exercises.

## Before you start

The project environment has already been configured with:

- Python 3.12 and the `.venv312` virtual environment.
- RDFLib and Owlready2.
- Java JDK 21.
- Protégé Desktop with HermiT and ELK.
- ROBOT for ontology reasoning and quality reports.

All commands below are run from the **Food_Knowledge_Representation project root**, not from inside `session_03`.

Activate the virtual environment if necessary.

## Part A — Prepare, reason, and observe

### Step 1: Prepare the local ontologies

```powershell
python session_03/fetch_ontologies.py
```

The script checks the food ontology files, configures `catalog-v001.xml`, updates the sample ontology import, and prepares licensing documentation.

**Verified result:**

- Three required ontology files found.
- Clean ontology parsed with 43 triples.
- Food ontology IRI registered.
- Sample ontology import updated.
- Offline catalog verification passed.

### Step 2: Check the clean ontology

```powershell
python session_03/local_reasoner.py session_03/workspace/food-reasoning-clean.ttl
```

**Verified result:**

```text
Ontology is consistent.
Impossible classes (equivalent to owl:Nothing): none
Individual classifications:
  No food individuals found.
```

This demonstrates that the reference ontology's definitions are logically consistent in the tested configuration.

### Step 3: Observe inferred food classifications

```powershell
python session_03/local_reasoner.py session_03/workspace/sample-foods.ttl
```

**Verified result:**

```text
Ontology is consistent.
Impossible classes (equivalent to owl:Nothing): none

Individual classifications:
  Sesame: Sesame ingredient
  Sugar: Ingredient
  product_other_1: Branded food
  product_sesame_1: Branded food, Sesame declaration candidate
  product_sesame_2: Sesame declaration candidate
```

The reasoner recognizes sesame declaration candidates using the class definition.

`product_sesame_2` is also a branded food because `SesameDeclarationCandidate` is a subclass of `BrandedFood`, even when the direct classification display omits the superclass.

These are teaching examples, not independently verified ingredient-safety findings.

### Step 4: Observe an ontology inconsistency

```powershell
python session_03/local_reasoner.py session_03/workspace/domain-mistake.ttl
```

**Verified result:**

```text
The ontology is INCONSISTENT.
Its axioms and assertions contradict each other.
```

The domain-mistake example uses an object property in a way that conflicts with disjoint class definitions.

This illustrates why the domain and range of a property must be checked before using it.

The corrected version is stored in `workspace/domain-mistake-fixed.ttl`.

### Step 5: Compare EquivalentTo and SubClassOf

```powershell
python session_03/realize_sample.py
```

The script compares two definitions of `SesameDeclarationCandidate`.

**Experiment 1 — EquivalentTo**

The reasoner classifies `product_sesame_1` and `product_sesame_2` as sesame declaration candidates.

**Experiment 2 — SubClassOf**

The reasoner no longer infers those candidate memberships solely from the ingredient assertions.

**Conclusion:** `EquivalentTo` supports classification in both directions; `SubClassOf` expresses only the subclass relationship.

The recorded result is saved to:

`session_03/reference-outputs/realized-sample.txt`

## Part B — Practice OWL axioms

Open:

`session_03/my_axioms.ttl`

The three exercises are:

| Exercise | OWL concept | Food example |
|---|---|---|
| Y1 | Disjointness | A branded food is not an ingredient declaration |
| Y2 | EquivalentTo and hasValue | A branded food explicitly marked with incomplete declaration status |
| Y3 | some and only | A branded food with at least one sesame ingredient assertion and all declared ingredient relationships restricted to sesame |

Run:

```powershell
python session_03/check_my_axioms.py
```

**Verified result:**

```text
Y1: right.
Y2: right.
Y3: right.

3 of 3 right.
```

The checker evaluates the logical behavior of the axioms using HermiT.

**Important:** An `only` restriction does not prove that an ingredient declaration is complete. Under the open-world assumption, additional ingredients may still exist unless stronger information is supplied.

## Part C — Think and discuss

1. Why does `SesameDeclarationCandidate` need an `EquivalentTo` definition to infer membership from ingredient assertions?
2. Why can a property-domain mistake make an ontology inconsistent?
3. Why does the absence of a sesame assertion not prove that a food is sesame-free?
4. Which food classes directly answer competency questions, and which are supporting classes?
5. What additional modeling is required to represent food categories and declaration completeness across the full dataset?
6. What is the difference between an OWL inconsistency and an unsatisfiable class?

See [competency_questions.md](competency_questions.md).

## Optional — Automated validation

### ROBOT quality report

```powershell
python session_03/robot_report.py
```

The verified ROBOT run successfully reasoned over the clean ontology and generated:

- `session_03/reference-outputs/reasoned.ttl`
- `session_03/reference-outputs/report.tsv`

The latest observed report contained:

- 1 ERROR: missing ontology license.
- 0 WARN findings.
- 2 INFO findings: missing explicit superclasses for top-level classes.

The license remains to be selected by the ontology's rights holder.

### Closed-world versus open-world demonstration

```powershell
python session_03/closed_world_demo.py
```

The demonstration shows a SQLite foreign-key constraint rejecting an unknown product identifier, while explaining how OWL's property-domain semantics can infer a type from a relationship assertion.

Recorded output:

`session_03/reference-outputs/closed-world-demo.txt`

## Files and their roles

| File | Purpose |
|---|---|
| `fetch_ontologies.py` | Prepare local ontology imports and catalog |
| `local_reasoner.py` | Run offline HermiT reasoning |
| `check_my_axioms.py` | Validate Y1, Y2, and Y3 |
| `realize_sample.py` | Compare EquivalentTo and SubClassOf |
| `closed_world_demo.py` | Contrast SQLite constraints with OWL semantics |
| `robot_report.py` | Run ROBOT reasoning and quality checks |
| `my_axioms.ttl` | Three OWL axiom exercises |
| `competency_questions.md` | Research questions guiding ontology design |
| `workspace/food-reasoning-clean.ttl` | Clean food ontology |
| `workspace/sample-foods.ttl` | Sample food individuals |
| `workspace/domain-mistake.ttl` | Deliberately inconsistent example |
| `workspace/domain-mistake-fixed.ttl` | Corrected example |
| `workspace/catalog-v001.xml` | Offline ontology import mappings |
| `workspace/LICENCES.md` | Provenance and licensing notes |
| `reference-outputs/` | Recorded reasoning and validation results |

## You understood this lab if you can explain

- Why `EquivalentTo` infers a sesame candidate classification but `SubClassOf` alone does not.
- Why an object property's domain can infer the subject's class.
- Why disjointness can expose an inconsistent assertion.
- Why `some` and `only` express different conditions.
- Why OWL does not assume missing information is false.
- Why a consistent ontology is not automatically a complete or accurate representation of real-world food data.

## Take it to the team project

Use the clean ontology as the foundation for later integration with USDA FoodData Central records.

Extend the model to represent food categories, declaration completeness, and product-level evidence while keeping candidate detection separate from verified ingredient presence.

Before adding new classes or properties, identify the competency question they support, inspect their formal meanings, and run a reasoner after making changes.