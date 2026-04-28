"""JSON serialization for ESHResult pipeline output."""
import json
from esh_savings.models.result import ESHResult


def result_to_dict(result: ESHResult) -> dict:
    return result.model_dump(mode="json")


def result_to_json(result: ESHResult) -> str:
    return json.dumps(result_to_dict(result), indent=2)
