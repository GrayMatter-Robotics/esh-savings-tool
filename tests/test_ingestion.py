import numpy as np
from esh_savings.pipeline.ingestion import load_session
from esh_savings.models.session import SandingSession


def test_load_hdf5_returns_sanding_session(sample_hdf5_path):
    session = load_session(sample_hdf5_path)
    assert isinstance(session, SandingSession)


def test_load_hdf5_channels_have_correct_shape(sample_hdf5_path):
    session = load_session(sample_hdf5_path)
    n = len(session.timestamps)
    assert session.force_xyz.shape  == (n, 3)
    assert session.torque_xyz.shape == (n, 3)
    assert session.accel_xyz.shape  == (n, 3)


def test_load_hdf5_optional_channels_loaded(sample_hdf5_path):
    session = load_session(sample_hdf5_path)
    assert session.position_xyz is not None
    assert session.orientation is not None
    assert session.orientation.shape[1] == 4


def test_load_hdf5_timestamps_monotonic(sample_hdf5_path):
    session = load_session(sample_hdf5_path)
    assert np.all(np.diff(session.timestamps) > 0)


def test_unsupported_format_raises():
    import pytest
    with pytest.raises(ValueError, match="Unsupported"):
        load_session("file.bag")


def test_missing_torque_fills_zeros_with_warning(tmp_path):
    """HDF5 without torque_xyz dataset should fill zeros and emit UserWarning."""
    import h5py
    import pytest

    rng = np.random.default_rng(0)
    n = 100
    t = np.linspace(0.0, 10.0, n)
    p = tmp_path / "no_torque.hdf5"
    with h5py.File(p, "w") as f:
        f.create_dataset("timestamps", data=t)
        f.create_dataset("force/xyz", data=rng.normal(0, 10, (n, 3)))
        f.create_dataset("imu/accel_xyz", data=rng.normal(0, 1, (n, 3)))

    with pytest.warns(UserWarning, match="not found"):
        session = load_session(p)

    assert np.all(session.torque_xyz == 0.0)
    assert session.torque_xyz.shape == (n, 3)
