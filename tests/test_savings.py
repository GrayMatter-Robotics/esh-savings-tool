import pytest
from esh_savings.models.scores import RiskScores, ComplianceStatus
from esh_savings.models.se_inputs import SEProvidedInputs
from esh_savings.models.config import AnalysisConfig
from esh_savings.models.result import ProvenanceTag
from esh_savings.pipeline.savings import compute_savings
from esh_savings.constants.economics import (
    MANUAL_MSD_IR, TOTAL_CLAIM_COST_USD, WAGE_INFLATION_RATE,
)


def _scores_both_channels() -> RiskScores:
    return RiskScores(
        vibration_score=60.0,
        force_score=80.0,
        compliance_status=ComplianceStatus(a8_exceeds_eav=True),
        a8_vs_eav=0.6,
        a8_vs_elv=0.3,
        havs_onset_years=20.0,
    )


def test_esh_manual_score_weighted_mean():
    scores = _scores_both_channels()
    cfg = AnalysisConfig(include_vibration=True, include_force=True, include_orientation=False)
    result = compute_savings(scores, SEProvidedInputs(operator_count=1), cfg)
    # (40 × 60 + 30 × 80) / 70 = (2400 + 2400) / 70 ≈ 68.57
    assert result.esh_risk_score_manual == pytest.approx(68.57, abs=0.1)


def test_robot_score_lower_than_manual():
    scores = _scores_both_channels()
    cfg = AnalysisConfig(include_vibration=True, include_force=True, include_orientation=False)
    result = compute_savings(scores, SEProvidedInputs(operator_count=1), cfg)
    assert result.esh_risk_score_robot < result.esh_risk_score_manual


def test_annual_savings_positive():
    scores = _scores_both_channels()
    cfg = AnalysisConfig()
    result = compute_savings(scores, SEProvidedInputs(operator_count=10), cfg)
    assert result.annual_esh_savings_usd > 0


def test_annual_cost_scales_with_operator_count():
    scores = _scores_both_channels()
    cfg = AnalysisConfig()
    r1 = compute_savings(scores, SEProvidedInputs(operator_count=1), cfg)
    r10 = compute_savings(scores, SEProvidedInputs(operator_count=10), cfg)
    assert r10.annual_injury_cost_manual == pytest.approx(r1.annual_injury_cost_manual * 10)


def test_y5_cost_higher_than_y1_due_to_inflation():
    scores = _scores_both_channels()
    cfg = AnalysisConfig()
    result = compute_savings(scores, SEProvidedInputs(operator_count=5), cfg)
    assert result.y5_cost_manual > result.y1_cost_manual


def test_y5_inflation_factor():
    scores = _scores_both_channels()
    cfg = AnalysisConfig()
    result = compute_savings(scores, SEProvidedInputs(operator_count=1), cfg)
    expected = result.annual_injury_cost_manual * (1 + WAGE_INFLATION_RATE) ** 5
    assert result.y5_cost_manual == pytest.approx(expected, rel=1e-6)


def test_provenance_map_populated():
    scores = _scores_both_channels()
    cfg = AnalysisConfig()
    result = compute_savings(scores, SEProvidedInputs(operator_count=1), cfg)
    assert "annual_injury_cost_manual" in result.provenance_map
    assert result.provenance_map["annual_injury_cost_manual"] == ProvenanceTag.DEFAULT


def test_single_channel_renormalizes_score():
    scores = RiskScores(
        vibration_score=80.0,
        force_score=None,
        compliance_status=ComplianceStatus(),
    )
    cfg = AnalysisConfig(include_vibration=True, include_force=False, include_orientation=False)
    result = compute_savings(scores, SEProvidedInputs(operator_count=1), cfg)
    # Only vibration: (40 × 80) / 40 = 80
    assert result.esh_risk_score_manual == pytest.approx(80.0)
