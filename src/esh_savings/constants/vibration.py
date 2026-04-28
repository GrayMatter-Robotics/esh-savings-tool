"""Vibration exposure thresholds and coefficients.

Source: ISO 5349-1:2001 §6.2; EU Directive 2002/44/EC
"""

# ISO 5349-1:2001 Exposure Action Value
HAV_EAV: float = 2.5  # m/s²  [V]

# ISO 5349-1:2001 Exposure Limit Value
HAV_ELV: float = 5.0  # m/s²  [V]

# Standard 8-hr shift; override to 36_000 (10h) or 43_200 (12h) via SE input
SHIFT_DURATION_S: float = 28_800.0  # s  [D]

# ISO 5349-1:2001 Annex C — years to 10% HAVS prevalence: Dy = COEFF × A(8)^EXP
HAVS_ONSET_COEFF: float = 31.8  # [V]
HAVS_ONSET_EXP: float = -1.06   # [V]

# UK Control of Vibration at Work Regulations 2005
HSE_POINTS_EAV: int = 100   # pts [V]
HSE_POINTS_ELV: int = 400   # pts [V]
