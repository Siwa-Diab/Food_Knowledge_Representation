# Competency Questions — Food Knowledge Representation (Session 3)

## Purpose

This document defines the competency questions that guide the design and evaluation of the Food Knowledge Representation ontology.

**Research question:**

A food safety agency flags sesame for review. Which branded products declare that ingredient, which food categories are affected, and how many products have incomplete ingredient declarations that prevent a reliable assessment?

A competency question describes information the knowledge representation system should be able to retrieve or infer.

The questions below distinguish between capabilities already represented in the Session 3 ontology and capabilities requiring additional modeling or dataset queries.

## Eight competency questions

| # | Competency question | Relevant ontology class or concept | Current status |
|---|---|---|---|
| 1 | Which branded food products have ingredient declarations that identify sesame? | `food:SesameDeclarationCandidate` | Modeled and demonstrated with sample individuals |
| 2 | Which branded products have incomplete ingredient declarations? | `food:ProductWithIncompleteDeclaration` | Modeled in `my_axioms.ttl`; not yet applied to the full dataset |
| 3 | Which food ingredients are explicitly declared by a branded product? | `food:Ingredient`, `food:hasDeclaredIngredient` | Represented in the sample ontology |
| 4 | Which products belong to food categories affected by a sesame review? | Proposed `food:FoodCategory` | Requires category modeling and product-category relationships |
| 5 | How many branded products are sesame declaration candidates? | `food:SesameDeclarationCandidate` | Can be counted using the processed dataset; OWL alone does not calculate aggregate counts |
| 6 | How many products have missing or unusable ingredient declarations? | `food:ProductWithIncompleteDeclaration` and declaration status | Requires applying the data-quality rules to the processed dataset |
| 7 | Which products cannot be reliably assessed for sesame because their ingredient declarations are incomplete? | `food:ProductWithIncompleteDeclaration` | Concept modeled; product-level population still required |
| 8 | Which products have usable ingredient declarations but no sesame text match? | Declaration status and ingredient matching results | Requires explicit data-quality and matching information; absence of an OWL assertion is not sufficient |

## Current dataset observations

The project's processed USDA FoodData Central subset contains 20,000 branded food records.

Earlier profiling identified:

- **523** sesame-text candidate products.
- **19,932** products with usable ingredient declarations.
- **68** products with missing or unusable ingredient declarations.
- **19,409** products with usable declarations but no sesame text match.

These are dataset-profiling results, not counts produced by the Session 3 OWL reasoner.

A sesame text match identifies a candidate for review, not laboratory-confirmed sesame presence. A product without a text match is not necessarily sesame-free.

## Classes and properties already implemented

| Ontology entity | Purpose |
|---|---|
| `food:Food` | General food concept |
| `food:BrandedFood` | Represents branded food products |
| `food:Ingredient` | Represents ingredient concepts |
| `food:SesameIngredient` | Identifies the sesame ingredient concept |
| `food:SesameDeclarationCandidate` | Classifies products with a declared ingredient typed as sesame |
| `food:hasDeclaredIngredient` | Connects branded products to declared ingredients |
| `food:ProductWithIncompleteDeclaration` | Classifies products explicitly marked with incomplete declaration status in the axiom exercise |

The final entity is currently defined in `my_axioms.ttl`, not necessarily in the main reference ontology.

## Competency-question coverage

The current Session 3 ontology demonstrates reasoning for CQ1 and the basic ingredient relationships needed for CQ3.

The `my_axioms.ttl` exercise provides a logical definition relevant to CQ2 and CQ7.

The remaining questions require additional