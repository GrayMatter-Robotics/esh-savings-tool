from pydantic import BaseModel


class SEProvidedInputs(BaseModel):
    customer_id:         str = ""
    operator_count:      int                     # required — no default
    injury_history:      dict[int, int] = {}     # {year: injury_count}; Phase 2
    wc_cost_paid_usd:    float | None = None     # Phase 2 cost calibration
    wc_base_premium_usd: float | None = None     # Phase 2 cost calibration
    shift_duration_s:    float = 28_800.0
