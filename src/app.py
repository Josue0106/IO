from __future__ import annotations

import json
from typing import Dict

import pandas as pd
import streamlit as st
from pandas.io.formats.style import Styler

from core.data_model import case_from_dict, case_to_dict, load_case
from core.validation import validate_case
from core.reporting import (
    build_comparison_table,
    build_layout_table,
    build_method_summary,
    build_relation_display_tables,
    build_space_display_table,
)
from core.matrices import build_relation_matrix
from core.space_matrix import build_constraint_table
from slp.heuristic import slp_layout
from optimization.ortools_model import solve_layout as ortools_solve
from optimization.pulp_model import solve_layout as pulp_solve
from visualization.plotting import plot_layout, plot_relation_graph


METRIC_COL = "Métrica"
VALUE_COL = "Valor"
CSV_MIME = "text/csv"
CELL_PADDING = "0.35rem 0.5rem"
NEUTRAL_BG = "background-color: rgba(120, 120, 120, 0.08)"


st.set_page_config(page_title="Layout SLP vs Opt", layout="wide")

st.title("Diseño de layout: SLP y optimización")

st.sidebar.header("Datos")
use_sample = st.sidebar.checkbox("Usar datos de ejemplo", value=True)

case_data = None
raw_payload = None

uploaded = None

if use_sample:
    case_data = load_case("data/sample_case.json")
else:
    uploaded = st.sidebar.file_uploader("Cargar JSON", type=["json"])
    if uploaded:
        raw_payload = json.load(uploaded)
        case_data = case_from_dict(raw_payload)

if case_data is None:
    st.info("Cargue un archivo JSON o use el ejemplo para continuar.")
    st.stop()

payload = case_to_dict(case_data)

facility_area = int(case_data.facility.width) * int(case_data.facility.height)
minimum_area = sum(int(area.min_area) for area in case_data.areas)
slack_area = facility_area - minimum_area

st.sidebar.subheader("Configuracion")
payload["facility"]["width"] = int(st.sidebar.number_input("Ancho", min_value=1, value=payload["facility"]["width"]))
payload["facility"]["height"] = int(st.sidebar.number_input("Alto", min_value=1, value=payload["facility"]["height"]))
payload["growth_percent"] = float(
    st.sidebar.number_input("Holgura (0.0 = sin crecimiento)", min_value=0.0, max_value=1.0, value=payload.get("growth_percent", 0.0))
)
enforce_relations = st.sidebar.checkbox("Aplicar A/E/X como restricciones duras", value=True)

st.sidebar.subheader("Areas")
areas_df = pd.DataFrame(payload["areas"])
areas_df = st.sidebar.data_editor(areas_df, num_rows="dynamic", use_container_width=True, key="areas_editor")

st.sidebar.subheader("Relaciones")
relations_df = pd.DataFrame(payload["relations"])
relations_df = st.sidebar.data_editor(relations_df, num_rows="dynamic", use_container_width=True, key="relations_editor")

st.sidebar.subheader("Flujos")
flows_df = pd.DataFrame(payload["flows"])
flows_df = st.sidebar.data_editor(flows_df, num_rows="dynamic", use_container_width=True, key="flows_editor")

st.sidebar.subheader("Restricciones especiales")
adj_df = pd.DataFrame(payload.get("special_constraints", {}).get("must_adjacent", []))
sep_df = pd.DataFrame(payload.get("special_constraints", {}).get("must_separate", []))
adj_df = st.sidebar.data_editor(adj_df, num_rows="dynamic", use_container_width=True, key="adj_editor")
sep_df = st.sidebar.data_editor(sep_df, num_rows="dynamic", use_container_width=True, key="sep_editor")

payload["areas"] = areas_df.dropna().to_dict("records")
payload["relations"] = relations_df.dropna().to_dict("records")
payload["flows"] = flows_df.dropna().to_dict("records")
payload["special_constraints"] = {
    "must_adjacent": adj_df.dropna().to_dict("records"),
    "must_separate": sep_df.dropna().to_dict("records"),
}

case_data = case_from_dict(payload)

validation_errors = validate_case(case_data)
if validation_errors:
    for e in validation_errors:
        st.error(e)
    st.stop()

if use_sample:
    st.info(
        (
            f"Caso recomendado activo: recinto {facility_area} m², área mínima funcional {minimum_area} m² y holgura {slack_area} m². "
            f"El ejemplo usa growth_percent={case_data.growth_percent:.1f} para evitar bloques demasiado pequeños, "
            f"con A/X como restricciones duras y E/I/O como preferencias.")
    )

raw_rel_df, raw_score_df = build_relation_matrix(case_data.areas, case_data.relations, case_data.relation_weights)
rel_df, score_df = build_relation_display_tables(case_data)
space_df, total_min_area, circulation_slack = build_space_display_table(case_data)
constraints_df = build_constraint_table(case_data.constraints)

def summary_metrics_df(summary: Dict[str, float | str]) -> pd.DataFrame:
    rows = [
        {METRIC_COL: "Valor de la función objetivo", VALUE_COL: f"{float(summary['objective_value']):.2f}"},
        {METRIC_COL: "Distancia total ponderada", VALUE_COL: f"{float(summary['flow_distance']):.2f}"},
        {METRIC_COL: "Relaciones A satisfechas", VALUE_COL: f"{summary['a_satisfied']}/{summary['a_total']}",},
        {METRIC_COL: "Relaciones E satisfechas", VALUE_COL: f"{summary['e_satisfied']}/{summary['e_total']}",},
        {METRIC_COL: "Relaciones X violadas", VALUE_COL: f"{summary['x_violations']}/{summary['x_total']}",},
        {METRIC_COL: "% de área utilizada", VALUE_COL: f"{float(summary['area_utilization_pct']):.2f}"},
        {METRIC_COL: "Tiempo de ejecución (seg)", VALUE_COL: f"{float(summary['runtime_s']):.4f}"},
        {METRIC_COL: "Estado del solver", VALUE_COL: str(summary["solver_status"])},
    ]
    return pd.DataFrame(rows)


def style_relation_matrix(df: pd.DataFrame, numeric: bool = False) -> Styler:
    if numeric:
        def color_numeric(value):
            try:
                number = float(value)
            except Exception:
                return ""
            if number > 0:
                return "background-color: rgba(46, 125, 50, 0.14)"
            if number < 0:
                return "background-color: rgba(198, 40, 40, 0.16)"
            return NEUTRAL_BG

        return (
            df.style.format(na_rep="—")
            .map(color_numeric)
            .set_properties(**{"text-align": "center"})
            .set_table_styles([
                {"selector": "th", "props": [("text-align", "center"), ("font-weight", "600")]},
                {"selector": "td", "props": [("padding", CELL_PADDING)]},
            ])
        )

    color_map = {
        "A": "background-color: rgba(198, 40, 40, 0.18)",
        "E": "background-color: rgba(239, 108, 0, 0.18)",
        "I": "background-color: rgba(249, 168, 37, 0.18)",
        "O": "background-color: rgba(109, 76, 65, 0.16)",
        "U": "background-color: rgba(158, 158, 158, 0.08)",
        "X": "background-color: rgba(21, 101, 192, 0.14)",
        "-": "background-color: rgba(38, 50, 56, 0.12)",
    }

    def style_symbol(value):
        return color_map.get(value, "")

    return (
        df.style.map(style_symbol)
        .set_properties(**{"text-align": "center"})
        .set_table_styles([
            {"selector": "th", "props": [("text-align", "center"), ("font-weight", "600")]},
                {"selector": "td", "props": [("padding", CELL_PADDING)]},
        ])
    )


def style_space_table(df: pd.DataFrame) -> Styler:
    return (
        df.style.hide(axis="index")
        .set_properties(**{"text-align": "center"})
        .set_table_styles([
            {"selector": "th", "props": [("text-align", "center"), ("font-weight", "600")]},
            {"selector": "td", "props": [("padding", "0.35rem 0.5rem")]},
        ])
    )


def style_comparison_table(df: pd.DataFrame) -> Styler:
    def winner_style(row):
        winner = row["¿Cuál gana?"]
        styles = [""] * len(row)
        if winner == "SLP":
            styles[1] = "background-color: rgba(46, 125, 50, 0.16); font-weight: 700"
        elif winner == "Optimización":
            styles[2] = "background-color: rgba(25, 118, 210, 0.16); font-weight: 700"
        else:
            styles[1] = NEUTRAL_BG
            styles[2] = NEUTRAL_BG
        return styles

    return (
        df.style.apply(winner_style, axis=1)
        .set_properties(**{"text-align": "center"})
        .set_table_styles([
            {"selector": "th", "props": [("text-align", "center"), ("font-weight", "600")]},
            {"selector": "td", "props": [("padding", CELL_PADDING)]},
        ])
    )


st.subheader("1. Matriz relacional")
st.caption("Matriz simétrica 8×8 con formato cualitativo y formato numérico con puntaje total por área.")
rel_col1, rel_col2 = st.columns(2)
with rel_col1:
    st.markdown("**Formato cualitativo**")
    st.dataframe(style_relation_matrix(rel_df), use_container_width=True)
    st.download_button(
        "Descargar matriz relacional cualitativa (CSV)",
        rel_df.to_csv(index=True).encode("utf-8"),
        file_name="matriz_relacional_qualitativa.csv",
        mime=CSV_MIME,
    )
with rel_col2:
    st.markdown("**Formato numérico**")
    st.dataframe(style_relation_matrix(score_df, numeric=True), use_container_width=True)
    st.download_button(
        "Descargar matriz relacional numérica (CSV)",
        score_df.to_csv(index=True).encode("utf-8"),
        file_name="matriz_relacional_numerica.csv",
        mime=CSV_MIME,
    )

st.subheader("2. Matriz de espacios")
st.caption(f"Área total mínima: {total_min_area} m². Holgura disponible para circulación: {circulation_slack} m².")
st.dataframe(style_space_table(space_df), use_container_width=True)
st.download_button(
    "Descargar matriz de espacios (CSV)",
    space_df.to_csv(index=False).encode("utf-8"),
    file_name="matriz_espacios.csv",
    mime=CSV_MIME,
)

st.subheader("Restricciones especiales")
if constraints_df.empty:
    st.caption("Sin restricciones adicionales.")
else:
    st.dataframe(constraints_df, use_container_width=True)

st.subheader("6. Diagrama de relaciones")
relation_fig = plot_relation_graph(case_data.areas, case_data.relations)
st.pyplot(relation_fig)

st.divider()

run_slp = st.button("Ejecutar SLP")
solver_choice = st.sidebar.radio("Solver", options=["ORTOOLS", "PULP"], index=0)
run_opt = st.button("Ejecutar Optimización")

if "slp_result" not in st.session_state:
    st.session_state.slp_result = None
if "opt_result" not in st.session_state:
    st.session_state.opt_result = None

if run_slp:
    print("[streamlit] Running SLP solver...", flush=True)
    st.session_state.slp_result = slp_layout(case_data, raw_score_df)
    print(
        f"[streamlit] SLP finished: status={st.session_state.slp_result.status} "
        f"placed={len(st.session_state.slp_result.layout)}",
        flush=True,
    )

if run_opt:
    print(f"[streamlit] Running optimization solver={solver_choice}...", flush=True)
    if solver_choice == "PULP":
        st.session_state.opt_result = pulp_solve(case_data, time_limit_s=120)
    else:
        st.session_state.opt_result = ortools_solve(case_data, enforce_relations=enforce_relations)
    print(
        f"[streamlit] Optimization finished: status={st.session_state.opt_result.status} "
        f"layout_size={len(st.session_state.opt_result.layout)} objective={st.session_state.opt_result.objective_value}",
        flush=True,
    )

slp_result = st.session_state.slp_result
opt_result = st.session_state.opt_result

metrics_data = []
comparison_ready = False

if slp_result:
    st.subheader("3. Layout generado por SLP")
    st.caption(f"Recinto de {case_data.facility.width} × {case_data.facility.height} m. Las celdas muestran área y dimensiones de cada bloque.")
    fig = plot_layout(slp_result.layout, case_data.facility.width, case_data.facility.height, "SLP")
    st.pyplot(fig)
    layout_df = build_layout_table(case_data, slp_result.layout)
    st.dataframe(layout_df, use_container_width=True)
    st.download_button(
        "Descargar layout SLP (CSV)",
        layout_df.to_csv(index=False).encode("utf-8"),
        file_name="layout_slp.csv",
        mime=CSV_MIME,
    )

    slp_summary = build_method_summary(
        case_data,
        slp_result.layout,
        slp_result.runtime_s,
        "SLP",
        solver_status=slp_result.status,
        hard_violations=slp_result.a_hard_violations,
    )
    metrics_data.append(("SLP", slp_summary))

    st.subheader("4. Métricas del SLP")
    st.dataframe(summary_metrics_df(slp_summary), use_container_width=True)
    if slp_result.status != "feasible":
        st.warning(f"SLP terminó con estado {slp_result.status} y {slp_result.a_hard_violations} violaciones duras A/X.")

if opt_result and opt_result.layout:
    st.subheader("5. Layout generado por optimización")
    st.caption(f"Recinto de {case_data.facility.width} × {case_data.facility.height} m. Se muestran centroides y área asignada por módulo.")
    fig = plot_layout(opt_result.layout, case_data.facility.width, case_data.facility.height, "Optimizacion")
    st.pyplot(fig)
    layout_df = build_layout_table(case_data, opt_result.layout)
    st.dataframe(layout_df, use_container_width=True)
    st.download_button(
        "Descargar layout OPT (CSV)",
        layout_df.to_csv(index=False).encode("utf-8"),
        file_name="layout_opt.csv",
        mime=CSV_MIME,
    )

    opt_summary = build_method_summary(
        case_data,
        opt_result.layout,
        opt_result.runtime_s,
        "OPT",
        objective_value=opt_result.objective_value,
        solver_status=opt_result.status,
    )
    metrics_data.append(("OPT", opt_summary))

    st.subheader("7. Métricas del modelo matemático")
    st.dataframe(summary_metrics_df(opt_summary), use_container_width=True)

if metrics_data:
    comparison_ready = len(metrics_data) == 2

if comparison_ready:
    slp_summary = metrics_data[0][1]
    opt_summary = metrics_data[1][1]
    st.subheader("8. Tabla comparativa final")
    comparison_df = build_comparison_table(slp_summary, opt_summary)
    st.dataframe(style_comparison_table(comparison_df), use_container_width=True)
    st.download_button(
        "Descargar comparacion (CSV)",
        comparison_df.to_csv(index=False).encode("utf-8"),
        file_name="comparacion.csv",
        mime=CSV_MIME,
    )
