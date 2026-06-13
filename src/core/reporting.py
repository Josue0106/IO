from __future__ import annotations

from typing import Dict, Tuple

import pandas as pd

from .data_model import Area, CaseData
from .layout_metrics import Rect, compute_metrics, count_relation_satisfaction
from .matrices import build_relation_matrix
from .space_matrix import build_space_matrix


SPACE_MODULE_COL = "module"
SPACE_MIN_AREA_COL = "Área mínima (m²)"
SPACE_PERCENT_COL = "% del recinto"
SPACE_ADJ_COL = "Adyacencias requeridas"
SPACE_INCOMP_COL = "Incompatibilidades"
SPACE_GROWTH_COL = "Área con holgura (m²)"
COMPARISON_SLP_COL = "SLP Heurístico"
COMPARISON_OPT_COL = "Modelo Matemático"
COMPARISON_WINNER_COL = "¿Cuál gana?"


def area_label(area: Area) -> str:
    return f"{area.code} {area.name}"


def build_relation_display_tables(case: CaseData) -> Tuple[pd.DataFrame, pd.DataFrame]:
    rel_df, score_df = build_relation_matrix(case.areas, case.relations, case.relation_weights)
    labels = [area_label(area) for area in case.areas]

    qualitative = rel_df.copy()
    qualitative.index = labels
    qualitative.columns = labels

    numeric = score_df.copy()
    numeric.index = labels
    numeric.columns = labels
    numeric["Puntaje total"] = numeric.sum(axis=1).astype(int)

    return qualitative, numeric


def build_space_display_table(case: CaseData) -> Tuple[pd.DataFrame, int, int]:
    base = build_space_matrix(case.areas, case.growth_percent, case.relations, case.constraints).copy()
    facility_area = int(case.facility.width) * int(case.facility.height)
    total_min_area = int(base["min_area"].sum()) if not base.empty else 0
    slack_area = facility_area - total_min_area

    if not base.empty:
        base["module"] = base.apply(lambda row: f"{row['code']} {row['name']}", axis=1)
        base[SPACE_MIN_AREA_COL] = base["min_area"].astype(int)
        base[SPACE_PERCENT_COL] = base["min_area"].apply(lambda value: round((float(value) / facility_area) * 100.0, 1))
        base[SPACE_ADJ_COL] = base["required_adjacencies"]
        base[SPACE_INCOMP_COL] = base["incompatibilities"]
        base[SPACE_GROWTH_COL] = base["required_area"].astype(int)
        display = base[
            [SPACE_MODULE_COL, SPACE_MIN_AREA_COL, SPACE_PERCENT_COL, SPACE_ADJ_COL, SPACE_INCOMP_COL, SPACE_GROWTH_COL]
        ].copy()
    else:
        display = pd.DataFrame(
            columns=[SPACE_MODULE_COL, SPACE_MIN_AREA_COL, SPACE_PERCENT_COL, SPACE_ADJ_COL, SPACE_INCOMP_COL, SPACE_GROWTH_COL]
        )

    total_row = pd.DataFrame(
        [
            {
                SPACE_MODULE_COL: "Total",
                SPACE_MIN_AREA_COL: total_min_area,
                SPACE_PERCENT_COL: round((float(total_min_area) / facility_area) * 100.0, 1) if facility_area else 0.0,
                SPACE_ADJ_COL: "—",
                SPACE_INCOMP_COL: "—",
                SPACE_GROWTH_COL: int(base["required_area"].sum()) if not base.empty else 0,
            }
        ]
    )

    display = pd.concat([display, total_row], ignore_index=True)
    return display, total_min_area, slack_area


def build_layout_table(case: CaseData, layout: Dict[str, Rect]) -> pd.DataFrame:
    rows = []
    for area in case.areas:
        rect = layout.get(area.code)
        if rect is None:
            continue
        rows.append(
            {
                "Módulo": area_label(area),
                "X centroide (m)": round(rect.x + rect.w / 2.0, 2),
                "Y centroide (m)": round(rect.y + rect.h / 2.0, 2),
                "Área asignada (m²)": int(rect.w * rect.h),
                "Ancho (m)": int(rect.w),
                "Alto (m)": int(rect.h),
            }
        )
    return pd.DataFrame(rows)


def build_method_summary(
    case: CaseData,
    layout: Dict[str, Rect],
    runtime_s: float,
    method_name: str,
    objective_value: float | None = None,
    solver_status: str | None = None,
    hard_violations: int | None = None,
) -> Dict[str, float | str]:
    metrics = compute_metrics(layout, case.flows, case.relations, case.facility.width * case.facility.height)
    relation_counts = count_relation_satisfaction(layout, case.relations)
    summary: Dict[str, float | str] = {
        "method": method_name,
        "objective_value": float(objective_value if objective_value is not None else metrics["flow_distance"]),
        "flow_distance": float(metrics["flow_distance"]),
        "a_satisfied": int(relation_counts["a_satisfied"]),
        "a_total": int(relation_counts["a_total"]),
        "e_satisfied": int(relation_counts["e_satisfied"]),
        "e_total": int(relation_counts["e_total"]),
        "x_violations": int(relation_counts["x_violations"]),
        "x_total": int(relation_counts["x_total"]),
        "area_utilization_pct": round(float(metrics["area_utilization"]) * 100.0, 2),
        "runtime_s": float(runtime_s),
        "solver_status": solver_status or "N/A",
        "interpretability": "Alta" if method_name == "SLP" else "Media",
    }
    if hard_violations is not None:
        summary["hard_violations"] = int(hard_violations)
    return summary


def build_comparison_table(slp_summary: Dict[str, float | str], opt_summary: Dict[str, float | str]) -> pd.DataFrame:
    def pick_winner(lower_is_better: bool, slp_value, opt_value) -> str:
        if slp_value == opt_value:
            return "Empate"
        if lower_is_better:
            return "SLP" if slp_value < opt_value else "Optimización"
        return "SLP" if slp_value > opt_value else "Optimización"

    rows = [
        {
            "Indicador": "Distancia total ponderada (m·pers/día)",
            COMPARISON_SLP_COL: f"{float(slp_summary['flow_distance']):.2f}",
            COMPARISON_OPT_COL: f"{float(opt_summary['objective_value']):.2f}",
            COMPARISON_WINNER_COL: pick_winner(True, float(slp_summary["flow_distance"]), float(opt_summary["objective_value"])),
        },
        {
            "Indicador": f"Relaciones A satisfechas (de {slp_summary['a_total']})",
            COMPARISON_SLP_COL: f"{slp_summary['a_satisfied']}/{slp_summary['a_total']}",
            COMPARISON_OPT_COL: f"{opt_summary['a_satisfied']}/{opt_summary['a_total']}",
            COMPARISON_WINNER_COL: pick_winner(False, int(slp_summary["a_satisfied"]), int(opt_summary["a_satisfied"])),
        },
        {
            "Indicador": f"Relaciones E satisfechas (de {slp_summary['e_total']})",
            COMPARISON_SLP_COL: f"{slp_summary['e_satisfied']}/{slp_summary['e_total']}",
            COMPARISON_OPT_COL: f"{opt_summary['e_satisfied']}/{opt_summary['e_total']}",
            COMPARISON_WINNER_COL: pick_winner(False, int(slp_summary["e_satisfied"]), int(opt_summary["e_satisfied"])),
        },
        {
            "Indicador": f"Relaciones X violadas (de {slp_summary['x_total']})",
            COMPARISON_SLP_COL: f"{slp_summary['x_violations']}/{slp_summary['x_total']}",
            COMPARISON_OPT_COL: f"{opt_summary['x_violations']}/{opt_summary['x_total']}",
            COMPARISON_WINNER_COL: pick_winner(True, int(slp_summary["x_violations"]), int(opt_summary["x_violations"])),
        },
        {
            "Indicador": "Área utilizada (%)",
            COMPARISON_SLP_COL: f"{float(slp_summary['area_utilization_pct']):.2f}",
            COMPARISON_OPT_COL: f"{float(opt_summary['area_utilization_pct']):.2f}",
            COMPARISON_WINNER_COL: pick_winner(False, float(slp_summary["area_utilization_pct"]), float(opt_summary["area_utilization_pct"])),
        },
        {
            "Indicador": "Tiempo de ejecución (seg)",
            COMPARISON_SLP_COL: f"{float(slp_summary['runtime_s']):.4f}",
            COMPARISON_OPT_COL: f"{float(opt_summary['runtime_s']):.4f}",
            COMPARISON_WINNER_COL: pick_winner(True, float(slp_summary["runtime_s"]), float(opt_summary["runtime_s"])),
        },
        {
            "Indicador": "Interpretabilidad",
            COMPARISON_SLP_COL: slp_summary["interpretability"],
            COMPARISON_OPT_COL: opt_summary["interpretability"],
            COMPARISON_WINNER_COL: pick_winner(False, 1 if slp_summary["interpretability"] == "Alta" else 0, 1 if opt_summary["interpretability"] == "Alta" else 0),
        },
    ]

    return pd.DataFrame(rows)