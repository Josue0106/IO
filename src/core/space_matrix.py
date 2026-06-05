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
    rows = []
    for area in areas:
        required_area = int(math.ceil(area.min_area * (1.0 + growth_percent)))
        rows.append(
            {
                "code": area.code,
                "name": area.name,
                "min_area": area.min_area,
                "growth_percent": growth_percent,
                "required_area": required_area,
            }
        )

    return pd.DataFrame(rows)


def build_constraint_table(constraints: SpecialConstraints) -> pd.DataFrame:
    rows = []
    for a, b in constraints.must_adjacent:
        rows.append({"type": "must_adjacent", "a": a, "b": b})
    for a, b in constraints.must_separate:
        rows.append({"type": "must_separate", "a": a, "b": b})
    return pd.DataFrame(rows)
