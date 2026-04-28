"""FastAPI route handlers for upload, compute, report, and excel endpoints."""
import io
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

from esh_savings.pipeline.ingestion import load_session
from esh_savings.pipeline import Pipeline
from esh_savings.models.config import AnalysisConfig
from esh_savings.models.se_inputs import SEProvidedInputs
from esh_savings.pipeline.standards.jurisdictions import get_adapter
from esh_savings.reporting.json import result_to_dict
from esh_savings.reporting.excel import result_to_excel

router = APIRouter()

_sessions: dict[str, Path] = {}   # session_id → temp file path
_results:  dict[str, Any]  = {}   # session_id → ESHResult


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    session_id = str(uuid.uuid4())
    suffix = Path(file.filename or "upload.hdf5").suffix
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(await file.read())
    tmp.close()
    _sessions[session_id] = Path(tmp.name)
    return {"session_id": session_id}


@router.post("/compute")
async def compute_endpoint(body: dict):
    session_id = body.get("session_id")
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found. Upload a file first.")

    config     = AnalysisConfig(**body.get("analysis_config", {}))
    se_inputs  = SEProvidedInputs(**body.get("se_inputs", {"operator_count": 1}))
    adapter    = get_adapter(body.get("jurisdiction", "US"))

    session = load_session(_sessions[session_id])
    result  = Pipeline(config, se_inputs, adapter).run(session)
    _results[session_id] = result
    tmp_path = _sessions.pop(session_id)  # remove from session store
    os.unlink(tmp_path)                    # delete temp file
    return result_to_dict(result)


@router.get("/report/{session_id}")
async def get_report(session_id: str):
    if session_id not in _results:
        raise HTTPException(status_code=404, detail="Result not found. Run /compute first.")
    return result_to_dict(_results[session_id])


@router.get("/excel/{session_id}")
async def get_excel(session_id: str):
    if session_id not in _results:
        raise HTTPException(status_code=404, detail="Result not found. Run /compute first.")
    wb_bytes = result_to_excel(_results[session_id])
    filename = f"esh-savings-{session_id[:8]}.xlsx"
    return StreamingResponse(
        io.BytesIO(wb_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
