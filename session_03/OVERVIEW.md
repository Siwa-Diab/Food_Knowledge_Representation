# Read First — What This Food Ontology Lab Is Doing

## The central question

How can an ontology represent food ingredient declarations, infer which products require sesame review, and detect logical modeling mistakes?

This lab follows a food ontology from its definitions, through consistency checking and inference, to validation using HermiT and ROBOT.

## The short story

In the earlier sessions, the Food Knowledge Representation project explored USDA FoodData Central records and represented selected information using RDF.

Session 3 adds **OWL ontology semantics**.

RDF expresses facts and relationships. OWL adds formal definitions that allow a reasoner to derive consequences and detect contradictions.

For example, suppose a branded product declares an ingredient identified as sesame.

Instead of manually assigning the product the class `SesameDeclarationCandidate`, we define that class logically and allow HermiT to infer membership.

```text
Branded food product
        |
        | hasDeclaredIngredient
        v
Sesame ingredient
        |
        v
OWL EquivalentTo definition
        |
        v
SesameDeclarationCandidate
```

This is an inference from the ontology and asserted declaration facts, not proof that sesame is physically present in the product.

## The research problem

A food safety agency flags sesame for review.

The project aims to answer:

1. Which branded products have declarations suggesting sesame?
2. Which food categories are affected?
3. How many products have missing or incomplete ingredient declarations?
4. Which products cannot be assessed reliably from the available information?

These questions are documented in `competency_questions.md`.

The Session 3 ontology demonstrates the logical foundation for answering them. Full dataset integration and aggregation remain separate tasks.

## The food examples

The sample ontology contains three branded food products and two ingredient individuals.

| Individual | Intended demonstration |
|---|---|
| `product_sesame_1` | A product classified as a sesame declaration candidate |
| `product_sesame_2` | A product whose candidate classification is inferred |
| `product_other_1` | A branded product without an inferred sesame candidate classification |
| `Sesame` | An individual typed as `SesameIngredient` |
| `Sugar` | An individual typed as `Ingredient` |

These individuals are constructed teaching examples.

They are not asserted to correspond to specific real USDA products.

## The two central reasoning ideas

### 1. A reasoner can detect contradictory modeling

The ontology defines object properties with domains and ranges.

For example:

```text
hasDeclaredIngredient

Domain: BrandedFood
Range: Ingredient
```

In OWL, using this property allows the reasoner to infer that its subject is a `BrandedFood` and its object is an `Ingredient`.

This is different from a database constraint that rejects an invalid relationship.

In the deliberately incorrect `domain-mistake.ttl`, a declaration individual is used in a relationship whose domain requires it to be a branded food.

The example also declares the relevant classes disjoint.

Consequently, the individual is forced into incompatible classes, making the ontology inconsistent.

The corrected file avoids that contradiction.

### 2. A defined class can produce new classifications

The clean ontology defines:

```text
SesameDeclarationCandidate
    EquivalentTo:
        BrandedFood
        and hasDeclaredIngredient some SesameIngredient
```

This means:

A product is a sesame declaration candidate exactly when it satisfies the specified class conditions.

If we replace `EquivalentTo` with `SubClassOf`, the definition becomes one-way.

It tells us what a sesame declaration candidate must be, but it does not necessarily classify an untyped product as one.

The `realize_sample.py` experiment demonstrates this distinction.

## Why open-world reasoning matters

OWL uses the open-world assumption.

If a product has no recorded sesame ingredient assertion, that does not prove sesame is absent.

Similarly, a missing ingredient declaration does not prove the product contains no ingredients.

The project therefore distinguishes three important situations:

| Situation | Interpretation |
|---|---|
| Sesame declaration candidate | Available declaration evidence suggests sesame |
| Usable declaration, no sesame text match | Sesame was not identified by the matching procedure |
| Missing or unusable declaration | Assessment is unknown or unreliable |

These categories should not be collapsed into a simple sesame-versus-no-sesame binary.

## The actual dataset

The project uses a processed subset of USDA FoodData Central branded foods.

Earlier data profiling found:

| Measure | Count |
|---|---:|
| Branded food records | 20,000 |
| Sesame-text candidates | 523 |
| Usable ingredient declarations | 19,932 |
| Missing or unusable declarations | 68 |
| Usable declarations without a sesame text match | 19,409 |

These numbers come from dataset profiling.

They are not inferred by the small Session 3 sample ontology.

## What each lab step proves

| Step | File or tool | Main lesson |
|---|---|---|
| 1 | `fetch_ontologies.py` | Ontology imports should be portable and reproducible |
| 2 | Clean ontology + HermiT | Ontology definitions can be checked for consistency |
| 3 | Sample foods + HermiT | Logical definitions can infer new class memberships |
| 4 | Domain mistake + HermiT | Incorrect property use can create contradictions |
| 5 | `realize_sample.py` | EquivalentTo and SubClassOf have different inference behavior |
| 6 | `my_axioms.ttl` | Disjointness, hasValue, some, and only have precise meanings |
| 7 | `closed_world_demo.py` | Database constraints and OWL reasoning have different semantics |
| 8 | `robot_report.py` | Automated checks support ontology quality assurance |

## ELK and HermiT

The professor's original supply-chain lab compares ELK and HermiT on an ontology containing deliberately unsatisfiable classes.

In that example, HermiT detects an additional problem involving a cardinality restriction outside OWL EL.

Our food project has successfully used:

- **HermiT** for consistency checking and class inference.
- **ROBOT with ELK** for reasoning and ontology quality reporting.

We have not reproduced the professor's specific two-unsatisfiable-class comparison using a food ontology.

Therefore, that comparison remains a conceptual lesson from the original course, not a verified result of our food files.

## What the ontology can and cannot establish

The ontology can:

- Represent food and ingredient classes.
- Define object properties and their semantics.
- Infer sesame declaration candidate memberships.
- Detect certain logical contradictions.
- Support consistency and satisfiability checks.

The ontology alone cannot:

- Verify physical ingredient composition.
- Guarantee the completeness of a declaration.
- Treat an absent assertion as a negative fact.
- Produce reliable full-dataset counts without loading the relevant records and executing suitable queries.
- Guarantee that the underlying data is factually correct.

## Important terminology

| Term | Meaning |
|---|---|
| Ontology | A formal representation of classes, properties, and their meanings |
| Class | A category of entities, such as `BrandedFood` |
| Individual | A particular entity, such as `product_sesame_1` |
| Object property | A relationship between individuals |
| Domain | A class inferred for subjects of a property |
| Range | A class inferred for objects of a property |
| Disjointness | A statement that two classes cannot share members |
| Restriction | A condition defined using a property |
| EquivalentTo | A two-way logical class definition |
| SubClassOf | A one-way subclass relationship |
| some | Requires at least one relationship to an instance of the specified class |
| only | Restricts all values of a property to a specified class, without requiring any to exist |
| Reasoner | Software that derives logical consequences from ontology axioms |
| Inconsistency | A contradiction that prevents the ontology from having a model |
| Unsatisfiable class | A class that cannot have any members under the ontology's axioms |
| Open-world assumption | Missing facts are not automatically considered false |

## Source facts, modeling choices, and reasoning results

It is important to distinguish four kinds of information.

**1. Source data**

USDA FoodData Central provides branded product records and associated information.

**2. Project modeling choices**

The project introduces classes such as `SesameDeclarationCandidate` and properties such as `hasDeclaredIngredient`.

**3. Teaching examples**

The three sample products and the domain-mistake example are constructed to demonstrate OWL reasoning.

**4. Reasoner conclusions**

HermiT infers candidate memberships or detects contradictions based on the supplied axioms and assertions.

A reasoner conclusion is logically justified relative to those inputs, but it does not independently verify the truth of the underlying data.

## Conclusion

Session 3 demonstrates that an ontology is more than a collection of RDF labels.

Its formal definitions allow software to infer classifications, identify logical contradictions, and check whether a model behaves as intended.

The next project stages can build on this foundation by integrating real product records, food categories, ingredient-declaration completeness, and SPARQL queries.

Return to [README.md](README.md) for the commands and exercises.