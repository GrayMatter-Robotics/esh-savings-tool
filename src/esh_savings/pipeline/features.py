"""Stage 2: Feature extraction — vibration and force exposure features.

Phase 1 notes:
- Vibration uses *unweighted* vector RMS (ISO 8041-1 Wh frequency weighting deferred to Phase 2).
- Orientation features (arm_elevation_deg, wrist_pronation_deg) are deferred to Phase 3.
- SI postural multipliers HWP, SW, DD are fixed [D] defaults; Phase 3 will derive from sensors.
"""

import numpy as np
from scipy import signal as sp_signal

from esh_savings.models.session import SandingSession
from esh_savings.models.features import ExposureFeatures, SIFactors
from esh_savings.models.config import AnalysisConfig
from esh_savings.constants.vibration import SHIFT_DURATION_S
from esh_savings.constants.ergonomics import SNOOK_PUSH_LIMIT_N


def _detect_active_mask(accel_xyz: np.ndarray, timestamps: np.ndarray) -> np.ndarray:
    """Boolean mask of active-sanding samples.

    Algorithm: rolling 0.5 s RMS of the vector magnitude; samples above
    20 % of the 95th-percentile rolling RMS are classified as active.
    """
    dt = float(np.median(np.diff(timestamps)))
    window = max(1, int(0.5 / dt))
    rms = np.linalg.norm(accel_xyz, axis=1)
    kernel = np.ones(window) / window
    rolling_rms = np.sqrt(np.convolve(rms ** 2, kernel, mode="same"))
    threshold = 0.20 * float(np.percentile(rolling_rms, 95))
    return rolling_rms > threshold


def _si_im(pct_mvc: float) -> float:
    """Intensity-of-exertion multiplier (Moore & Garg 1995, Table 1)."""
    if pct_mvc < 10:
        return 0.5
    if pct_mvc < 30:
        return 1.0
    if pct_mvc < 50:
        return 1.5
    if pct_mvc < 70:
        return 2.0
    if pct_mvc < 90:
        return 3.0
    return 4.0


def _si_du(duty_cycle: float) -> float:
    """Duration-of-exertion multiplier (Moore & Garg 1995)."""
    dc = duty_cycle * 100
    if dc < 10:
        return 0.5
    if dc < 30:
        return 1.0
    if dc < 50:
        return 1.5
    if dc < 80:
        return 2.0
    return 3.0


def _si_em(rep_rate: float) -> float:
    """Efforts-per-minute multiplier (Moore & Garg 1995)."""
    if rep_rate < 4:
        return 0.5
    if rep_rate < 8:
        return 1.0
    if rep_rate < 12:
        return 1.5
    if rep_rate < 16:
        return 2.0
    return 3.0


def extract_features(
    session: SandingSession,
    config: AnalysisConfig,
    shift_duration_s: float = SHIFT_DURATION_S,
) -> ExposureFeatures:
    """Extract vibration and force exposure features from a sanding session.

    Parameters
    ----------
    session:
        Loaded sensor data for one sanding session.
    config:
        Flags that gate which channel groups are computed.
    shift_duration_s:
        Reference shift length used for A(8) normalisation (default 8 h).
        Pass ``se_inputs.shift_duration_s`` from the pipeline.

    Returns
    -------
    ExposureFeatures
        Fields for disabled channels are ``None``.
    """
    active = _detect_active_mask(session.accel_xyz, session.timestamps)
    dt = float(np.median(np.diff(session.timestamps)))
    t_active_s = float(active.sum()) * dt

    # ------------------------------------------------------------------
    # Vibration  (§ahv, §A(8))
    # Phase 1: unweighted vector RMS; ISO 8041-1 Wh weighting is Phase 2.
    # ------------------------------------------------------------------
    ahv: float | None = None
    a8: float | None = None

    if config.include_vibration and active.any():
        accel_active = session.accel_xyz[active]
        ahv = float(np.sqrt(np.mean(np.sum(accel_active ** 2, axis=1))))
        a8 = float(ahv * np.sqrt(t_active_s / shift_duration_s))

    # ------------------------------------------------------------------
    # Force  (§HAL, §SI)
    # ------------------------------------------------------------------
    hal = fz_mean = fz_p50 = fz_p90 = None
    duty_cycle = repetition_rate = None
    si_factors: SIFactors | None = None

    if config.include_force and active.any():
        fz = session.force_xyz[active, 2]          # Fz column — push direction
        fz_pos = fz[fz > 0]

        if len(fz_pos) > 0:
            fz_mean = float(np.mean(fz_pos))
            fz_p50 = float(np.percentile(fz_pos, 50))
            fz_p90 = float(np.percentile(fz_pos, 90))
        else:
            fz_mean = fz_p50 = fz_p90 = 0.0

        threshold = 0.10 * SNOOK_PUSH_LIMIT_N
        duty_cycle = float((fz > threshold).mean())

        if t_active_s > 0:
            peaks, _ = sp_signal.find_peaks(
                fz,
                height=threshold,
                distance=max(1, int(0.5 / dt)),
            )
            repetition_rate = float(len(peaks) / (t_active_s / 60.0))
        else:
            repetition_rate = 0.0

        # HAL: empirical approximation to ACGIH nomogram (Marley & Kumar 1996)
        hal = min(10.0, 6.56 * duty_cycle)

        pct_mvc = (fz_p50 / SNOOK_PUSH_LIMIT_N * 100.0) if fz_p50 else 0.0
        si_factors = SIFactors(
            im=_si_im(pct_mvc),
            du=_si_du(duty_cycle),
            em=_si_em(repetition_rate),
            hwp=1.5,   # [D] slightly deviated wrist — Phase 3 will sensor-derive
            sw=1.0,    # [D] normal work pace
            dd=1.0,    # [D] standard 8-hour shift
        )

    return ExposureFeatures(
        ahv=ahv,
        a8=a8,
        hal=hal,
        fz_mean=fz_mean,
        fz_p50=fz_p50,
        fz_p90=fz_p90,
        duty_cycle=duty_cycle,
        repetition_rate=repetition_rate,
        si_factors=si_factors,
    )
