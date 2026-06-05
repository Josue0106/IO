from __future__ import annotations

from typing import Dict, List, Tuple
import pandas as pd

from .data_model import Area, Relation


def build_relation_matrix(
    areas: List[Area],
    relations: List[Relation],
    relation_weights: Dict[str, int],
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    codes = [a.code for a in areas]
    rel_map: Dict[Tuple[str, str], str] = {}

    for rel in relations:
        if rel.a == rel.b:
            continue
        key = (rel.a, rel.b)
        reverse = (rel.b, rel.a)
        existing = rel_map.get(key) or rel_map.get(reverse)
        if existing and existing != rel.rel:
            raise ValueError(f"Contradiction in relations: {rel.a}-{rel.b} has {existing} and {rel.rel}")
        rel_map[key] = rel.rel

    rel_df = pd.DataFrame("U", index=codes, columns=codes)
    score_df = pd.DataFrame(0, index=codes, columns=codes, dtype=int)

    for a in codes:
        rel_df.loc[a, a] = "-"
        score_df.loc[a, a] = 0

    for (a, b), rel in rel_map.items():
        rel_df.loc[a, b] = rel
        rel_df.loc[b, a] = rel
        score = relation_weights.get(rel, 0)
        score_df.loc[a, b] = score
        score_df.loc[b, a] = score

    return rel_df, score_df


def relation_score(areas: List[Area], score_df: pd.DataFrame) -> Dict[str, int]:
    scores: Dict[str, int] = {}
    for area in areas:
        scores[area.code] = int(score_df.loc[area.code].sum())
    return scores
