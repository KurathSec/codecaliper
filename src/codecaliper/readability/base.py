"""FeatureSet registry — bw2010 now; scalabrino2018/dorn2012 slot in at 1.x
without model changes (FileReport.readability is already plural)."""

from __future__ import annotations

#: name -> native granularity; extraction dispatch lives in api.py for the MVP.
FEATURE_SETS: dict[str, str] = {"bw2010": "snippet"}


def available_feature_sets() -> tuple[str, ...]:
    return tuple(FEATURE_SETS)
