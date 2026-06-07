from __future__ import annotations

from typing import Dict, List, Tuple
import math
import pandas as pd

from .data_model import Area, Relation, SpecialConstraints


def build_space_matrix(
    areas: List[Area],
    growth_percent: float,
    relations: List[Relation],
    constraints: SpecialConstraints,
) -> pd.DataFrame:
    # Basic validations
    codes = [a.code for a in areas]
    if len(set(codes)) != len(codes):
        raise ValueError("Area codes must be unique when building space matrix.")

    rows = []
    for area in areas:
        if area.min_area < 1:
            raise ValueError(f"Area '{area.code}' has non-positive min_area.")
        required_area = int(math.ceil(area.min_area * (1.0 + growth_percent)))
        rows.append(
            {
                "code": area.code,
                "name": area.name,
                "min_area": int(area.min_area),
                "growth_percent": float(growth_percent),
                "required_area": required_area,
            }
        )

    df = pd.DataFrame(rows)
    # Ensure consistent column ordering
    cols = ["code", "name", "min_area", "growth_percent", "required_area"]
    return df[cols] if not df.empty else pd.DataFrame(columns=cols)


def build_constraint_table(constraints: SpecialConstraints) -> pd.DataFrame:
    rows = []
    for a, b in constraints.must_adjacent:
        rows.append({"type": "must_adjacent", "a": a, "b": b})
    for a, b in constraints.must_separate:
        rows.append({"type": "must_separate", "a": a, "b": b})
    df = pd.DataFrame(rows)
    cols = ["type", "a", "b"]
    return df[cols] if not df.empty else pd.DataFrame(columns=cols)
