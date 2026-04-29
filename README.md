# esh-savings

Quantifies ESH (Environment, Safety & Health) dollar savings of robot sanding vs. manual, grounded in ISO 5349-1, Moore & Garg SI, and OSHA standards.

## Install

```bash
uv venv && uv pip install -e ".[all]"
```

## Run the dashboard

```bash
esh-savings serve
# open http://127.0.0.1:8000
```

Options:
```bash
esh-savings serve --host 0.0.0.0 --port 8080 --reload
```

## Run the pipeline from Python

```python
from pathlib import Path
from esh_savings.pipeline.ingestion import load_session
from esh_savings.pipeline import Pipeline
from esh_savings.models.config import AnalysisConfig
from esh_savings.models.se_inputs import SEProvidedInputs
from esh_savings.pipeline.standards.jurisdictions.us import USAdapter

session = load_session(Path("session.hdf5"))
result = Pipeline(
    config=AnalysisConfig(include_vibration=True, include_force=True),
    se_inputs=SEProvidedInputs(operator_count=10),
    adapter=USAdapter(),
).run(session)

print(f"Annual savings: ${result.annual_esh_savings_usd:,.0f}")
print(f"ESH risk reduction: {result.risk_reduction_pct:.1f}%")
```

## Export results

```python
from esh_savings.reporting.json import result_to_json
from esh_savings.reporting.excel import result_to_excel

# JSON
print(result_to_json(result))

# Excel workbook (3 sheets: Summary, Exposure, Assumptions)
Path("report.xlsx").write_bytes(result_to_excel(result))
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/upload` | Upload `.hdf5` file → `{"session_id": "..."}` |
| `POST` | `/compute` | Run pipeline → ESH result JSON |
| `GET` | `/report/{id}` | Retrieve cached result |
| `GET` | `/excel/{id}` | Download Excel report |

### `/compute` request body

```json
{
  "session_id": "...",
  "analysis_config": {
    "include_vibration": true,
    "include_force": true,
    "include_orientation": false
  },
  "se_inputs": {
    "operator_count": 10,
    "shift_duration_s": 28800
  },
  "jurisdiction": "US"
}
```

## Tests

```bash
# all tests
.venv/bin/pytest tests/ -v

# single module
.venv/bin/pytest tests/test_pipeline.py -v
```

## HDF5 file format

Required datasets: `timestamps` (s), `force_xyz` (N, 3-col), `accel_xyz` (m/s², 3-col)  
Optional: `torque_xyz` (N·m, 3-col), `position_xyz` (m, 3-col), `orientation` (quaternion, 4-col)
