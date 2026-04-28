import numpy as np
import pytest
from esh_savings.models.session import SandingSession, SessionMetadata
from esh_savings.models.features import ExposureFeatures, SIFactors
from esh_savings.models.scores import RiskScores, ComplianceStatus
from esh_savings.models.result import ESHResult, ProvenanceTag
from esh_savings.models.config import AnalysisConfig
from esh_savings.models.se_inputs import SEProvidedInputs


def _make_session() -> SandingSession:
    n = 100
    return SandingSession(
        force_xyz=np.zeros((n, 3)),
        torque_xyz=np.zeros((n, 3)),
        accel_xyz=np.zeros((n, 3)),
        timestamps=np.linspace(0, 10.0, n),
    )


def test_sanding_session_accepts_numpy():
    session = _make_session()
    assert session.force_xyz.shape == (100, 3)
    assert session.position_xyz is None


def test_analysis_config_defaults():
    cfg = AnalysisConfig()
    assert cfg.include_vibration is True
    assert cfg.include_force is True
    assert cfg.include_orientation is True


def test_se_inputs_requires_operator_count():
    with pytest.raises(Exception):
        SEProvidedInputs()  # operator_count has no default


def test_se_inputs_valid():
    si = SEProvidedInputs(operator_count=5)
    assert si.shift_duration_s == 28_800.0


def test_provenance_tag_values():
    assert ProvenanceTag.MEASURED == "MEASURED"
    assert ProvenanceTag.ESTIMATED == "ESTIMATED"


def test_compliance_status_defaults_safe():
    c = ComplianceStatus()
    assert c.a8_exceeds_eav is False
    assert c.regulatory_cost_annual_usd == 0.0


def test_risk_scores_requires_compliance_status():
    with pytest.raises(Exception):
        RiskScores()  # compliance_status has no default — must be supplied


def test_cost_calibration_rejects_invalid_source():
    from esh_savings.models.calibration_result import CostCalibration
    with pytest.raises(Exception):
        CostCalibration(
            cost_per_claim_usd=50000.0,
            calibration_source="invalid",  # not in Literal["customer","blend","benchmark"]
            emr_savings_annual_usd=1000.0,
            absenteeism_cost_annual_usd=500.0,
            exposure_history_mismatch=False,
        )
    # valid source should work
    c = CostCalibration(
        cost_per_claim_usd=50000.0,
        calibration_source="benchmark",
        emr_savings_annual_usd=1000.0,
        absenteeism_cost_annual_usd=500.0,
        exposure_history_mismatch=False,
    )
    assert c.calibration_source == "benchmark"
