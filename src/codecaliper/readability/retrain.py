"""Retraining scaffold (ARCHITECTURE.md §7.4): feature extraction is decoupled from any
trained model; codecaliper ships NO weights. Model artifacts are JSON (never
pickle) and carry honesty metadata: applying a Java-snippet model elsewhere is
a construct-validity decision the user makes with eyes open.

The heavy lifting (logistic regression) needs the [retrain] extra
(scikit-learn); this module only defines the artifact contract, so the §8.3
faithfulness pipeline and user retraining share one format.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from codecaliper.errors import SpecError
from codecaliper.readability.bw2010 import BW_FEATURE_ORDER_SHA
from codecaliper.spec import spec_version


@dataclass(frozen=True, slots=True)
class ModelArtifact:
    feature_set: str  # "bw2010"
    feature_order_sha: str  # must equal BW_FEATURE_ORDER_SHA at predict time
    spec_version: str
    trained_granularity: str
    trained_language: str
    dataset_id: str  # e.g. "bw2010-original-100java"; an ID, never bundled data
    protocol: str  # e.g. "bw2010-logistic-10fold"
    seed: int
    coefficients: tuple[float, ...]
    intercept: float

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2, sort_keys=True)
            f.write("\n")

    @classmethod
    def load(cls, path: str) -> ModelArtifact:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        data["coefficients"] = tuple(data["coefficients"])
        art = cls(**data)
        if art.feature_set == "bw2010" and art.feature_order_sha != BW_FEATURE_ORDER_SHA:
            raise SpecError(
                "model artifact feature order does not match this codecaliper's "
                "canonical bw2010 order; refusing to predict with misaligned features"
            )
        return art


def new_artifact_metadata(
    *, trained_granularity: str, trained_language: str, dataset_id: str,
    protocol: str, seed: int,
) -> dict[str, object]:
    """Metadata stamp for a fresh training run (used by validation/bw_faithfulness)."""
    return {
        "feature_set": "bw2010",
        "feature_order_sha": BW_FEATURE_ORDER_SHA,
        "spec_version": spec_version(),
        "trained_granularity": trained_granularity,
        "trained_language": trained_language,
        "dataset_id": dataset_id,
        "protocol": protocol,
        "seed": seed,
    }
