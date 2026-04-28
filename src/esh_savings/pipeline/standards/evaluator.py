"""Stage 3: apply jurisdiction thresholds to exposure features → risk scores."""

from esh_savings.models.features import ExposureFeatures
from esh_savings.models.scores import RiskScores, ComplianceStatus
from esh_savings.constants.vibration import HAVS_ONSET_COEFF, HAVS_ONSET_EXP
from esh_savings.constants.ergonomics import STRAIN_INDEX_HAZARD
from esh_savings.pipeline.standards.jurisdictions import JurisdictionAdapter


def evaluate(features: ExposureFeatures, adapter: JurisdictionAdapter) -> RiskScores:

    # --- Vibration ---
    vibration_score = a8_vs_eav = a8_vs_elv = havs_onset = None
    if features.a8 is not None:
        eav = adapter.hav_eav
        elv = adapter.hav_elv
        a8_vs_eav = features.a8 / eav
        a8_vs_elv = features.a8 / elv
        vibration_score = min(100.0, a8_vs_eav * 100.0)
        if features.a8 > 0:
            havs_onset = HAVS_ONSET_COEFF * (features.a8 ** HAVS_ONSET_EXP)

    # --- Force / Strain Index ---
    force_score = si_score = si_vs_hazard = None
    if features.si_factors is not None:
        f = features.si_factors
        si_score = f.im * f.du * f.em * f.hwp * f.sw * f.dd
        si_vs_hazard = si_score / STRAIN_INDEX_HAZARD
        force_score = min(100.0, si_vs_hazard * 100.0)

    # --- Compliance ---
    flags = adapter.compliance_flags(features)
    compliance = ComplianceStatus(
        a8_exceeds_eav=flags.get("a8_exceeds_eav", False),
        a8_exceeds_elv=flags.get("a8_exceeds_elv", False),
        si_hazardous=(si_score >= STRAIN_INDEX_HAZARD) if si_score is not None else False,
        regulatory_cost_annual_usd=adapter.regulatory_cost(features),
    )

    return RiskScores(
        vibration_score=vibration_score,
        a8_vs_eav=a8_vs_eav,
        a8_vs_elv=a8_vs_elv,
        havs_onset_years=havs_onset,
        force_score=force_score,
        si_score=si_score,
        si_vs_hazard=si_vs_hazard,
        rula_score=None,   # Phase 3
        compliance_status=compliance,
    )
