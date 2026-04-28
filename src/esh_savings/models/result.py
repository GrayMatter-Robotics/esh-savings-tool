from enum import Enum
from pydantic import BaseModel
from esh_savings.models.scores import ComplianceStatus


class ProvenanceTag(str, Enum):
    MEASURED  = "MEASURED"
    COMPUTED  = "COMPUTED"
    DEFAULT   = "DEFAULT"
    ESTIMATED = "ESTIMATED"


class ESHResult(BaseModel):
    esh_risk_score_manual: float
    esh_risk_score_robot:  float
    risk_reduction_pct:    float

    annual_injury_cost_manual:      float
    annual_injury_cost_robot:       float
    emr_savings_annual_usd:         float = 0.0   # Phase 2
    absenteeism_savings_annual_usd: float = 0.0   # Phase 2
    annual_esh_savings_usd:         float

    y1_cost_manual: float;  y1_cost_robot: float
    y2_cost_manual: float;  y2_cost_robot: float
    y3_cost_manual: float;  y3_cost_robot: float
    y4_cost_manual: float;  y4_cost_robot: float
    y5_cost_manual: float;  y5_cost_robot: float

    compliance_status:           ComplianceStatus
    havs_onset_estimate:         float | None = None
    a8_vs_eav:                   float | None = None   # A(8)/EAV ratio from RiskScores
    payback_contribution_years:  float = 0.0   # Phase 2 — robot system cost not tracked yet

    provenance_map: dict[str, ProvenanceTag]
