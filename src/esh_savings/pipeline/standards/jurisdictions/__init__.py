from esh_savings.pipeline.standards.jurisdictions.us import USAdapter

REGISTRY: dict[str, type] = {
    "US": USAdapter,
}


def get_adapter(jurisdiction: str):
    """Return an adapter instance for the given jurisdiction name."""
    cls = REGISTRY.get(jurisdiction.upper())
    if cls is None:
        raise ValueError(f"Unknown jurisdiction '{jurisdiction}'. Available: {list(REGISTRY)}")
    return cls()
