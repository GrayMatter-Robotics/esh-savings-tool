from pathlib import Path

from esh_savings.models.session import SandingSession
from esh_savings.pipeline.ingestion.config import IngestionConfig


def load_session(path: str | Path, config: IngestionConfig | None = None) -> SandingSession:
    """Auto-detect file format by extension and return a SandingSession."""
    p = Path(path)
    suffix = p.suffix.lower()

    if suffix in (".hdf5", ".h5"):
        from esh_savings.pipeline.ingestion.hdf5_reader import read_hdf5
        return read_hdf5(p, config)
    elif suffix == ".mcap":
        raise NotImplementedError("MCAP reader not available in Phase 1. Install esh-savings[mcap].")
    elif suffix == ".rrd":
        raise NotImplementedError("RRD reader not available in Phase 1. Install esh-savings[rerun].")
    else:
        raise ValueError(f"Unsupported file format: '{suffix}'. Supported: .hdf5, .h5")
