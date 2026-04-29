import h5py
import numpy as np
from pathlib import Path

def generate_sample_hdf5(output_path="sample_session.hdf5"):
    rng = np.random.default_rng(42)
    n = 2_000
    t = np.linspace(0.0, 100.0, n)
    active = (t >= 20.0) & (t <= 80.0)

    accel = np.zeros((n, 3))
    accel[active]  = rng.normal(0, 4.0,  (active.sum(), 3))
    accel[~active] = rng.normal(0, 0.05, ((~active).sum(), 3))

    force = np.zeros((n, 3))
    force[active, 2]  = rng.normal(80, 15, active.sum())
    force[~active, 2] = rng.normal(3, 1, (~active).sum())

    torque = rng.normal(0, 2, (n, 3))
    position = rng.uniform(0, 500, (n, 3))
    quats = rng.normal(0, 1, (n, 4))
    quats /= np.linalg.norm(quats, axis=1, keepdims=True)

    with h5py.File(output_path, "w") as f:
        f.create_dataset("timestamps", data=t)
        f.create_dataset("force/xyz", data=force)
        f.create_dataset("force/torque_xyz", data=torque)
        f.create_dataset("imu/accel_xyz", data=accel)
        f.create_dataset("position/xyz", data=position)
        f.create_dataset("imu/orientation", data=quats)
    
    print(f"✓ Generated synthetic data: {output_path}")

if __name__ == "__main__":
    generate_sample_hdf5()
