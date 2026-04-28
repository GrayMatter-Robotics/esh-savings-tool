"""Jurisdiction adapter registry and factory."""

from typing import Protocol

from esh_savings.models.features import ExposureFeatures
from esh_savings.pipeline.standards.jurisdictions.us import USAdapter


class JurisdictionAdapter(Protocol):
    name: str
    hav_eav: float
    hav_elv: float

    def compliance_flags(self, features: ExposureFeatures) -> dict[str, bool]: ...
    def regulatory_cost(self, features: ExposureFeatures) -> float: ...


REGISTRY: dict[str, type] = {
    "US": USAdapter,
}


def get_adapter(jurisdiction: str) -> JurisdictionAdapter:
    """Return an adapter instance for the given jurisdiction name."""
    cls = REGISTRY.get(jurisdiction.upper())
    if cls is None:
        raise ValueError(f"Unknown jurisdiction '{jurisdiction}'. Available: {list(REGISTRY)}")
    return cls()
