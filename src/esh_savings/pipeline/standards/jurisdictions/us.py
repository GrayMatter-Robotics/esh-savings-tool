from esh_savings.models.features import ExposureFeatures
from esh_savings.constants.vibration import HAV_EAV, HAV_ELV
from esh_savings.constants.regulatory import (
    OSHA_INSPECTION_PROB, OSHA_CITATION_PROB, OSHA_EXPECTED_PENALTY_USD,
)


class USAdapter:
    name = "US"
    hav_eav: float = HAV_EAV
    hav_elv: float = HAV_ELV

    def regulatory_cost(self, features: ExposureFeatures) -> float:
        """Expected annual US regulatory cost: P(inspection) × P(citation|inspection) × E(penalty)."""
        if features.a8 is None and features.si_factors is None:
            return 0.0
        return OSHA_INSPECTION_PROB * OSHA_CITATION_PROB * OSHA_EXPECTED_PENALTY_USD

    def compliance_flags(self, features: ExposureFeatures) -> dict[str, bool]:
        flags: dict[str, bool] = {}
        if features.a8 is not None:
            flags["a8_exceeds_eav"] = features.a8 > self.hav_eav
            flags["a8_exceeds_elv"] = features.a8 > self.hav_elv
        return flags
