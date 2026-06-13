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

    relation_lookup: Dict[Tuple[str, str], str] = {}
    for rel in relations:
        if rel.a == rel.b:
            continue
        relation_lookup[(rel.a, rel.b)] = rel.rel
        relation_lookup[(rel.b, rel.a)] = rel.rel

    rows = []
    for area in areas:
        if area.min_area < 1:
            raise ValueError(f"Area '{area.code}' has non-positive min_area.")
        required_area = int(math.ceil(area.min_area * (1.0 + growth_percent)))
        required_adjacencies = []
        incompatibilities = []
        for other in areas:
            if other.code == area.code:
                continue
            rel = relation_lookup.get((area.code, other.code))
            if rel in {"A", "E"}:
                required_adjacencies.append(other.code)
            elif rel == "X":
                incompatibilities.append(other.code)
        rows.append(
            {
                "code": area.code,
                "name": area.name,
                "min_area": int(area.min_area),
                "growth_percent": float(growth_percent),
                "required_area": required_area,
                "required_adjacencies": ", ".join(required_adjacencies) if required_adjacencies else "—",
                "incompatibilities": ", ".join(incompatibilities) if incompatibilities else "—",
            }
        )

    df = pd.DataFrame(rows)
    # Ensure consistent column ordering
    cols = [
        "code",
        "name",
        "min_area",
        "growth_percent",
        "required_area",
        "required_adjacencies",
        "incompatibilities",
    ]
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
