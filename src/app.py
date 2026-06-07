from __future__ import annotations

import json
from typing import Dict

import pandas as pd
import streamlit as st

from core.data_model import case_from_dict, case_to_dict, load_case
from core.validation import validate_case
from core.matrices import build_relation_matrix
from core.layout_metrics import Rect, compute_metrics
from core.comparison import build_comparison_df
from core.space_matrix import build_space_matrix, build_constraint_table
from slp.heuristic import slp_layout
from optimization.ortools_model import solve_layout
from visualization.plotting import plot_layout


st.set_page_config(page_title="Layout SLP vs Opt", layout="wide")

st.title("Diseno de layout: SLP y Optimizacion")

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

rel_df, score_df = build_relation_matrix(case_data.areas, case_data.relations, case_data.relation_weights)
space_df = build_space_matrix(case_data.areas, case_data.growth_percent, case_data.relations, case_data.constraints)
constraints_df = build_constraint_table(case_data.constraints)

col_a, col_b = st.columns([1, 1])
with col_a:
    st.subheader("Matriz relacional")
    st.dataframe(rel_df)
    st.download_button(
        "Descargar matriz relacional (CSV)",
        rel_df.to_csv(index=True).encode("utf-8"),
        file_name="matriz_relacional.csv",
        mime="text/csv",
    )

with col_b:
    st.subheader("Matriz de puntajes")
    st.dataframe(score_df)
    st.download_button(
        "Descargar matriz de puntajes (CSV)",
        score_df.to_csv(index=True).encode("utf-8"),
        file_name="matriz_puntajes.csv",
        mime="text/csv",
    )

st.subheader("Matriz de espacios")
st.dataframe(space_df)
st.download_button(
    "Descargar matriz de espacios (CSV)",
    space_df.to_csv(index=False).encode("utf-8"),
    file_name="matriz_espacios.csv",
    mime="text/csv",
)

st.subheader("Restricciones especiales")
if constraints_df.empty:
    st.caption("Sin restricciones adicionales.")
else:
    st.dataframe(constraints_df)

st.divider()

run_slp = st.button("Ejecutar SLP")
run_opt = st.button("Ejecutar Optimizacion")

if "slp_result" not in st.session_state:
    st.session_state.slp_result = None
if "opt_result" not in st.session_state:
    st.session_state.opt_result = None

if run_slp:
    st.session_state.slp_result = slp_layout(case_data, score_df)

if run_opt:
    st.session_state.opt_result = solve_layout(case_data, enforce_relations=enforce_relations)

slp_result = st.session_state.slp_result
opt_result = st.session_state.opt_result

metrics_data = []

if slp_result:
    st.subheader("Layout SLP")
    fig = plot_layout(slp_result.layout, case_data.facility.width, case_data.facility.height, "SLP")
    st.pyplot(fig)

    # Export layout: PNG and CSV
    import io

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    st.download_button("Descargar layout SLP (PNG)", buf.getvalue(), file_name="layout_slp.png", mime="image/png")

    layout_rows = [
        {"code": k, "x": r.x, "y": r.y, "w": r.w, "h": r.h} for k, r in slp_result.layout.items()
    ]
    layout_df = pd.DataFrame(layout_rows)
    st.download_button(
        "Descargar layout SLP (CSV)", layout_df.to_csv(index=False).encode("utf-8"), file_name="layout_slp.csv", mime="text/csv"
    )

    metrics = compute_metrics(
        slp_result.layout,
        case_data.flows,
        case_data.relations,
        case_data.facility.width * case_data.facility.height,
    )
    metrics["runtime_s"] = slp_result.runtime_s
    metrics_data.append(("SLP", metrics))

if opt_result and opt_result.layout:
    st.subheader("Layout Optimizacion")
    fig = plot_layout(opt_result.layout, case_data.facility.width, case_data.facility.height, "Optimizacion")
    st.pyplot(fig)

    # Export layout: PNG and CSV
    import io

    buf2 = io.BytesIO()
    fig.savefig(buf2, format="png", bbox_inches="tight")
    buf2.seek(0)
    st.download_button("Descargar layout OPT (PNG)", buf2.getvalue(), file_name="layout_opt.png", mime="image/png")

    layout_rows = [
        {"code": k, "x": r.x, "y": r.y, "w": r.w, "h": r.h} for k, r in opt_result.layout.items()
    ]
    layout_df = pd.DataFrame(layout_rows)
    st.download_button(
        "Descargar layout OPT (CSV)", layout_df.to_csv(index=False).encode("utf-8"), file_name="layout_opt.csv", mime="text/csv"
    )

    metrics = compute_metrics(
        opt_result.layout,
        case_data.flows,
        case_data.relations,
        case_data.facility.width * case_data.facility.height,
    )
    metrics["runtime_s"] = opt_result.runtime_s
    metrics["solver_status"] = opt_result.status
    metrics_data.append(("OPT", metrics))

if metrics_data:
    st.subheader("Comparacion")
    rows = []
    for label, metrics in metrics_data:
        row = {"metodo": label}
        row.update(metrics)
        rows.append(row)
    comparison_df = pd.DataFrame(rows)
    st.dataframe(comparison_df)
    st.download_button(
        "Descargar comparacion (CSV)",
        comparison_df.to_csv(index=False).encode("utf-8"),
        file_name="comparacion.csv",
        mime="text/csv",
    )

    # Detailed comparison with deltas
    detailed_df = build_comparison_df(metrics_data)
    st.download_button(
        "Descargar comparacion detallada (CSV)",
        detailed_df.to_csv(index=False).encode("utf-8"),
        file_name="comparacion_detallada.csv",
        mime="text/csv",
    )
