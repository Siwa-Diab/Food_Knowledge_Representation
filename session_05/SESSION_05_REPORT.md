# Session 05 — Relational Integration, Virtualization and Entity Resolution

## Objective

The objective of Session 05 was to integrate the USDA FoodData Central dataset with relational and semantic technologies. The implementation demonstrates relational data loading, R2RML-based RDF generation, virtual SPARQL querying, SHACL validation, and entity resolution.

## Relational Data Integration

Four CSV datasets were loaded into PostgreSQL:

- `food`: 20,000 records
- `branded_food`: 20,000 records
- `food_nutrient`: 261,255 records
- `nutrient`: 477 records

Total: 301,732 records.

## RDF Materialization

Morph-KGC was used to materialize RDF triples from the PostgreSQL tables using R2RML mappings.

The resulting graph contained 1,200,683 triples.

Comparison with the Session 02 graph showed 1,200,682 shared triples. Most differences resulted from ontology/schema triples included in Session 02 but not produced by the Session 05 mapping. One ingredient declaration differed in trailing whitespace.

## SHACL Validation

The mapped RDF graph was validated using the shapes developed in Session 04.

Results:

- 68 violations: missing ingredient declarations
- 266 warnings: missing brand-owner or category information

The quality gate failed because the source dataset contains incomplete ingredient declarations. These records remain unknown with respect to the flagged ingredient and must not be classified as ingredient-free.

## Ontop Virtualization

Ontop was configured to query the PostgreSQL database through a virtual RDF graph.

SPARQL queries were executed to identify products declaring sesame, summarize affected categories, identify sesame candidates with missing categories, and retrieve product details.

The query for sesame returned 523 candidate products.

## Entity Resolution

A synthetic external brand-owner dataset was generated using controlled variations of 46 USDA brand-owner names, together with six unmatched records.

The matching algorithm applied name normalization, blocking, Jaro–Winkler similarity, and manually specified Fellegi–Sunter-style likelihood weights.

Blocking reduced the number of candidate comparisons from 2,392 to 712.

At threshold 4, precision and recall were both 100%.

At threshold 8, precision remained 100%, while recall decreased to 93.5% because three genuine matches were missed.

These results demonstrate the effect of matching thresholds on record-linkage performance. Since the external dataset was synthetically generated, the results should not be interpreted as real-world entity-resolution accuracy.

## Conclusion

Session 05 demonstrated how relational food data can be represented and queried through semantic technologies without losing awareness of source-data limitations.

Materialization produces a stored RDF graph, while virtualization translates SPARQL queries into relational database operations.

Entity resolution provides a complementary mechanism for identifying potentially equivalent organizations across heterogeneous systems.

Together, these techniques support the food safety investigation by improving data integration, traceability, and the identification of records requiring further review.