"""Regulatory compliance constants: OSHA penalties and inspection probabilities.

Source: OSHA Jan 2025 penalty schedule
"""

# OSHA Jan 2025 penalty schedule
OSHA_SERIOUS_MAX_USD: float = 16_550.0    # USD/violation [V]
OSHA_WILLFUL_MAX_USD: float = 165_514.0   # USD/violation [V]
OSHA_FAILURE_ABATE_USD: float = 16_550.0  # USD/day      [V]

# US expected annual regulatory cost = P(inspection) × P(citation|inspection) × E(penalty)
OSHA_INSPECTION_PROB: float = 0.03    # /yr [D] baseline rate for manufacturing
OSHA_CITATION_PROB: float = 0.65      # given inspection [D]
OSHA_EXPECTED_PENALTY_USD: float = 8_000.0  # USD given citation [D]
