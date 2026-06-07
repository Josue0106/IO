from __future__ import annotations

from typing import List, Tuple, Dict

import pandas as pd


def build_comparison_df(metrics_data: List[Tuple[str, Dict[str, float]]]) -> pd.DataFrame:
    """Build a comparison DataFrame from metrics_data.

    metrics_data: list of (label, metrics_dict)
    Returns a DataFrame with rows per method and delta columns relative to the first method when possible.
    """
    rows = []
    for label, metrics in metrics_data:
        row = {"metodo": label}
        row.update(metrics)
        rows.append(row)

    df = pd.DataFrame(rows)

    if df.shape[0] >= 2:
        base = df.iloc[0]
        for col in df.columns:
            if col == "metodo":
                continue
            try:
                df[f"delta_{col}"] = df[col] - base[col]
            except Exception:
                df[f"delta_{col}"] = None

    return df
