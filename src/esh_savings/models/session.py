from pydantic import BaseModel, ConfigDict
import numpy as np


class SessionMetadata(BaseModel):
    material: str = "unknown"
    jurisdiction: str = "US"
    se_id: str = ""


class SandingSession(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    force_xyz:    np.ndarray           # (N, 3), N — Fx Fy Fz
    torque_xyz:   np.ndarray           # (N, 3), Nm
    accel_xyz:    np.ndarray           # (N, 3), m/s² — vibration
    position_xyz: np.ndarray | None = None  # (N, 3), mm — ingested but not used in pipeline
    orientation:  np.ndarray | None = None  # (N, 4), quaternion (w, x, y, z)
    timestamps:   np.ndarray           # (N,), s
    metadata:     SessionMetadata = SessionMetadata()
