# 🥗 Food Knowledge Representation & Intelligent Querying

### From Food Data to Knowledge Graphs, Semantic Reasoning, Graph Learning, and AI-Powered Question Answering

**Master 2 – Artificial Intelligence | Lebanese University, Faculty of Sciences**

👩‍💻 Project Team

This project was developed by:

-Siwa Diab

-Ghadeer Kassem

-Maya Issa

Course: Knowledge Representation
Academic Year: 2026–2027

## 📌 Project Overview

This project explores how **Knowledge Representation (KR)** technologies can transform structured food data into an intelligent, interconnected, and queryable knowledge system.

Using a subset of the **USDA FoodData Central** dataset, we developed a pipeline that integrates data profiling, RDF knowledge graphs, SPARQL querying, OWL ontologies, semantic reasoning, SHACL validation, relational-to-RDF mapping, graph machine learning, and large language models (LLMs).

The final system allows users to ask questions in natural language, translates them into SPARQL queries using **Google Gemini**, and retrieves answers from the food knowledge graph.

The project demonstrates how symbolic knowledge representation and modern AI can complement each other to improve data accessibility, interpretability, and reliability.

---

## 🎯 Research Question

> A food safety agency flags a specific ingredient for review. Which branded products declare that ingredient, which food categories are affected, and how many products have incomplete ingredient declarations that prevent a reliable assessment?

We use **sesame** as the primary ingredient in our investigation.

The objective is to identify relevant product declarations, explore affected categories, detect missing information, and support food-data investigations.

**Important:** A text match in an ingredient declaration is not proof of contamination or laboratory-confirmed allergen presence.

---

## 📊 Dataset

**Source:** USDA FoodData Central

We prepared a manageable subset of branded food records and their nutritional information.

| Dataset | Records | Description |
|---|---:|---|
| `food.csv` | 20,000 | General food information |
| `branded_food.csv` | 20,000 | Brands, categories, and ingredient declarations |
| `food_nutrient.csv` | 261,255 | Food-to-nutrient relationships |
| `nutrient.csv` | 477 | Nutrient definitions |

### Initial Data Analysis

Our initial investigation identified:

- **19,932** branded foods with usable ingredient declarations.
- **523** products whose declarations mention sesame.
- **68** products with missing or blank ingredient declarations.
- **76** distinct food-category labels among the sesame-matching products.

These findings demonstrate the importance of distinguishing known declarations from missing information.

---

## 🏗️ Project Architecture

```text
USDA FoodData Central
         |
         v
Session 01 — Data Preparation & Profiling
         |
         v
Session 02 — RDF Knowledge Graph & SPARQL
         |
         v
Session 03 — OWL Ontology & Reasoning
         |
         v
Session 04 — SHACL Validation & Provenance
         |
         v
Session 05 — PostgreSQL, R2RML & Virtual KG
         |
         v
Session 06 — Graph Learning & Link Prediction
         |
         v
Session 07 — Gemini Natural Language to SPARQL
         |
         v
Intelligent Food Knowledge Querying
```

The sessions explore complementary techniques. In particular, graph learning and natural-language querying are separate capabilities built around the project's knowledge graph rather than a single sequential prediction pipeline.

---

## 🔬 Project Development

### Session 01 — Data Preparation, Profiling & Constraints

**Objective:** Understand the source data and identify data-quality issues before constructing the knowledge graph.

**Main tasks:**
- Extract a representative subset of food records.
- Profile columns, missing values, and data distributions.
- Implement six rule-based checks.
- Investigate ingredient declarations, food categories, and data consistency.
- Document constraints and their implications.

**Key files:** `prepare_subset.py`, `profiling.py`, `rule_checks.py`

**Outcome:** A prepared dataset and an initial evidence-based
