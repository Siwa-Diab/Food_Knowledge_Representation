
"""Session 06: GraphSAGE for Food Knowledge Representation.

Predict whether a branded food's ingredient declaration mentions sesame.

Run:
    python session_06/gnn.py

Uses the same random and brand-owner splits as baseline.py.
"""

from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    roc_auc_score,
)

from torch_geometric.nn import HeteroConv, SAGEConv

from learning_utils import (
    precision_at_k,
    split_random,
    split_by_brand_owner,
)

HERE = Path(__file__).resolve().parent

EPOCHS = 100
HIDDEN = 32
LR = 0.01

torch.set_num_threads(2)


class FoodGraphSAGE(torch.nn.Module):

    def __init__(self, metadata):

        super().__init__()

        node_types, edge_types = metadata

        self.input_layers = torch.nn.ModuleDict({
            node_type: torch.nn.LazyLinear(HIDDEN)
            for node_type in node_types
        })

        self.conv1 = HeteroConv({
            edge_type: SAGEConv(
                (HIDDEN, HIDDEN), HIDDEN
            )
            for edge_type in edge_types
        }, aggr="sum")

        self.conv2 = HeteroConv({
            edge_type: SAGEConv(
                (HIDDEN, HIDDEN), HIDDEN
            )
            for edge_type in edge_types
        }, aggr="sum")

        self.score = torch.nn.Linear(HIDDEN, 1)

    def forward(self, x_dict, edge_index_dict):

        h = {
            node_type: F.relu(
                self.input_layers[node_type](x)
            )
            for node_type, x in x_dict.items()
        }

        h = self.conv1(
            h,
            edge_index_dict
        )

        h = {
            key: F.relu(value)
            for key, value in h.items()
        }

        h = self.conv2(
            h,
            edge_index_dict
        )

        return self.score(
            h["food"]
        ).squeeze(-1)


def run(data, y, train, test, seed=0):

    if len(train) == 0 or len(test) == 0:
        return None

    if len(np.unique(y[train])) < 2:
        return None

    torch.manual_seed(seed)

    model = FoodGraphSAGE(
        data.metadata()
    )

    # Initialize lazy linear layers.
    with torch.no_grad():
        model(
            data.x_dict,
            data.edge_index_dict
        )

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=LR
    )

    target = torch.tensor(
        y,
        dtype=torch.float32
    )

    train_positive_share = float(
        y[train].mean()
    )

    positive_weight = torch.tensor(
        (1.0 - train_positive_share)
        / train_positive_share
    )

    for epoch in range(EPOCHS):

        model.train()

        optimizer.zero_grad()

        logits = model(
            data.x_dict,
            data.edge_index_dict
        )

        loss = F.binary_cross_entropy_with_logits(
            logits[train],
            target[train],
            pos_weight=positive_weight
        )

        loss.backward()
        optimizer.step()

    model.eval()

    with torch.no_grad():

        probabilities = torch.sigmoid(
            model(
                data.x_dict,
                data.edge_index_dict
            )
        ).numpy()[test]

    actual = y[test]

    positives = int(actual.sum())

    return {
        "positive in test": positives,
        "test size": len(test),
        "PR-AUC": (
            average_precision_score(actual, probabilities)
            if positives else float("nan")
        ),
        "ROC-AUC": (
            roc_auc_score(actual, probabilities)
            if 0 < positives < len(test)
            else float("nan")
        ),
        "precision@100": precision_at_k(
            actual,
            probabilities,
            100
        ),
        "accuracy": accuracy_score(
            actual,
            probabilities > 0.5
        ),
        "parameters": sum(
            p.numel()
            for p in model.parameters()
        ),
    }


def display(name, result):

    if result is None:
        return f"{name}: skipped (insufficient data)"

    return (
        f"{name:<36} "
        f"positive in test {result['positive in test']:>4} "
        f"PR-AUC {result['PR-AUC']:.3f} "
        f"ROC-AUC {result['ROC-AUC']:.3f} "
        f"precision@100 {result['precision@100']:.3f} "
        f"accuracy {result['accuracy']:.3f}"
    )


def main():

    bundle = torch.load(
        HERE / "data" / "food-graph.pt",
        weights_only=False
    )

    data = bundle["data"]

    y = data["food"].y.numpy()

    brand_group = bundle["brand_group"].numpy()

    print("=" * 75)
    print("SESSION 06 - FOOD GRAPH NEURAL NETWORK")
    print("=" * 75)

    print(f"\nFood nodes: {len(y):,}")
    print(f"Known labels: {int((y >= 0).sum()):,}")
    print(f"Positive labels: {int((y == 1).sum()):,}\n")

    # Random split: 3 training seeds
    train, test = split_random(
        len(y),
        y,
        seed=0
    )

    for seed in range(3):

        result = run(
            data,
            y,
            train,
            test,
            seed=seed
        )

        print(
            display(
                f"Random split, training seed {seed}",
                result
            )
        )

        if seed == 0 and result is not None:
            print(
                f"Model parameters: "
                f"{result['parameters']:,}"
            )

    print()

    # Brand-owner split: 5 seeds
    for seed in range(5):

        train, test = split_by_brand_owner(
            brand_group,
            y,
            seed=seed
        )

        result = run(
            data,
            y,
            train,
            test,
            seed=seed
        )

        print(
            display(
                f"Brand-owner split, seed {seed}",
                result
            )
        )


if __name__ == "__main__":
    main()
