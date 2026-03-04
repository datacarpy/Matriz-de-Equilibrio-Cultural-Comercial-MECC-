import json
from datetime import datetime
from typing import Dict, Any, List

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from mecc_core import (
    MECCInput,
    evaluate,
    DEFAULT_DIMENSIONS,
    DEFAULT_THRESHOLDS,
    DEFAULT_RED_FLAGS,
)

st.set_page_config(page_title="MECC Evaluator Pro", page_icon="🧭", layout="wide")


# -------------------------
# Helpers
# -------------------------

def _now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _init_state():
    if "saved_evals" not in st.session_state:
        st.session_state.saved_evals = []  # list of payloads


def radar_chart(labels: List[str], values: List[float], title: str = ""):
    """
    Radar chart simple con matplotlib (sin estilos raros).
    values esperado en escala 0..5
    """
    import numpy as np

    N = len(labels)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    values2 = values + values[:1]
    angles2 = angles + angles[:1]

    fig = plt.figure()
    ax = plt.subplot(111, polar=True)
    ax.plot(angles2, values2, linewidth=2)
    ax.fill(angles2, values2, alpha=0.15)
    ax.set_thetagrids([a * 180 / np.pi for a in angles], labels)
    ax.set_ylim(0, 5)
    ax.set_title(title)
    return fig


def payload_to_markdown(payload: Dict[str, Any]) -> str:
    i = payload["input"]
    r = payload["result"]

    rows = r["per_dimension"]
    table = "\n".join([f"| {d['name']} | {d['score']} | {d['weight']:.2f} | {d['weighted']:.2f} |" for d in rows])

    red_flags = r["red_flags_triggered"]
    gates = r["gates_failed"]
    recs = r["recommendations"]
    clauses = r["clauses"]
    naming = r["naming_advice"]

    return f"""# MECC — Reporte de Evaluación (Pro)

- **Fecha:** {payload.get("meta", {}).get("created_at", "")}
- **Proyecto:** {i["project_name"]}
- **Evento:** {i["event_name"]}
- **Sponsor:** {i["sponsor_name"]}

## Resultado
- **MECC ponderado:** {r["weighted_score"]:.2f} / 5
- **MECC simple:** {r["unweighted_score"]:.2f} / 5
- **Riesgo de mercantilización (0–100):** {r["commercialization_risk_0_100"]:.1f}
- **Clasificación:** {r["label"]}

## Gates (condiciones mínimas)
{("- " + "\\n- ".join(gates)) if gates else "- Ninguno"}

## Red flags
{("- " + "\\n- ".join(red_flags)) if red_flags else "- Ninguno"}

## Matriz (detalle por dimensión)
| Dimensión | Puntaje | Peso | Ponderado |
|---|---:|---:|---:|
{table}

## Recomendaciones
{("- " + "\\n- ".join(recs)) if recs else "- (sin recomendaciones)"}

## Cláusulas sugeridas
{("\\n".join(clauses)) if clauses else "- (sin cláusulas sugeridas)"}

## Naming sugerido
{("- " + "\\n- ".join(naming)) if naming else "- (sin sugerencias)"}

## Notas globales
{i.get("global_notes") or "_(sin notas)_"}
"""


def build_payload(mecc_in: MECCInput, res) -> Dict[str, Any]:
    return {
        "meta": {
            "created_at": _now_stamp(),
            "version": "MECC Pro v1",
        },
        "input": {
            "project_name": mecc_in.project_name,
            "event_name": mecc_in.event_name,
            "sponsor_name": mecc_in.sponsor_name,
            "scores": mecc_in.scores,
            "notes_by_dimension": mecc_in.notes_by_dimension,
            "global_notes": mecc_in.global_notes,
        },
        "result": {
            "weighted_score": float(res.weighted_score),
            "unweighted_score": float(res.unweighted_score),
            "commercialization_risk_0_100": float(res.commercialization_risk_0_100),
            "label": res.label,
            "gates_failed": res.gates_failed,
            "red_flags_triggered": res.red_flags_triggered,
            "per_dimension": res.per_dimension,
            "recommendations": res.recommendations,
            "clauses": res.clauses,
            "naming_advice": res.naming_advice,
        },
    }


# -------------------------
# UI
# -------------------------

_init_state()

st.title("🧭 MECC Evaluator Pro")
st.caption("Evaluación minuciosa y genérica para patrocinios: identidad vs comercialización, con matriz, radar y comparador.")

with st.sidebar:
    st.header("Contexto")
    project_name = st.text_input("Nombre del proyecto", value="Proyecto")
    event_name = st.text_input("Nombre del evento", value="Evento")
    sponsor_name = st.text_input("Sponsor a evaluar", value="Marca X")
    global_notes = st.text_area("Notas globales (opcional)", height=120, placeholder="Supuestos, contexto, acuerdos, riesgos, etc.")

    st.divider()
    st.header("Ajustes (avanzado)")
    show_weights = st.checkbox("Mostrar/editar pesos", value=False)
    show_gates = st.checkbox("Mostrar gates (mínimos)", value=True)
    show_notes = st.checkbox("Notas por dimensión", value=True)

    st.divider()
    st.header("Comparador")
    st.caption("Guarda evaluaciones para comparar sponsors entre sí.")
    if st.button("🧹 Limpiar historial guardado"):
        st.session_state.saved_evals = []
        st.success("Historial limpio.")

# Inputs: sliders + notas por dimensión
st.subheader("1) Matriz de evaluación (1–5)")
st.caption("1=muy negativo · 2=riesgoso · 3=aceptable · 4=bueno · 5=ideal")

scores: Dict[str, int] = {}
notes_by_dimension: Dict[str, str] = {}
weights_override: Dict[str, float] = {}

# Render en dos columnas para que se vea pro
cols = st.columns(2)
for idx, d in enumerate(DEFAULT_DIMENSIONS):
    c = cols[idx % 2]
    with c:
        st.markdown(f"### {d['name']}")
        st.caption(d["question"])
        scores[d["key"]] = st.slider(
            label=f"Puntaje — {d['name']}",
            min_value=1,
            max_value=5,
            value=3,
            step=1,
            key=f"score_{d['key']}",
        )

        if show_weights:
            weights_override[d["key"]] = st.number_input(
                label=f"Peso — {d['name']}",
                min_value=0.1,
                max_value=3.0,
                value=float(d["weight"]),
                step=0.1,
                key=f"w_{d['key']}",
            )
        else:
            weights_override[d["key"]] = float(d["weight"])

        if show_gates:
            st.caption(f"Gate mínimo recomendado: **{d.get('min_gate', 1)}**")

        if show_notes:
            notes_by_dimension[d["key"]] = st.text_area(
                label=f"Notas — {d['name']}",
                height=80,
                placeholder=d.get("notes_hint", ""),
                key=f"note_{d['key']}",
            )
        else:
            notes_by_dimension[d["key"]] = ""

# Construir dimensiones con pesos ajustados si el usuario los editó
dimensions = []
for d in DEFAULT_DIMENSIONS:
    dd = dict(d)
    dd["weight"] = float(weights_override[d["key"]])
    dimensions.append(dd)

mecc_in = MECCInput(
    project_name=project_name.strip() or "Proyecto",
    event_name=event_name.strip() or "Evento",
    sponsor_name=sponsor_name.strip() or "Marca X",
    scores=scores,
    notes_by_dimension=notes_by_dimension,
    global_notes=global_notes.strip(),
    thresholds=DEFAULT_THRESHOLDS,
    red_flags=DEFAULT_RED_FLAGS,
    dimensions=dimensions,
)

res = evaluate(mecc_in)
payload = build_payload(mecc_in, res)

st.divider()
st.subheader("2) Resultado ejecutivo")

c1, c2, c3, c4 = st.columns(4)
c1.metric("MECC ponderado", f"{res.weighted_score:.2f} / 5")
c2.metric("MECC simple", f"{res.unweighted_score:.2f} / 5")
c3.metric("Riesgo mercantilización", f"{res.commercialization_risk_0_100:.1f} / 100")
c4.write("**Clasificación**")
c4.write(res.label)

if res.gates_failed:
    st.error("Gates fallidos (condiciones mínimas):")
    for g in res.gates_failed:
        st.write(f"- ⚠️ `{g}`")
else:
    st.success("Sin gates fallidos.")

if res.red_flags_triggered:
    st.error("Red flags activos (alertas críticas):")
    for rf in res.red_flags_triggered:
        st.write(f"- 🚩 `{rf}`")
else:
    st.info("Sin red flags críticos.")

st.divider()
st.subheader("3) Visual (Radar) + Matriz")

left, right = st.columns([1, 1])

with left:
    labels = [d["name"] for d in res.per_dimension]
    values = [float(d["score"]) for d in res.per_dimension]
    fig = radar_chart(labels, values, title="Perfil de riesgo (1–5 por dimensión)")
    st.pyplot(fig, clear_figure=True)

with right:
    df = pd.DataFrame(
        [
            {
                "Dimensión": d["name"],
                "Puntaje (1–5)": d["score"],
                "Peso": round(float(d["weight"]), 2),
                "Puntaje ponderado": round(float(d["weighted"]), 2),
                "Gate mín.": d.get("min_gate", ""),
                "Notas": mecc_in.notes_by_dimension.get(d["key"], ""),
            }
            for d in res.per_dimension
        ]
    )
    st.dataframe(df, use_container_width=True)

st.divider()
st.subheader("4) Salvaguardas recomendadas")

tab1, tab2, tab3 = st.tabs(["Recomendaciones", "Cláusulas sugeridas", "Naming sugerido"])

with tab1:
    if res.recommendations:
        for r in res.recommendations:
            st.write(f"- {r}")
    else:
        st.write("- Mantener lineamientos actuales; documentar límites de marca y control curatorial.")

with tab2:
    if res.clauses:
        st.caption("Plantillas base: adaptalas con tu abogado/contrato.")
        for c in res.clauses:
            st.write(c)
    else:
        st.write("- (sin cláusulas sugeridas)")

with tab3:
    for n in res.naming_advice:
        st.write(f"- {n}")

st.divider()
st.subheader("5) Comparador de sponsors (guardá y compará)")

save_col, exp_col = st.columns([1, 1])

with save_col:
    if st.button("💾 Guardar esta evaluación en el historial"):
        st.session_state.saved_evals.append(payload)
        st.success("Guardado.")

with exp_col:
    st.download_button(
        "⬇️ Descargar evaluación (JSON)",
        data=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name="mecc_evaluation_pro.json",
        mime="application/json",
    )
    report_md = payload_to_markdown(payload)
    st.download_button(
        "⬇️ Descargar reporte (Markdown)",
        data=report_md.encode("utf-8"),
        file_name="mecc_report_pro.md",
        mime="text/markdown",
    )

if st.session_state.saved_evals:
    st.markdown("### Historial guardado")
    # Tabla comparativa rápida
    rows = []
    for p in st.session_state.saved_evals:
        r = p["result"]
        i = p["input"]
        rows.append(
            {
                "Fecha": p["meta"]["created_at"],
                "Proyecto": i["project_name"],
                "Evento": i["event_name"],
                "Sponsor": i["sponsor_name"],
                "MECC": round(r["weighted_score"], 2),
                "Riesgo(0-100)": round(r["commercialization_risk_0_100"], 1),
                "Clasificación": r["label"],
                "Red flags": len(r["red_flags_triggered"]),
                "Gates fallidos": len(r["gates_failed"]),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

    # Comparación por dimensión (promedio por sponsor seleccionado)
    st.markdown("### Comparar perfiles (por dimensión)")
    sponsors = [p["input"]["sponsor_name"] for p in st.session_state.saved_evals]
    selected = st.multiselect("Seleccioná sponsors para comparar", options=sponsors, default=sponsors[-2:] if len(sponsors) >= 2 else sponsors)
    if selected:
        # construir dataframe wide
        dims = [d["name"] for d in DEFAULT_DIMENSIONS]
        data = {"Dimensión": dims}
        # map key->name
        key_to_name = {d["key"]: d["name"] for d in DEFAULT_DIMENSIONS}

        for sp in selected:
            # tomar la última evaluación de ese sponsor (si hay varias)
            last = None
            for p in reversed(st.session_state.saved_evals):
                if p["input"]["sponsor_name"] == sp:
                    last = p
                    break
            if last:
                per = last["result"]["per_dimension"]
                name_to_score = {d["name"]: d["score"] for d in per}
                data[sp] = [name_to_score.get(dim, None) for dim in dims]

        st.dataframe(pd.DataFrame(data), use_container_width=True)
else:
    st.info("Todavía no guardaste evaluaciones. Guardá 2 o más para comparar sponsors.")
