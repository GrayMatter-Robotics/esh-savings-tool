import warnings
from pathlib import Path

import h5py
import numpy as np

from esh_savings.models.session import SandingSession
from esh_savings.pipeline.ingestion.config import IngestionConfig


def read_hdf5(path: Path, config: IngestionConfig | None = None) -> SandingSession:
    cfg = config or IngestionConfig()

    with h5py.File(path, "r") as f:
        timestamps = f[cfg.hdf5_timestamps][:]
        force_xyz  = f[cfg.hdf5_force_xyz][:]
        accel_xyz  = f[cfg.hdf5_accel_xyz][:]

        if cfg.hdf5_torque_xyz in f:
            torque_xyz = f[cfg.hdf5_torque_xyz][:]
        else:
            warnings.warn(
                f"Dataset '{cfg.hdf5_torque_xyz}' not found; filling with zeros",
                UserWarning,
                stacklevel=2,
            )
            torque_xyz = np.zeros_like(force_xyz)

        position_xyz = f[cfg.hdf5_position_xyz][:] if cfg.hdf5_position_xyz in f else None
        orientation  = f[cfg.hdf5_orientation][:]   if cfg.hdf5_orientation in f else None

    return SandingSession(
        force_xyz=force_xyz,
        torque_xyz=torque_xyz,
        accel_xyz=accel_xyz,
        position_xyz=position_xyz,
        orientation=orientation,
        timestamps=timestamps,
    )
