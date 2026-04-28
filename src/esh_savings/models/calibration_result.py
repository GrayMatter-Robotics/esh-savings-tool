from typing import Literal
from pydantic import BaseModel


class CostCalibration(BaseModel):
    """Phase 2 — produced by cost_calibration stage. Stub model defined here for type stability."""
    cost_per_claim_usd:          float
    calibration_source:          Literal["customer", "blend", "benchmark"]
    emr_savings_annual_usd:      float
    absenteeism_cost_annual_usd: float
    exposure_history_mismatch:   bool
