"""Session 06: fast preliminary food -> category link prediction.

Run from the Food_Knowledge_Representation project root:
    python session_06/link_prediction.py

Ten epochs / one seed are for a smoke test, not a final benchmark.
"""

import collections
import os
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
os.environ.setdefault("PYSTOW_HOME", str(HERE / "data" / "pystow"))

from pykeen.models import TransE
from pykeen.triples import TriplesFactory
from pykeen.training import SLCWATrainingLoop
from learning_utils import mrr, hits_at_k

SEEDS = range(3)
EPOCHS = 150
BATCH_SIZE = 512
EMBEDDING_DIM = 32


def extract_triples(bundle):
    data = bundle["data"]
    food = [f"food::{s}" for s in bundle["food_iri"]]
    brand = [f"brand::{s}" for s in bundle["brand_names"]]
    category = [f"category::{s}" for s in bundle["category_names"]]
    nutrient = [f"nutrient::{s}" for s in bundle["nutrient_iri"]]

    targets = [
        (food[f], "in_category", category[c])
        for f, c in data["food", "in_category", "category"].edge_index.T.tolist()
    ]
    other = set()
    other.update(
        (food[f], "owned_by", brand[b])
        for f, b in data["food", "owned_by", "brand"].edge_index.T.tolist()
    )
    other.update(
        (food[f], "has_nutrient", nutrient[n])
        for f, n in data["food", "has_nutrient", "nutrient"].edge_index.T.tolist()
    )
    return targets, sorted(other)


def make_factory(triples, training=None):
    array = np.asarray(triples, dtype=str).reshape(-1, 3)
    if training is None:
        return TriplesFactory.from_labeled_triples(array)
    return TriplesFactory.from_labeled_triples(
        array,
        entity_to_id=training.entity_to_id,
        relation_to_id=training.relation_to_id,
    )


def rank_categories(scores, candidate_categories, true_category, excluded):
    """Return the 1-based filtered rank; stable category-name tie-break."""
    allowed = np.array(
        [c == true_category or c not in excluded for c in candidate_categories],
        dtype=bool,
    )
    actual_index = candidate_categories.index(true_category)
    actual_score = scores[actual_index]
    # Lexicographic tie-breaking matches alphabetical category order.
    better = (scores > actual_score) | (
        (scores == actual_score) & (np.arange(len(scores)) < actual_index)
    )
    return 1 + int(np.count_nonzero(better & allowed))


def evaluate(model, training, test, train_targets, all_targets, categories):
    entity_to_id = training.entity_to_id
    rel_id = training.relation_to_id["in_category"]
    device = next(model.parameters()).device
    category_ids = torch.tensor([entity_to_id[c] for c in categories], dtype=torch.long, device=device)

    # Only filter other *training-known* true edges. Validation/test labels
    # are not used as training facts; this is a conservative filtered metric.
    known_train = collections.defaultdict(set)
    for h, _, t in train_targets:
        known_train[h].add(t)

    popularity = collections.Counter(t for _, _, t in train_targets)
    popularity_scores = np.array([popularity.get(c, 0) for c in categories], dtype=float)

    model_ranks = []
    popularity_ranks = []
    model.eval()
    with torch.no_grad():
        for idx, (h, _, true_t) in enumerate(test, 1):
            query = torch.tensor([[entity_to_id[h], rel_id]], dtype=torch.long, device=device)
            all_scores = model.score_t(query).squeeze(0)
            scores = all_scores[category_ids].detach().cpu().numpy()
            excluded = known_train[h]
            model_ranks.append(rank_categories(scores, categories, true_t, excluded))
            popularity_ranks.append(rank_categories(popularity_scores, categories, true_t, excluded))
            if idx % 500 == 0:
                print(f"  Ranked {idx:,}/{len(test):,} held-out links", flush=True)
    return model_ranks, popularity_ranks


def main():
    torch.set_num_threads(2)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Training device: {device}", flush=True)
    print("Loading graph...", flush=True)
    bundle = torch.load(HERE / "data" / "food-graph.pt", map_location="cpu", weights_only=False)
    targets, other = extract_triples(bundle)
    categories = sorted({t for _, _, t in targets})

    print("=" * 70)
    print("SESSION 06 - FOOD CATEGORY LINK PREDICTION (GPU FINAL RUN)")
    print("=" * 70)
    print(f"{len(targets):,} category links ({len(categories)} categories)")
    print(f"{len(other):,} auxiliary links")
    print(f"Training: {EPOCHS} epochs, {len(SEEDS)} seed(s), batch size {BATCH_SIZE}\n", flush=True)

    for seed in SEEDS:
        rng = np.random.RandomState(seed)
        permutation = rng.permutation(len(targets))
        n = len(targets) // 10
        test = [targets[i] for i in permutation[:n]]
        valid = [targets[i] for i in permutation[n:2 * n]]
        train = [targets[i] for i in permutation[2 * n:]]

        print(f"Seed {seed}: preparing training triples...", flush=True)
        tf = make_factory(train + other)
        entities = tf.entity_to_id
        # Cold-start targets cannot be scored by TransE.
        test_seen = [tr for tr in test if tr[0] in entities and tr[2] in entities]
        cold = len(test) - len(test_seen)
        categories_seen = sorted(c for c in categories if c in entities)
        # The number of candidates must be reported; this is conditional
        # on categories being represented in the training graph.
        test_seen = [tr for tr in test_seen if tr[2] in categories_seen]
        print(f"  Training triples: {tf.num_triples:,}; test links: {len(test_seen):,}; "
              f"cold-start excluded: {cold}; candidate categories: {len(categories_seen)}", flush=True)
        if not test_seen:
            print("  No scorable links; skipping.")
            continue

        torch.manual_seed(seed)
        np.random.seed(seed)
        model = TransE(triples_factory=tf, embedding_dim=EMBEDDING_DIM).to(device)
        optimizer = torch.optim.Adam(params=model.get_grad_params(), lr=0.001)
        trainer = SLCWATrainingLoop(model=model, triples_factory=tf, optimizer=optimizer)
        print("  Training TransE...", flush=True)
        trainer.train(triples_factory=tf, num_epochs=EPOCHS, batch_size=BATCH_SIZE, use_tqdm=True)
        print("  Training finished; ranking test links...", flush=True)

        r_model, r_pop = evaluate(model, tf, test_seen, train, targets, categories_seen)
        print(f"Seed {seed}: {len(test_seen):,} hidden links scored ({cold} cold-start excluded)")
        print(f"  TransE      MRR {mrr(r_model):.3f}  Hits@1 {hits_at_k(r_model, 1):.3f}  Hits@10 {hits_at_k(r_model, 10):.3f}")
        print(f"  Popularity  MRR {mrr(r_pop):.3f}  Hits@1 {hits_at_k(r_pop, 1):.3f}  Hits@10 {hits_at_k(r_pop, 10):.3f}")
        print("NOTE: Test-set results; do not tune settings based on these scores.")


if __name__ == "__main__":
    main()
