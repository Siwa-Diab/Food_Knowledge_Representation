# Session 06 — Learning on the Food Knowledge Graph

**Project:** Food Knowledge Representation  
**Milestone:** Learning on a knowledge graph (node classification and link prediction)  
**Dataset:** FoodData Central-derived Food subset (20,000 branded products)  
**Implementation:** `session_06/`  
**Status:** Experiments completed; reproducibility and evaluation caveats documented below

## 1. Research question and learning objectives

The project's main question is:

> A food safety agency flags a specific ingredient for review. Which branded products declare that ingredient, which food categories are affected, and how many products have incomplete ingredient declarations that prevent a reliable assessment?

**Sesame** is used as the example flagged ingredient. The direct answer comes from checking ingredient-declaration text; Session 06 explores whether graph structure and non-target features can help prioritize products for review, and whether knowledge-graph embeddings can predict food–category links.

Two distinct learning tasks were implemented:

1. **Node classification:** predict whether a branded food's available ingredient declaration **mentions the string “sesame.”** This is a *text-mention proxy label*, not independent evidence that sesame is present, absent, or safe.
2. **Link prediction:** rank candidate food categories for a food product after hiding a portion of known food–category links.

These tasks have different target variables and evaluation metrics. Their scores must not be directly compared with one another.

## 2. Data preparation and graph construction

The learning graph was constructed by `build_graph.py` from the Session 05 materialized RDF file (`session_05/output/food-mapped.nt`). The source graph contained **1,200,683 RDF triples**.

| Graph element | Count |
|---|---:|
| Food nodes | 20,000 |
| Brand-owner nodes | 4,748 |
| Food-category nodes | 222 |
| Nutrient nodes | 81 |
| Food → brand-owner links | 19,828 |
| Food → category links | 19,906 |
| Food → nutrient links | 261,255 |

The heterogeneous graph contains node types for foods, brand owners, categories, and nutrients, plus typed relationships and reverse relationships for graph message passing.

### 2.1 Classification labels and unknown cases

| Label status | Products |
|---|---:|
| Usable ingredient declaration | 19,932 |
| Declaration mentions sesame | 523 |
| Missing or blank declaration | 68 |

The positive rate among products with known declarations is **523 / 19,932 ≈ 2.62%**. The **68 missing declarations are unknown**, not negative examples, and are excluded from supervised classification evaluation. Their absence also prevents a reliable declaration-based assessment for those products.

### 2.2 Input features and leakage control

The food node features used in the graph builder include nutrient-count and nutrient-amount summaries, and indicators for whether brand/category metadata are present. Ingredient-declaration text and the derived sesame-mention label are **excluded from the valid classification input features**.

A deliberately invalid baseline also includes the answer as an input feature to demonstrate **target leakage**. That experiment is a diagnostic only and must not be presented as predictive performance.

**Important caveat:** The aggregate nutrient-amount feature sums measurements that can have different units and meanings. It is a weak, not physically interpretable, feature; future versions should normalize units or use nutrient-specific values. Brand/category relationships are also present in the graph, so the classification GNN is evaluated in a **transductive** graph setting; a brand-grouped label split alone does not establish fully inductive generalization to entirely unseen graph entities.

## 3. Node classification: Logistic Regression baseline

`baseline.py` trains a class-weighted Logistic Regression model and reports average precision (called PR-AUC in the script), ROC-AUC, precision@100, and accuracy. Random and brand-owner-grouped splits are used. Grouped splits prevent the same brand owner from contributing labeled examples to both train and test sets. Multiple split seeds assess variation in the held-out brands.

### 3.1 Observed results

| Experiment | Sesame-positive test foods | PR-AUC / AP | ROC-AUC | Precision@100 | Accuracy |
|---|---:|---:|---:|---:|---:|
| Random split, **label leaked** — invalid | 157 | 1.000 | 1.000 | 1.000 | 1.000 |
| Random split, no target feature | 157 | 0.171 | 0.845 | 0.260 | 0.866 |
| Brand-owner split, seed 0 | 171 | 0.187 | 0.808 | 0.300 | 0.893 |
| Brand-owner split, seed 1 | 132 | 0.092 | 0.799 | 0.130 | 0.873 |
| Brand-owner split, seed 2 | 193 | 0.142 | 0.850 | 0.180 | 0.887 |
| Brand-owner split, seed 3 | 154 | 0.103 | 0.826 | 0.150 | 0.883 |
| Brand-owner split, seed 4 | 163 | 0.158 | 0.850 | 0.260 | 0.889 |

The overall no-skill average-precision reference is approximately **0.026**, reflecting the positive-label prevalence. A model that always predicts “no sesame” would have approximately **97.4% accuracy**, despite identifying no positives. Thus, accuracy alone is unsuitable for this imbalanced task.

The brand-owner split performance varies by seed because the set of held-out owners and their positive examples changes. In the baseline output, **335 of 4,712 brand owners** represented in the labeled split population have at least one sesame-positive product.

## 4. Node classification: GraphSAGE

`gnn.py` trains a heterogeneous GraphSAGE model with graph message passing to predict the same sesame-mention label. Its reported results are compared with the Logistic Regression baseline, using the same task and split types.

### 4.1 Observed results

| Experiment | Sesame-positive test foods | PR-AUC / AP | ROC-AUC | Precision@100 | Accuracy |
|---|---:|---:|---:|---:|---:|
| Random split, training seed 0 | 157 | 0.035 | 0.614 | 0.020 | 0.445 |
| Random split, training seed 1 | 157 | 0.031 | 0.574 | 0.030 | 0.526 |
| Random split, training seed 2 | 157 | 0.032 | 0.589 | 0.030 | 0.444 |
| Brand-owner split, seed 0 | 171 | 0.042 | 0.653 | 0.030 | 0.496 |
| Brand-owner split, seed 1 | 132 | 0.028 | 0.568 | 0.040 | 0.463 |
| Brand-owner split, seed 2 | 193 | 0.037 | 0.584 | 0.050 | 0.340 |
| Brand-owner split, seed 3 | 154 | 0.035 | 0.649 | 0.020 | 0.292 |
| Brand-owner split, seed 4 | 163 | 0.039 | 0.637 | 0.040 | 0.614 |

The reported GNN has **25,345 parameters**. Across the observed experiments, GraphSAGE performed substantially worse than Logistic Regression on average precision and precision@100. Its accuracy also remained low at the fixed decision threshold of 0.5; this should not be conflated with its ranking quality.

**Interpretation:** The available graph features and relationships may be insufficient to infer the sesame text-mention target. More model complexity is not inherently better. Possible improvements would require validation-controlled experiments with better features, architecture choices, and careful analysis of graph connectivity—not use of the test set to tune hyperparameters.

## 5. Food-category link prediction: TransE vs popularity

`link_prediction_colab.py` evaluates **TransE**, a knowledge-graph embedding model, against a simple **category-popularity baseline**. The task hides food–category edges and ranks possible categories for held-out links. The evaluation excludes other known correct categories when ranking a true category (filtered ranking), and reports mean reciprocal rank (MRR), Hits@1, and Hits@10.

The graph supplied to this experiment contained:

- **19,906 food–category links** across **222 categories**.
- **281,083 auxiliary links**.

The quick local test used **10 epochs, one seed, batch size 1,024, CPU**. The extended Colab experiment used **150 epochs per run, three split seeds, GPU**, following the professor's epoch count. The exact Colab script and its configuration should be retained with the repository; its reported random-seed warning is noted below.

### 5.1 Preliminary local CPU run: 10 epochs

| Model | MRR | Hits@1 | Hits@10 |
|---|---:|---:|---:|
| TransE | 0.076 | 0.020 | 0.169 |
| Category popularity | 0.133 | 0.043 | 0.317 |

This was a functionality test rather than the final benchmark.

### 5.2 Extended Google Colab GPU run: 150 epochs, three seeds

| Seed | Held-out links scored | Cold-start links excluded | Model | MRR | Hits@1 | Hits@10 |
|---|---:|---:|---|---:|---:|---:|
| 0 | 1,986 | 4 | TransE | 0.091 | 0.037 | 0.178 |
| 0 | 1,986 | 4 | Popularity | 0.133 | 0.043 | 0.317 |
| 1 | 1,984 | 6 | TransE | 0.076 | 0.026 | 0.161 |
| 1 | 1,984 | 6 | Popularity | 0.136 | 0.046 | 0.312 |
| 2 | 1,985 | 5 | TransE | 0.082 | 0.030 | 0.168 |
| 2 | 1,985 | 5 | Popularity | 0.135 | 0.045 | 0.305 |

**Mean of the three displayed, rounded per-seed scores:**

| Model | Mean MRR | Mean Hits@1 | Mean Hits@10 |
|---|---:|---:|---:|
| TransE | **0.083** | 0.031 | 0.169 |
| Category popularity | **0.135** | 0.045 | 0.311 |

These are unweighted averages across seeds of the three-decimal values displayed by the scripts. Slight differences are possible if computed from unrounded metrics.

### 5.3 Interpretation

The **popularity baseline outperformed TransE on all three metrics in every recorded seed**. More epochs did not eliminate the gap in this experiment. This is a meaningful negative result: an embedding model must outperform a simple baseline before additional complexity can be justified.

The results do **not** establish that TransE is generally ineffective, nor that 150 epochs is optimal. The dataset, relationships, split, negative sampling, model settings, and training randomness all affect performance.

### 5.4 Evaluation and reproducibility limitations

1. **Training randomness:** The Colab output included the warning **“No random seed is specified. This may lead to non-reproducible results.”** The split seed may therefore be controlled while model initialization/training is not fully controlled. Before claiming exact reproducibility, pass an explicit training random seed to the PyKEEN pipeline and rerun a controlled experiment.
2. **Cold-start exclusions:** Four, six, and five held-out links were excluded in Seeds 0, 1, and 2 respectively because the needed entities were absent from training. The reported metrics therefore apply to the scored subset, not every originally hidden link.
3. **Potential edge leakage:** Held-out food–category links must be absent from *all* training relationships and derived features that could reveal the same target. The evaluation should audit auxiliary relations for alternative paths that explicitly encode category membership. The report does not claim this has been independently verified.
4. **Filtered ranking:** The filtering procedure and candidate-category set should be documented precisely. The local quick run reported 217 candidate categories; the full candidate universe can vary depending on training coverage.
5. **Model selection:** The extended experiment used a fixed 150-epoch budget. No validation-based checkpoint selection or systematic hyperparameter search was established. Test-set scores must not be used to tune and then report an unbiased final estimate.
6. **Output provenance:** `seed_0_results.txt` contains a captured run log from a separate Seed 0 rerun. The Seed 1 and Seed 2 text files contain transcribed final metrics from Colab output, not full execution logs. The `.ipynb` notebook and `transe_results.csv` should also be retained.

## 6. Part B — Learning utilities

The Food adaptation of the professor's Part B consists of:

- **Y1 — `split_by_brand`:** assigns all products belonging to the same brand owner to one side of a train/test split.
- **Y2 — `recall_at_k`:** number of true positives among the top *k* scores divided by all true positives.
- **Y3 — `hits_at_k`:** proportion of correct links whose ranks are at most *k* (including rank *k* itself).

The adapted checker is `check_my_learning.py`, and the implementations are in `my_learning.py`. The user reported completing the exercise; retain the actual checker output (`3 of 3 right`) as evidence when available. This checker is a **Food-specific adaptation** of the professor's Brunel checker; it is not the original checker run unchanged.

## 7. Relationship to the original food-safety question

The direct, evidence-based output of the food-safety workflow remains:

- Identify **523** products whose usable declarations mention sesame.
- Identify their affected categories using the graph's category information; the exact number of distinct affected categories has **not been established in the Session 06 outputs cited here** and should be computed with a query rather than guessed.
- Report **68** products with missing or blank declarations as **unknown**, requiring additional review.

The learned node-classification scores may help prioritize manual review, but they must not replace inspection of actual declarations. Likewise, predicting a category edge does not establish a product's ingredients or safety.

## 8. Conclusions

1. A heterogeneous graph was built successfully from the food RDF data, representing foods, brand owners, categories, and nutrients.
2. Sesame-mention classification is highly imbalanced; **average precision and precision@100** are more informative than accuracy alone.
3. The deliberately leaked-label baseline achieved perfect metrics, illustrating why the target must be excluded from legitimate features.
4. On the observed data and settings, **Logistic Regression outperformed GraphSAGE** for sesame-mention prediction.
5. Across three 150-epoch GPU runs, **category popularity outperformed TransE** for food–category link prediction.
6. Brand-owner grouping, cold-start handling, transductive graph assumptions, feature leakage, training randomness, and validation-based model selection must be considered before interpreting these scores as generalization performance.
7. The practical food-safety conclusion remains grounded in the declarations: **523 sesame mentions and 68 unknown declarations** in the selected 20,000-product subset.

## 9. Reproduction and artifacts

Run from the Food Knowledge Representation project root with the Session 06 environment activated:

```powershell
python session_06/build_graph.py
python session_06/baseline.py
python session_06/gnn.py
python session_06/check_my_learning.py
```

For link prediction, the local quick-test script is `session_06/link_prediction.py`. The extended **150-epoch GPU experiment** was executed in Google Colab using `session_06/link_prediction_colab.py` and the prepared `session_06/data/food-graph.pt`. Results are recorded in:

```text
session_06/output/transe_results.csv
session_06/output/seed_0_results.txt
session_06/output/seed_1_results.txt
session_06/output/seed_2_results.txt
```

**Submission note:** The large `.pt` graph may be excluded from Git depending on repository size limits; if so, document how to regenerate it. Preserve the Colab notebook, script version, and package versions for future reproducibility.
