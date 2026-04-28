"""Stage 5: ESH savings calculator — composite risk score and Y1–Y5 injury cost forecast."""
from esh_savings.models.scores import RiskScores
from esh_savings.models.result import ESHResult, ProvenanceTag
from esh_savings.models.se_inputs import SEProvidedInputs
from esh_savings.models.config import AnalysisConfig
from esh_savings.constants.economics import (
    MANUAL_MSD_IR, ROBOT_MSD_IR, TOTAL_CLAIM_COST_USD,
    WAGE_INFLATION_RATE, ROBOT_LOAD_UNLOAD_FRACTION,
)

_WEIGHTS = {"vibration": 40.0, "force": 30.0, "posture": 30.0}


def _esh_composite(
    vibration_score: float | None,
    force_score: float | None,
    rula_score: float | None,
    config: AnalysisConfig,
) -> float:
    total_weight = 0.0
    total_score = 0.0
    if config.include_vibration and vibration_score is not None:
        total_weight += _WEIGHTS["vibration"]
        total_score  += _WEIGHTS["vibration"] * vibration_score
    if config.include_force and force_score is not None:
        total_weight += _WEIGHTS["force"]
        total_score  += _WEIGHTS["force"] * force_score
    if config.include_orientation and rula_score is not None:
        total_weight += _WEIGHTS["posture"]
        total_score  += _WEIGHTS["posture"] * rula_score
    return (total_score / total_weight) if total_weight > 0 else 0.0


def _projected(base: float, year: int) -> float:
    return base * ((1.0 + WAGE_INFLATION_RATE) ** year)


def compute_savings(
    scores: RiskScores,
    se_inputs: SEProvidedInputs,
    config: AnalysisConfig,
) -> ESHResult:
    n = se_inputs.operator_count

    annual_cost_manual = n * (MANUAL_MSD_IR / 10_000.0) * TOTAL_CLAIM_COST_USD
    annual_cost_robot  = n * (ROBOT_MSD_IR  / 10_000.0) * TOTAL_CLAIM_COST_USD
    annual_savings     = annual_cost_manual - annual_cost_robot

    f = ROBOT_LOAD_UNLOAD_FRACTION
    robot_vib   = (scores.vibration_score * f) if scores.vibration_score is not None else None
    robot_force = (scores.force_score     * f) if scores.force_score     is not None else None

    esh_manual = _esh_composite(scores.vibration_score, scores.force_score, scores.rula_score, config)
    esh_robot  = _esh_composite(robot_vib, robot_force, scores.rula_score, config)
    risk_reduction = ((esh_manual - esh_robot) / esh_manual * 100.0) if esh_manual > 0 else 0.0

    provenance: dict[str, ProvenanceTag] = {
        "esh_risk_score_manual":     ProvenanceTag.COMPUTED,
        "esh_risk_score_robot":      ProvenanceTag.COMPUTED,
        "annual_injury_cost_manual": ProvenanceTag.DEFAULT,
        "annual_injury_cost_robot":  ProvenanceTag.ESTIMATED,
    }

    return ESHResult(
        esh_risk_score_manual=esh_manual,
        esh_risk_score_robot=esh_robot,
        risk_reduction_pct=risk_reduction,
        annual_injury_cost_manual=annual_cost_manual,
        annual_injury_cost_robot=annual_cost_robot,
        annual_esh_savings_usd=annual_savings,
        y1_cost_manual=_projected(annual_cost_manual, 1),
        y1_cost_robot=_projected(annual_cost_robot, 1),
        y2_cost_manual=_projected(annual_cost_manual, 2),
        y2_cost_robot=_projected(annual_cost_robot, 2),
        y3_cost_manual=_projected(annual_cost_manual, 3),
        y3_cost_robot=_projected(annual_cost_robot, 3),
        y4_cost_manual=_projected(annual_cost_manual, 4),
        y4_cost_robot=_projected(annual_cost_robot, 4),
        y5_cost_manual=_projected(annual_cost_manual, 5),
        y5_cost_robot=_projected(annual_cost_robot, 5),
        compliance_status=scores.compliance_status,
        havs_onset_estimate=scores.havs_onset_years,
        provenance_map=provenance,
    )
