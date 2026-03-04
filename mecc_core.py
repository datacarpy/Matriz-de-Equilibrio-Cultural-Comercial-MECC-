from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import math


# =========================
# Config base (genérica)
# =========================

DEFAULT_DIMENSIONS = [
    {
        "key": "identity_integrity",
        "name": "Integridad de identidad",
        "question": "¿El sponsor respeta el propósito, tono y narrativa del proyecto sin diluirlos?",
        "weight": 1.2,
        "min_gate": 3,  # gate: si baja de esto, es NO / o requiere salvaguardas fuertes
        "notes_hint": "Ej: sponsor quiere renombrar el evento / cambiar mensaje central",
    },
    {
        "key": "brand_congruence",
        "name": "Congruencia de marca",
        "question": "¿El encaje de valores, público y reputación es coherente (no forzado)?",
        "weight": 1.0,
        "min_gate": 3,
        "notes_hint": "Ej: la marca tiene historial contradictorio con el propósito del proyecto",
    },
    {
        "key": "curatorial_control",
        "name": "Control curatorial",
        "question": "¿El proyecto conserva control total sobre contenidos, programación y decisiones?",
        "weight": 1.4,
        "min_gate": 3,
        "notes_hint": "Ej: sponsor pide aprobar programación, speakers, recorridos, guion, etc.",
    },
    {
        "key": "brand_saturation",
        "name": "Saturación de marca",
        "question": "¿La marca estará presente de forma moderada y no invasiva en la experiencia?",
        "weight": 1.4,
        "min_gate": 3,
        "notes_hint": "Ej: exceso de logos, activaciones agresivas, naming dominante",
    },
    {
        "key": "community_impact",
        "name": "Impacto comunitario",
        "question": "¿Aporta valor real a comunidad/aliados (no se percibe explotación)?",
        "weight": 1.1,
        "min_gate": 3,
        "notes_hint": "Ej: hay beneficios claros: accesibilidad, empleo local, artistas, conservación",
    },
    {
        "key": "heritage_sensitivity",
        "name": "Sensibilidad del contexto",
        "question": "¿Se respetan límites de espacios sensibles (patrimonio, comunidad, seguridad)?",
        "weight": 1.1,
        "min_gate": 3,
        "notes_hint": "Ej: no branding invasivo en espacios sensibles; logística segura",
    },
    {
        "key": "governance_transparency",
        "name": "Gobernanza y transparencia",
        "question": "¿Hay reglas claras: roles, permisos, comunicación, reporte, y rendición de cuentas?",
        "weight": 1.0,
        "min_gate": 3,
        "notes_hint": "Ej: contrato claro, comité, métricas, reportes públicos/privados",
    },
    {
        "key": "dependency_risk",
        "name": "Riesgo de dependencia",
        "question": "¿El proyecto puede sobrevivir sin este sponsor (no dependencia total)?",
        "weight": 0.9,
        "min_gate": 2,
        "notes_hint": "Ej: sponsor aporta >70% del presupuesto sin plan alternativo",
    },
]

# Umbrales (MECC ponderado 0-5)
DEFAULT_THRESHOLDS = {
    "green_min": 4.0,
    "amber_min": 3.2,
    "red_min": 2.6,
}

# Red flags: si alguna dimensión cae por debajo, alerta crítica
DEFAULT_RED_FLAGS: List[Tuple[str, int]] = [
    ("curatorial_control", 3),
    ("brand_saturation", 3),
    ("identity_integrity", 3),
]

# Recomendaciones (accionables)
RECOMMENDATIONS = {
    "identity_integrity": [
        "Definir una narrativa oficial (propósito + tono + límites) y alinear toda activación a esa narrativa.",
        "Evitar naming que opaque la marca del proyecto: preferir “con el apoyo de” vs “X presenta Y”.",
    ],
    "brand_congruence": [
        "Revisar reputación y riesgos: controversias recientes, coherencia con el propósito, percepción pública.",
        "Pedir una justificación escrita del “match” (para el deck y el contrato).",
    ],
    "curatorial_control": [
        "Cláusula: el sponsor NO define ni aprueba programación, guion, selección de espacios o contenidos.",
        "Crear rol/comité curatorial con poder de veto ante interferencias comerciales.",
    ],
    "brand_saturation": [
        "Aplicar regla 70/30 (70% experiencia del proyecto, 30% marca) y limitar logos por pieza.",
        "Prohibir branding físico invasivo en espacios sensibles; señalética reversible y discreta.",
    ],
    "community_impact": [
        "Incluir beneficios comunitarios: accesibilidad, empleo local, apoyo a guías/artistas, becas/entradas.",
        "Medir y publicar indicadores (asistencia, satisfacción, impacto local) para legitimar el aporte.",
    ],
    "heritage_sensitivity": [
        "Mapa de zonas sensibles + lineamientos (qué se puede hacer / qué no).",
        "Plan de seguridad y logística (capacidad, flujo, permisos, seguros) para evitar incidentes reputacionales.",
    ],
    "governance_transparency": [
        "Definir RACI (quién decide qué), cronograma de aprobaciones, y responsables por comunicación.",
        "Reporte post-evento: entregables al sponsor + métricas + lecciones aprendidas.",
    ],
    "dependency_risk": [
        "Diversificar ingresos (2+ sponsors o mix ticketing/grants/partners) para no depender de uno solo.",
        "Incluir plan de continuidad si el sponsor se retira (escala mínima viable).",
    ],
}

# Cláusulas sugeridas (plantillas)
CLAUSE_LIBRARY = {
    "curatorial_control": [
        "El Sponsor reconoce que el control curatorial y la programación pertenecen exclusivamente al Organizador. El Sponsor no tendrá derecho de aprobación sobre contenidos, guion, selección de espacios o participantes.",
        "Se establece un Comité Curatorial con autoridad final sobre contenidos. Cualquier solicitud comercial deberá ser evaluada por el Comité y podrá ser rechazada sin penalidad.",
    ],
    "brand_saturation": [
        "La presencia de marca se limitará a: (i) materiales digitales, (ii) punto de bienvenida, (iii) mención verbal y/o logo en piezas definidas. Se prohíbe instalación permanente, adhesivos o intervención sobre fachadas/elementos sensibles.",
        "Se adopta el principio de proporcionalidad: la experiencia prioriza el contenido del proyecto. Se limita el uso de logos por pieza y se prohíben activaciones invasivas que alteren el recorrido/experiencia.",
    ],
    "identity_integrity": [
        "El naming del evento conservará la marca principal del proyecto. El Sponsor será mencionado como 'con el apoyo de' o 'patrocinador principal', evitando denominaciones que sustituyan la identidad del proyecto.",
    ],
    "governance_transparency": [
        "Se acuerda un plan de gobernanza: roles, aprobaciones, cronograma, entregables y métricas. El Organizador entregará un reporte post-evento con indicadores de impacto y cumplimiento.",
    ],
    "dependency_risk": [
        "Las partes acuerdan un alcance mínimo viable independiente de la continuidad del sponsor. El Organizador mantiene la posibilidad de sumar co-sponsors sin veto, salvo categorías excluyentes acordadas explícitamente.",
    ],
}


NAMING_GUIDE = {
    "low_risk": [
        "{event} — con el apoyo de {sponsor}",
        "{event} — patrocinador principal: {sponsor}",
    ],
    "medium_risk": [
        "{event} presentado por {sponsor} (solo si el branding es discreto y sin control curatorial)",
        "{event} — con el apoyo de {sponsor}",
    ],
    "high_risk": [
        "{sponsor} {event} (evitar: tiende a diluir identidad del proyecto)",
        "{event} — con el apoyo de {sponsor}",
    ],
}


# =========================
# Modelos
# =========================

@dataclass
class MECCInput:
    project_name: str
    event_name: str
    sponsor_name: str
    scores: Dict[str, int]
    notes_by_dimension: Dict[str, str]
    global_notes: str = ""
    thresholds: Optional[Dict[str, float]] = None
    red_flags: Optional[List[Tuple[str, int]]] = None
    dimensions: Optional[List[dict]] = None


@dataclass
class MECCResult:
    weighted_score: float
    unweighted_score: float
    commercialization_risk_0_100: float
    label: str
    gates_failed: List[str]
    red_flags_triggered: List[str]
    per_dimension: List[dict]
    recommendations: List[str]
    clauses: List[str]
    naming_advice: List[str]


# =========================
# Cálculo
# =========================

def _clamp_int(x: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, x))


def compute_scores(dimensions: List[dict], scores: Dict[str, int]):
    total_w = 0.0
    total_ws = 0.0
    total_s = 0.0
    per_dim = []

    for d in dimensions:
        key = d["key"]
        w = float(d.get("weight", 1.0))
        s = _clamp_int(int(scores.get(key, 3)), 1, 5)
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
                "min_gate": int(d.get("min_gate", 1)),
            }
        )

    weighted_avg = total_ws / total_w if total_w else float("nan")
    unweighted_avg = total_s / len(dimensions) if dimensions else float("nan")
    return weighted_avg, unweighted_avg, per_dim


def classify(weighted_score: float, thresholds: Dict[str, float]) -> str:
    if weighted_score >= thresholds["green_min"]:
        return "🟢 Compatible (bajo riesgo de mercantilización)"
    if weighted_score >= thresholds["amber_min"]:
        return "🟠 Aceptable con reglas (riesgo moderado)"
    if weighted_score >= thresholds["red_min"]:
        return "🔴 Riesgo (solo con salvaguardas fuertes)"
    return "⛔ No recomendable (alto riesgo / rechazar)"


def commercialization_risk(weighted_score: float) -> float:
    """
    Convierte MECC (1..5) a un riesgo (0..100) de mercantilización.
    5 => 0 riesgo, 1 => 100 riesgo.
    """
    if math.isnan(weighted_score):
        return 100.0
    # map lineal inverso
    risk = (5.0 - weighted_score) / 4.0 * 100.0
    return max(0.0, min(100.0, risk))


def check_red_flags(scores: Dict[str, int], red_flags: List[Tuple[str, int]]) -> List[str]:
    triggered = []
    for key, min_ok in red_flags:
        if int(scores.get(key, 0)) < int(min_ok):
            triggered.append(f"{key} < {min_ok}")
    return triggered


def check_gates(per_dimension: List[dict]) -> List[str]:
    failed = []
    for d in per_dimension:
        if int(d["score"]) < int(d["min_gate"]):
            failed.append(f"{d['key']} ({d['name']}) < gate {d['min_gate']}")
    return failed


def build_recommendations(dimensions: List[dict], scores: Dict[str, int], red_flags_triggered: List[str], gates_failed: List[str]) -> List[str]:
    recs: List[str] = []
    for d in dimensions:
        key = d["key"]
        s = int(scores.get(key, 3))
        if s < 4:
            for r in RECOMMENDATIONS.get(key, []):
                recs.append(f"**{d['name']}**: {r}")

    if gates_failed:
        recs.append("**Gates fallidos**: no avanzar sin salvaguardas contractuales explícitas y ajuste de alcance.")
    if red_flags_triggered:
        recs.append("**Red flags activos**: exigir anexos (gobernanza + límites de marca + control curatorial) antes de firmar.")
        recs.append("Incluir **derecho de salida**: si el sponsor interfiere curaduría o excede presencia de marca, rescisión sin penalidad.")

    # dedupe
    out, seen = [], set()
    for r in recs:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def build_clauses(dimensions: List[dict], scores: Dict[str, int]) -> List[str]:
    clauses: List[str] = []
    # si la dimensión es baja, sugerir cláusulas asociadas
    for d in dimensions:
        key = d["key"]
        s = int(scores.get(key, 3))
        if s < 4:
            for c in CLAUSE_LIBRARY.get(key, []):
                clauses.append(f"- {c}")
    # dedupe
    out, seen = [], set()
    for c in clauses:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def naming_advice(weighted_score: float, sponsor: str, event: str) -> List[str]:
    if weighted_score >= 4.0:
        opts = NAMING_GUIDE["low_risk"]
    elif weighted_score >= 3.2:
        opts = NAMING_GUIDE["medium_risk"]
    else:
        opts = NAMING_GUIDE["high_risk"]
    return [o.format(sponsor=sponsor, event=event) for o in opts]


def evaluate(mecc_in: MECCInput) -> MECCResult:
    dimensions = mecc_in.dimensions or DEFAULT_DIMENSIONS
    thresholds = mecc_in.thresholds or DEFAULT_THRESHOLDS
    red_flags = mecc_in.red_flags or DEFAULT_RED_FLAGS

    weighted, unweighted, per_dim = compute_scores(dimensions, mecc_in.scores)
    label = classify(weighted, thresholds)
    risk = commercialization_risk(weighted)
    rf = check_red_flags(mecc_in.scores, red_flags)
    gates = check_gates(per_dim)
    recs = build_recommendations(dimensions, mecc_in.scores, rf, gates)
    clauses = build_clauses(dimensions, mecc_in.scores)
    naming = naming_advice(weighted, mecc_in.sponsor_name, mecc_in.event_name)

    return MECCResult(
        weighted_score=weighted,
        unweighted_score=unweighted,
        commercialization_risk_0_100=risk,
        label=label,
        gates_failed=gates,
        red_flags_triggered=rf,
        per_dimension=per_dim,
        recommendations=recs,
        clauses=clauses,
        naming_advice=naming,
    )
