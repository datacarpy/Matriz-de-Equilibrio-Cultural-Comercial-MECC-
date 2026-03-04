from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


DEFAULT_DIMENSIONS = [
    {
        "key": "cultural_identity",
        "name": "Identidad cultural",
        "question": "¿El sponsor respeta la identidad cultural/patrimonial del proyecto?",
        "weight": 1.0,
    },
    {
        "key": "brand_congruence",
        "name": "Congruencia de marca",
        "question": "¿Los valores de la marca son compatibles con el propósito del proyecto?",
        "weight": 1.0,
    },
    {
        "key": "curatorial_control",
        "name": "Control curatorial",
        "question": "¿El proyecto conserva el control de contenidos/decisiones?",
        "weight": 1.2,
    },
    {
        "key": "brand_saturation",
        "name": "Saturación de marca",
        "question": "¿La presencia de marca será moderada y no invasiva?",
        "weight": 1.2,
    },
    {
        "key": "community_impact",
        "name": "Impacto comunitario",
        "question": "¿La comunidad percibirá valor (no explotación) y habrá beneficios claros?",
        "weight": 1.0,
    },
]

DEFAULT_THRESHOLDS = {
    "green_min": 4.0,
    "amber_min": 3.0,
    "red_min": 2.0,
}

DEFAULT_RED_FLAGS: List[Tuple[str, int]] = [
    ("curatorial_control", 3),
    ("brand_saturation", 3),
    ("cultural_identity", 3),
]

RECOMMENDATIONS = {
    "curatorial_control": [
        "Incluir cláusula: el sponsor NO define programación, guion, selección de espacios ni contenidos.",
        "Crear comité/rol curatorial con poder de veto ante interferencias comerciales.",
    ],
    "brand_saturation": [
        "Aplicar regla 70/30 (70% cultura, 30% marca) y limitar logos por pieza.",
        "Prohibir branding físico sobre patrimonio; usar señalética reversible y discreta.",
    ],
    "cultural_identity": [
        "Definir narrativa oficial del proyecto y alinear toda activación a esa narrativa.",
        "Evitar naming que opaque la marca del proyecto: preferir 'con el apoyo de' vs 'X presenta Y'.",
    ],
    "brand_congruence": [
        "Pedir justificación de valores: ¿por qué esta marca es un match cultural? Dejarlo por escrito.",
        "Revisar riesgos reputacionales y controversias recientes antes de firmar.",
    ],
    "community_impact": [
        "Incluir beneficios comunitarios: accesibilidad, apoyo a artistas/guías locales, becas/entradas.",
        "Medir y publicar indicadores de impacto (asistencia, satisfacción, economía local).",
    ],
}

NAMING_GUIDE = {
    "low_risk": [
        "{event} — con el apoyo de {sponsor}",
        "{event} — patrocinador principal: {sponsor}",
    ],
    "medium_risk": [
        "{event} presentado por {sponsor} (solo si branding es discreto y sin control curatorial)",
    ],
    "high_risk": [
        "{sponsor} {event} (evitar: tiende a diluir identidad del proyecto)",
    ],
}


@dataclass
class MECCInput:
    project_name: str
    event_name: str
    sponsor_name: str
    scores: Dict[str, int]
    notes: str = ""
    dimensions: List[dict] = None
    thresholds: Dict[str, float] = None
    red_flags: List[Tuple[str, int]] = None


@dataclass
class MECCResult:
    weighted_score: float
    unweighted_score: float
    label: str
    red_flags_triggered: List[str]
    per_dimension: List[dict]
    recommendations: List[str]
    naming_advice: List[str]


def compute_scores(dimensions: List[dict], scores: Dict[str, int]):
    total_w = 0.0
    total_ws = 0.0
    total_s = 0.0
    per_dim = []
    for d in dimensions:
        key = d["key"]
        w = float(d.get("weight", 1.0))
        s = int(scores[key])
        total_w += w
        total_ws += w * s
        total_s += s
        per_dim.append(
            {
                "key": key,
                "name": d["name"],
                "weight": w,
                "score": s,
                "weighted": w * s,
                "question": d.get("question", ""),
            }
        )
    weighted_avg = total_ws / total_w if total_w else float("nan")
    unweighted_avg = total_s / len(dimensions) if dimensions else float("nan")
    return weighted_avg, unweighted_avg, per_dim


def classify(score: float, thresholds: Dict[str, float]) -> str:
    if score >= thresholds["green_min"]:
        return "🟢 Compatible (bajo riesgo de mercantilización)"
    if score >= thresholds["amber_min"]:
        return "🟠 Aceptable con reglas (riesgo moderado)"
    if score >= thresholds["red_min"]:
        return "🔴 Riesgo cultural (solo con salvaguardas fuertes)"
    return "⛔ No recomendable (alto riesgo / rechazar)"


def check_red_flags(scores: Dict[str, int], red_flags: List[Tuple[str, int]]) -> List[str]:
    triggered = []
    for key, min_ok in red_flags:
        if int(scores.get(key, 0)) < int(min_ok):
            triggered.append(f"{key} < {min_ok}")
    return triggered


def build_recommendations(dimensions: List[dict], scores: Dict[str, int], red_flags_triggered: List[str]) -> List[str]:
    recs = []
    for d in dimensions:
        key = d["key"]
        if int(scores[key]) < 4:
            for r in RECOMMENDATIONS.get(key, []):
                recs.append(f"**{d['name']}**: {r}")

    if red_flags_triggered:
        recs.append("**Red flags activos**: exigir anexos contractuales (gobernanza cultural + límites de marca) antes de firmar.")
        recs.append("Incluir **derecho de salida** si el sponsor intenta intervenir curaduría o exceder presencia de marca.")

    # dedupe preserve order
    out, seen = [], set()
    for r in recs:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def naming_advice(score: float, sponsor: str, event: str) -> List[str]:
    if score >= 4.0:
        options = NAMING_GUIDE["low_risk"]
    elif score >= 3.0:
        options = NAMING_GUIDE["medium_risk"] + NAMING_GUIDE["low_risk"]
    else:
        options = NAMING_GUIDE["low_risk"] + NAMING_GUIDE["high_risk"]
    return [o.format(sponsor=sponsor, event=event) for o in options]


def evaluate(mecc_in: MECCInput) -> MECCResult:
    dimensions = mecc_in.dimensions or DEFAULT_DIMENSIONS
    thresholds = mecc_in.thresholds or DEFAULT_THRESHOLDS
    red_flags = mecc_in.red_flags or DEFAULT_RED_FLAGS

    weighted, unweighted, per_dim = compute_scores(dimensions, mecc_in.scores)
    label = classify(weighted, thresholds)
    rf = check_red_flags(mecc_in.scores, red_flags)
    recs = build_recommendations(dimensions, mecc_in.scores, rf)
    naming = naming_advice(weighted, mecc_in.sponsor_name, mecc_in.event_name)

    return MECCResult(
        weighted_score=weighted,
        unweighted_score=unweighted,
        label=label,
        red_flags_triggered=rf,
        per_dimension=per_dim,
        recommendations=recs,
        naming_advice=naming,
    )
