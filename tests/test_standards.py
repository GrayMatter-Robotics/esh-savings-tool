import pytest
from esh_savings.models.features import ExposureFeatures, SIFactors
from esh_savings.models.scores import RiskScores
from esh_savings.pipeline.standards.evaluator import evaluate
from esh_savings.pipeline.standards.jurisdictions.us import USAdapter
from esh_savings.constants.vibration import HAV_EAV, HAV_ELV
from esh_savings.constants.ergonomics import STRAIN_INDEX_HAZARD


def _adapter():
    return USAdapter()


def test_vibration_score_at_eav_is_100():
    features = ExposureFeatures(a8=HAV_EAV)
    scores = evaluate(features, _adapter())
    assert scores.vibration_score == pytest.approx(100.0)


def test_vibration_score_below_eav():
    features = ExposureFeatures(a8=HAV_EAV / 2)
    scores = evaluate(features, _adapter())
    assert scores.vibration_score == pytest.approx(50.0)


def test_vibration_score_capped_at_100():
    features = ExposureFeatures(a8=HAV_ELV * 2)  # way over limit
    scores = evaluate(features, _adapter())
    assert scores.vibration_score == 100.0


def test_compliance_flags_above_eav():
    features = ExposureFeatures(a8=HAV_EAV + 0.1)
    scores = evaluate(features, _adapter())
    assert scores.compliance_status.a8_exceeds_eav is True
    assert scores.compliance_status.a8_exceeds_elv is False


def test_compliance_flags_above_elv():
    features = ExposureFeatures(a8=HAV_ELV + 0.1)
    scores = evaluate(features, _adapter())
    assert scores.compliance_status.a8_exceeds_eav is True
    assert scores.compliance_status.a8_exceeds_elv is True


def test_havs_onset_estimated_at_eav():
    features = ExposureFeatures(a8=HAV_EAV)
    scores = evaluate(features, _adapter())
    # At EAV (2.5 m/s²): Dy = 31.8 × 2.5^-1.06 ≈ 11.8 years
    assert scores.havs_onset_years == pytest.approx(11.8, abs=0.5)


def test_si_score_from_factors():
    factors = SIFactors(im=1.0, du=1.0, em=1.0, hwp=1.0, sw=1.0, dd=1.0)
    features = ExposureFeatures(si_factors=factors)
    scores = evaluate(features, _adapter())
    assert scores.si_score == pytest.approx(1.0)


def test_si_hazardous_flag():
    # SI = 3 × 3 × 1 × 1 × 1 × 1 = 9 >= 7 → hazardous
    factors = SIFactors(im=3.0, du=3.0, em=1.0, hwp=1.0, sw=1.0, dd=1.0)
    features = ExposureFeatures(si_factors=factors)
    scores = evaluate(features, _adapter())
    assert scores.compliance_status.si_hazardous is True


def test_no_features_returns_none_scores():
    features = ExposureFeatures()
    scores = evaluate(features, _adapter())
    assert scores.vibration_score is None
    assert scores.force_score is None
