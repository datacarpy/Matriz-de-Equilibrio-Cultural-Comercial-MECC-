import json
import streamlit as st
from mecc_core import MECCInput, evaluate, DEFAULT_DIMENSIONS

st.set_page_config(page_title="MECC Evaluator", page_icon="🧭", layout="centered")

st.title("🧭 MECC Evaluator")
st.caption("Matriz genérica para evaluar riesgo de sobre-comercialización vs identidad cultural.")

with st.sidebar:
    st.header("Proyecto / Evento")
    project_name = st.text_input("Nombre del proyecto", value="Proyecto Cultural")
    event_name = st.text_input("Nombre del evento", value="Evento")
    sponsor_name = st.text_input("Sponsor a evaluar", value="Marca X")
    st.divider()
    st.header("Opciones")
    show_weights = st.checkbox("Mostrar pesos (avanzado)", value=False)
    st.caption("Los pesos vienen por defecto. Si necesitás personalizarlos, te conviene editar `mecc_core.py`.")

st.subheader("1) Puntajes (1 a 5)")
st.caption("1=muy negativo · 2=riesgoso · 3=aceptable · 4=bueno · 5=ideal")

scores = {}
for d in DEFAULT_DIMENSIONS:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(f"**{d['name']}**")
        st.caption(d["question"])
        if show_weights:
            st.caption(f"Peso: {d['weight']}")
    with col2:
        scores[d["key"]] = st.slider(
            label=d["name"],
            min_value=1,
            max_value=5,
            value=3,
            key=f"score_{d['key']}",
            label_visibility="collapsed",
        )

notes = st.text_area("2) Notas / supuestos (opcional)", placeholder="Ej: el sponsor no define programación; branding limitado a piezas digitales...")

mecc_in = MECCInput(
    project_name=project_name.strip() or "Proyecto Cultural",
    event_name=event_name.strip() or "Evento",
    sponsor_name=sponsor_name.strip() or "Marca X",
    scores=scores,
    notes=notes.strip(),
)

res = evaluate(mecc_in)

st.divider()
st.subheader("Resultado")

st.metric("MECC ponderado (0–5)", f"{res.weighted_score:.2f}")
st.write(f"**Clasificación:** {res.label}")
st.caption(f"MECC simple (promedio): {res.unweighted_score:.2f} / 5")

if res.red_flags_triggered:
    st.error("Red flags activados (revisar antes de firmar):")
    for rf in res.red_flags_triggered:
        st.write(f"- ⚠️ `{rf}`")
else:
    st.success("Sin red flags críticos.")

st.subheader("Detalle por dimensión")
st.table([
    {"Dimensión": d["name"], "Puntaje": d["score"], "Peso": d["weight"], "Puntaje ponderado": round(d["weighted"], 2)}
    for d in res.per_dimension
])

st.subheader("Recomendaciones (salvaguardas)")
if res.recommendations:
    for r in res.recommendations:
        st.write(f"- {r}")
else:
    st.write("- Mantener lineamientos actuales; documentar límites de marca y control curatorial.")

st.subheader("Naming sugerido (sin perder identidad)")
for opt in res.naming_advice:
    st.write(f"- {opt}")

st.divider()
st.subheader("Exportar")

payload = {
    "input": {
        "project_name": mecc_in.project_name,
        "event_name": mecc_in.event_name,
        "sponsor_name": mecc_in.sponsor_name,
        "scores": mecc_in.scores,
        "notes": mecc_in.notes,
    },
    "result": {
        "weighted_score": res.weighted_score,
        "unweighted_score": res.unweighted_score,
        "label": res.label,
        "red_flags_triggered": res.red_flags_triggered,
        "per_dimension": res.per_dimension,
        "recommendations": res.recommendations,
        "naming_advice": res.naming_advice,
    }
}
st.download_button(
    "⬇️ Descargar evaluación (JSON)",
    data=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
    file_name="mecc_evaluation.json",
    mime="application/json",
)

report_md = f"""# MECC — Reporte de Evaluación

- **Proyecto:** {mecc_in.project_name}
- **Evento:** {mecc_in.event_name}
- **Sponsor:** {mecc_in.sponsor_name}

## Resultado
- **MECC ponderado:** {res.weighted_score:.2f} / 5
- **MECC simple:** {res.unweighted_score:.2f} / 5
- **Clasificación:** {res.label}

## Red flags
{("- " + "\\n- ".join(res.red_flags_triggered)) if res.red_flags_triggered else "- Ninguno"}

## Detalle por dimensión
| Dimensión | Puntaje | Peso | Ponderado |
|---|---:|---:|---:|
{"".join([f"| {d['name']} | {d['score']} | {d['weight']:.2f} | {d['weighted']:.2f} |\\n" for d in res.per_dimension])}

## Recomendaciones
{("- " + "\\n- ".join(res.recommendations)) if res.recommendations else "- (sin recomendaciones)"}

## Naming sugerido
- {"\\n- ".join(res.naming_advice)}

## Notas
{mecc_in.notes or "_(sin notas)_"}
"""
st.download_button(
    "⬇️ Descargar reporte (Markdown)",
    data=report_md.encode("utf-8"),
    file_name="mecc_report.md",
    mime="text/markdown",
)
