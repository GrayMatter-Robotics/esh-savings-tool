import warnings
from pathlib import Path

import h5py
import numpy as np

from esh_savings.models.session import SandingSession
from esh_savings.pipeline.ingestion.config import IngestionConfig


_FALLBACK_DT = 0.01  # 100 Hz synthetic timestamps when dataset absent


def read_hdf5(path: Path, config: IngestionConfig | None = None) -> SandingSession:
    cfg = config or IngestionConfig()

    try:
        with h5py.File(path, "r") as f:
            try:
                # Validate basic structure by attempting to read with explicit error handling
                raw_timestamps = f[cfg.hdf5_timestamps][:] if cfg.hdf5_timestamps in f else None
            except (RuntimeError, OSError, KeyError) as e:
                # h5py raises RuntimeError for corrupted/malformed HDF5 structures
                raise RuntimeError(
                    f"HDF5 file is corrupted or has invalid structure (error: {e}). "
                    f"Ensure the file:\n"
                    f"  1. Is a valid HDF5 file (not just a .hdf5 extension)\n"
                    f"  2. Contains dataset '{cfg.hdf5_timestamps}' (or matches IngestionConfig)\n"
                    f"  3. Is not truncated or partially uploaded"
                ) from e
            
            raw_force_xyz  = f[cfg.hdf5_force_xyz][:]  if cfg.hdf5_force_xyz  in f else None
            raw_accel_xyz  = f[cfg.hdf5_accel_xyz][:]  if cfg.hdf5_accel_xyz  in f else None
            raw_torque_xyz = f[cfg.hdf5_torque_xyz][:] if cfg.hdf5_torque_xyz in f else None
            position_xyz   = f[cfg.hdf5_position_xyz][:] if cfg.hdf5_position_xyz in f else None
            orientation    = f[cfg.hdf5_orientation][:]  if cfg.hdf5_orientation  in f else None
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Unexpected error reading HDF5 file: {type(e).__name__}: {e}") from e

    # Determine N from whatever primary dataset we managed to read.
    n_samples: int = next(
        (len(a) for a in (raw_timestamps, raw_force_xyz, raw_accel_xyz) if a is not None),
        1,
    )
    if n_samples == 1 and all(a is None for a in (raw_timestamps, raw_force_xyz, raw_accel_xyz)):
        raise ValueError(
            f"No primary datasets found in HDF5 file '{path.name}'. "
            f"Expected at least one of: '{cfg.hdf5_timestamps}', '{cfg.hdf5_force_xyz}', "
            f"'{cfg.hdf5_accel_xyz}'. "
            "Pass a custom IngestionConfig if your file uses different dataset paths."
        )

    if raw_force_xyz is None:
        warnings.warn(
            f"Dataset '{cfg.hdf5_force_xyz}' not found; filling with zeros",
            UserWarning,
            stacklevel=2,
        )
        raw_force_xyz = np.zeros((n_samples, 3))

    if raw_accel_xyz is None:
        warnings.warn(
            f"Dataset '{cfg.hdf5_accel_xyz}' not found; filling with zeros",
            UserWarning,
            stacklevel=2,
        )
        raw_accel_xyz = np.zeros((n_samples, 3))

    if raw_timestamps is None:
        warnings.warn(
            f"Dataset '{cfg.hdf5_timestamps}' not found; "
            f"generating synthetic timestamps at {1 / _FALLBACK_DT:.0f} Hz",
            UserWarning,
            stacklevel=2,
        )
        raw_timestamps = np.arange(n_samples) * _FALLBACK_DT

    if raw_torque_xyz is None:
        warnings.warn(
            f"Dataset '{cfg.hdf5_torque_xyz}' not found; filling with zeros",
            UserWarning,
            stacklevel=2,
        )
        raw_torque_xyz = np.zeros_like(raw_force_xyz)

    return SandingSession(
        force_xyz=raw_force_xyz,
        torque_xyz=raw_torque_xyz,
        accel_xyz=raw_accel_xyz,
        position_xyz=position_xyz,
        orientation=orientation,
        timestamps=raw_timestamps,
    )
