"""FastAPI application for ESH Savings Calculator."""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

from esh_savings.api.routes.compute import router as compute_router

app = FastAPI(title="ESH Savings Calculator", version="0.1.0")
app.include_router(compute_router)

_templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.get("/")
async def dashboard(request: Request):
    return _templates.TemplateResponse(request=request, name="dashboard.html")
