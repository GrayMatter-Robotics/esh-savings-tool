from pydantic import BaseModel


class SIFactors(BaseModel):
    im:  float   # intensity of exertion multiplier
    du:  float   # duration of exertion multiplier
    em:  float   # effort per minute multiplier
    hwp: float   # hand/wrist posture multiplier [D]
    sw:  float   # speed of work multiplier [D]
    dd:  float   # daily duration multiplier [D]


class ExposureFeatures(BaseModel):
    # Vibration — None when include_vibration = False
    ahv: float | None = None           # frequency-weighted RMS, m/s²
    a8:  float | None = None           # daily normalized dose, m/s²

    # Force — None when include_force = False
    hal:             float | None = None   # Hand Activity Level 0–10
    fz_mean:         float | None = None   # N
    fz_p50:          float | None = None   # N
    fz_p90:          float | None = None   # N
    duty_cycle:      float | None = None   # 0–1
    repetition_rate: float | None = None   # actions/min
    si_factors:      SIFactors | None = None

    # Orientation — None when include_orientation = False (Phase 3)
    arm_elevation_deg:   float | None = None  # [D]
    wrist_pronation_deg: float | None = None  # [D]
