import h5py
import numpy as np
import pytest


@pytest.fixture(scope="session")
def sample_hdf5_path(tmp_path_factory):
    """
    Synthetic HDF5 session: 100 s at 20 Hz.
    Vibration is high in the middle 60 s (active sanding window).
    Fz shows ~80 N push force during the active window.
    """
    rng = np.random.default_rng(42)
    n = 2_000
    t = np.linspace(0.0, 100.0, n)
    active = (t >= 20.0) & (t <= 80.0)

    accel = np.zeros((n, 3))
    accel[active]  = rng.normal(0, 4.0,  (active.sum(), 3))   # ~4 m/s² during sanding
    accel[~active] = rng.normal(0, 0.05, ((~active).sum(), 3)) # near-zero idle

    force = np.zeros((n, 3))
    force[active, 2]  = rng.normal(80, 15, active.sum())   # ~80 N Fz during sanding
    force[~active, 2] = rng.normal(3, 1, (~active).sum())  # minimal idle force

    torque = rng.normal(0, 2, (n, 3))
    position = rng.uniform(0, 500, (n, 3))

    quats = rng.normal(0, 1, (n, 4))
    quats /= np.linalg.norm(quats, axis=1, keepdims=True)

    p = tmp_path_factory.mktemp("fixtures") / "test_session.hdf5"
    with h5py.File(p, "w") as f:
        f.create_dataset("timestamps", data=t)
        f.create_dataset("force/xyz", data=force)
        f.create_dataset("force/torque_xyz", data=torque)
        f.create_dataset("imu/accel_xyz", data=accel)
        f.create_dataset("position/xyz", data=position)
        f.create_dataset("imu/orientation", data=quats)
    return p
