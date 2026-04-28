from pydantic import BaseModel


class ComplianceStatus(BaseModel):
    a8_exceeds_eav:              bool = False
    a8_exceeds_elv:              bool = False
    si_hazardous:                bool = False
    regulatory_cost_annual_usd:  float = 0.0


class RiskScores(BaseModel):
    # Vibration — None when include_vibration = False
    vibration_score:  float | None = None   # 0–100
    a8_vs_eav:        float | None = None   # A(8)/EAV ratio
    a8_vs_elv:        float | None = None   # A(8)/ELV ratio
    havs_onset_years: float | None = None   # years to 10% HAVS prevalence

    # Force — None when include_force = False
    force_score:   float | None = None   # 0–100
    si_score:      float | None = None   # product of 6 SI factors
    si_vs_hazard:  float | None = None   # SI / STRAIN_INDEX_HAZARD (uncapped ratio)

    # Posture — None in Phase 1 (no orientation); Phase 3 will populate
    rula_score: float | None = None   # 0–100

    compliance_status: ComplianceStatus
