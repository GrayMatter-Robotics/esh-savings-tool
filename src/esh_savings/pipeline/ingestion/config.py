from pydantic import BaseModel


class IngestionConfig(BaseModel):
    """HDF5 dataset paths and MCAP topic names. Override for non-HSPI recorders."""

    # HDF5 (default HSPI paths)
    hdf5_timestamps:   str = "timestamps"
    hdf5_force_xyz:    str = "force/xyz"
    hdf5_torque_xyz:   str = "force/torque_xyz"
    hdf5_accel_xyz:    str = "imu/accel_xyz"
    hdf5_position_xyz: str = "position/xyz"
    hdf5_orientation:  str = "imu/orientation"

    # MCAP topic names (Phase 2)
    mcap_force_torque: str = "/force_torque"
    mcap_imu:          str = "/imu/data"
    mcap_position:     str = "/position"
    mcap_orientation:  str = "/orientation"
