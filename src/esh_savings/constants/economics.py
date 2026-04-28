"""Economic impact constants: injury costs, wage, and insurance rates.

Sources:
- NCCI Annual Statistical Bulletin 2022-23
- BLS SOII 2022 (manufacturing sector)
- OSHA Safety Pays
"""

# NCCI Annual Statistical Bulletin 2022-23
DIRECT_CLAIM_COST_USD: float = 55_115.0   # USD [V] NCCI 2022-23; direct WC cost per MSD claim
INDIRECT_MULTIPLIER: float = 1.1           # [D] OSHA Safety Pays range 1.1–4.5×; conservative floor — not applied to TOTAL_CLAIM_COST_USD
TOTAL_CLAIM_COST_USD: float = 115_000.0   # USD [V] NCCI all-in cost (direct + indirect combined); use this for savings calculations

# BLS SOII 2022 — manufacturing sector
MANUAL_MSD_IR: float = 41.0     # injuries per 10,000 FTE [D] replaced by SE actuals when available
MEDIAN_DAYS_AWAY: int = 12      # days away from work [V]

# Robot exposure estimate — no peer-reviewed data; midpoint assumption
ROBOT_MSD_IR: float = 5.0                  # injuries per 10,000 FTE [E]
ROBOT_LOAD_UNLOAD_FRACTION: float = 0.15   # fraction of full-shift exposure [D] single-station cell

# Cost escalation and labor
WAGE_INFLATION_RATE: float = 0.03     # /yr [D] SE-adjustable
FBLR_DEFAULT_USD: float = 35.0        # USD/hr [D] fully burdened labor rate; override with customer rate
ABSENTEEISM_OT_MULT: float = 1.5      # [V] OT coverage multiplier (BLS 2022)

# WC calibration (Phase 2)
EMR_DELTA_ESTIMATE: float = 0.15           # [E] midpoint 0.10-0.20; no sanding-robot EMR study
NCCI_WC_RATE_PER_100: float = 4.35        # USD/100 [D] class code 3632 midpoint ($3.50-$5.20)
