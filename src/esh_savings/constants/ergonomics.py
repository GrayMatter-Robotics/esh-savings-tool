"""Ergonomic force limits and postural assessment constants.

Sources:
- Snook & Ciriello 1991
- ISO 11228-2:2007
- ISO 11228-3:2007
- Moore & Garg 1995 (Strain Index)
- McAtamney & Corlett 1993 (RULA)
"""

# Snook & Ciriello 1991 — maximum acceptable push force for occasional push tasks
SNOOK_PUSH_LIMIT_N: float = 129.0  # N [V]

# ISO 11228-2:2007
ISO_INITIAL_PUSH_N: float = 250.0    # N [V]
ISO_SUSTAINED_PUSH_N: float = 150.0  # N [V]

# ISO 11228-3:2007
OCRA_VIBRATION_MULTIPLIER: float = 0.80  # [V] exposure multiplier when vibration present

# Moore & Garg 1995 — Strain Index
STRAIN_INDEX_HAZARD: float = 7.0  # [V] SI >= 7 is hazardous

# McAtamney & Corlett 1993 (RULA)
# Fixed default score applied to joints not derived from sensor (Phase 3 will replace)
RULA_DEFAULT_POSTURE_SCORE: int = 3  # [E]
