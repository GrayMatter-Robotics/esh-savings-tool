import io
import json
import pytest
from fastapi.testclient import TestClient
from esh_savings.api.app import app
from esh_savings.api.routes import compute as compute_module


@pytest.fixture(autouse=True)
def _clear_api_state():
    compute_module._sessions.clear()
    compute_module._results.clear()
    yield
    compute_module._sessions.clear()
    compute_module._results.clear()


client = TestClient(app)


def test_root_returns_dashboard(sample_hdf5_path):
    r = client.get("/")
    assert r.status_code == 200
    assert "ESH Savings" in r.text


def test_upload_returns_session_id(sample_hdf5_path):
    with open(sample_hdf5_path, "rb") as f:
        r = client.post("/upload", files={"file": ("test.hdf5", f, "application/octet-stream")})
    assert r.status_code == 200
    data = r.json()
    assert "session_id" in data


def test_compute_returns_esh_result(sample_hdf5_path):
    with open(sample_hdf5_path, "rb") as f:
        upload = client.post("/upload", files={"file": ("test.hdf5", f, "application/octet-stream")})
    session_id = upload.json()["session_id"]

    r = client.post("/compute", json={
        "session_id": session_id,
        "analysis_config": {"include_vibration": True, "include_force": True, "include_orientation": False},
        "se_inputs": {"operator_count": 3},
    })
    assert r.status_code == 200
    body = r.json()
    assert "esh_risk_score_manual" in body
    assert body["annual_esh_savings_usd"] > 0


def test_report_returns_cached_result(sample_hdf5_path):
    with open(sample_hdf5_path, "rb") as f:
        upload = client.post("/upload", files={"file": ("test.hdf5", f, "application/octet-stream")})
    session_id = upload.json()["session_id"]
    client.post("/compute", json={"session_id": session_id, "se_inputs": {"operator_count": 1}})

    r = client.get(f"/report/{session_id}")
    assert r.status_code == 200


def test_excel_download_returns_xlsx(sample_hdf5_path):
    with open(sample_hdf5_path, "rb") as f:
        upload = client.post("/upload", files={"file": ("test.hdf5", f, "application/octet-stream")})
    session_id = upload.json()["session_id"]
    client.post("/compute", json={"session_id": session_id, "se_inputs": {"operator_count": 1}})

    r = client.get(f"/excel/{session_id}")
    assert r.status_code == 200
    assert "spreadsheetml" in r.headers["content-type"]


def test_compute_unknown_session_returns_404():
    r = client.post("/compute", json={"session_id": "nonexistent", "se_inputs": {"operator_count": 1}})
    assert r.status_code == 404


def test_report_unknown_session_returns_404():
    r = client.get("/report/nonexistent")
    assert r.status_code == 404


def test_excel_unknown_session_returns_404():
    r = client.get("/excel/nonexistent")
    assert r.status_code == 404
