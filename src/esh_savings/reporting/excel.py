"""Excel workbook serialization for ESHResult pipeline output.

Produces a three-sheet workbook:
  Summary     — headline KPIs and Y1–Y5 cost forecast table
  Exposure    — vibration / force exposure metrics
  Assumptions — economic and configuration constants baked into the run
"""
import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from esh_savings.models.result import ESHResult
from esh_savings.constants.economics import (
    MANUAL_MSD_IR,
    ROBOT_MSD_IR,
    TOTAL_CLAIM_COST_USD,
    WAGE_INFLATION_RATE,
    ROBOT_LOAD_UNLOAD_FRACTION,
)
from esh_savings.constants.vibration import (
    SHIFT_DURATION_S,
    HAV_EAV,
    HAV_ELV,
)

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
_HEADER_FILL  = PatternFill("solid", fgColor="1F4E79")   # dark navy
_ALT_FILL     = PatternFill("solid", fgColor="D6E4F0")   # light blue
_HEADER_FONT  = Font(bold=True, color="FFFFFF", size=11)
_LABEL_FONT   = Font(bold=True, size=10)
_NORMAL_FONT  = Font(size=10)
_TITLE_FONT   = Font(bold=True, size=14, color="1F4E79")


def _set_col_widths(ws, widths: dict[str, float]) -> None:
    for col_letter, width in widths.items():
        ws.column_dimensions[col_letter].width = width


def _header_row(ws, row: int, labels: list[str]) -> None:
    for col_idx, label in enumerate(labels, start=1):
        cell = ws.cell(row=row, column=col_idx, value=label)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")


# ---------------------------------------------------------------------------
# Sheet writers
# ---------------------------------------------------------------------------

def _write_summary(ws, result: ESHResult) -> None:
    ws.title = "Summary"
    _set_col_widths(ws, {"A": 32, "B": 18, "C": 18, "D": 18})

    # Title
    ws["A1"] = "ESH Savings Analysis — Summary"
    ws["A1"].font = _TITLE_FONT

    # KPI block
    kpi_rows = [
        ("ESH Risk Score (manual)",     result.esh_risk_score_manual,    "0–100"),
        ("ESH Risk Score (robot)",      result.esh_risk_score_robot,     "0–100"),
        ("Risk Reduction",              result.risk_reduction_pct,       "%"),
        ("Annual ESH Savings (USD)",    result.annual_esh_savings_usd,   "USD/yr"),
        ("Annual Injury Cost (manual)", result.annual_injury_cost_manual, "USD/yr"),
        ("Annual Injury Cost (robot)",  result.annual_injury_cost_robot,  "USD/yr"),
    ]

    _header_row(ws, 3, ["KPI", "Value", "Unit"])
    for i, (label, value, unit) in enumerate(kpi_rows, start=4):
        fill = _ALT_FILL if i % 2 == 0 else None
        for col, val in enumerate([label, value, unit], start=1):
            cell = ws.cell(row=i, column=col, value=val)
            cell.font = _NORMAL_FONT
            if fill:
                cell.fill = fill

    # Y1–Y5 forecast table
    forecast_start = 12
    ws.cell(row=forecast_start - 1, column=1, value="Y1–Y5 Injury Cost Forecast").font = _LABEL_FONT
    _header_row(ws, forecast_start, ["Year", "Manual Cost (USD)", "Robot Cost (USD)", "Annual Savings (USD)"])

    year_data = [
        (1, result.y1_cost_manual, result.y1_cost_robot),
        (2, result.y2_cost_manual, result.y2_cost_robot),
        (3, result.y3_cost_manual, result.y3_cost_robot),
        (4, result.y4_cost_manual, result.y4_cost_robot),
        (5, result.y5_cost_manual, result.y5_cost_robot),
    ]
    for i, (yr, manual, robot) in enumerate(year_data, start=forecast_start + 1):
        fill = _ALT_FILL if i % 2 == 0 else None
        for col, val in enumerate([yr, manual, robot, manual - robot], start=1):
            cell = ws.cell(row=i, column=col, value=val)
            cell.font = _NORMAL_FONT
            if fill:
                cell.fill = fill

    # 5-year cumulative
    cum_row = forecast_start + 6
    cumulative = sum(
        (m - r)
        for _, m, r in year_data
    )
    ws.cell(row=cum_row, column=1, value="5-Year Cumulative Savings (USD)").font = _LABEL_FONT
    ws.cell(row=cum_row, column=2, value=cumulative).font = Font(bold=True, size=10)


def _write_exposure(ws, result: ESHResult) -> None:
    ws.title = "Exposure"
    _set_col_widths(ws, {"A": 36, "B": 14, "C": 18, "D": 10})

    ws["A1"] = "Exposure Metrics"
    ws["A1"].font = _TITLE_FONT

    _header_row(ws, 2, ["Metric", "Provenance", "Value", "Unit"])

    # Rows: (label, provenance_tag, value, unit)
    # Row 3 is the section header; row 4 onward are data rows.
    # C4 must be a float — we use result.a8_vs_eav (A(8)/EAV ratio).
    rows = [
        ("--- Vibration ---",               "",           None,                        ""),
        ("A(8)/EAV ratio",                  "COMPUTED",   result.a8_vs_eav,            "ratio"),
        ("HAVS onset estimate",             "COMPUTED",   result.havs_onset_estimate,  "years"),
        ("A(8) exceeds EAV?",               "COMPUTED",   float(result.compliance_status.a8_exceeds_eav), "bool"),
        ("A(8) exceeds ELV?",               "COMPUTED",   float(result.compliance_status.a8_exceeds_elv), "bool"),
        ("--- Force / Strain Index ---",    "",           None,                        ""),
        ("SI hazardous?",                   "COMPUTED",   float(result.compliance_status.si_hazardous),   "bool"),
        ("Regulatory cost (annual USD)",    "COMPUTED",   result.compliance_status.regulatory_cost_annual_usd, "USD/yr"),
    ]

    start_row = 3
    for i, (label, prov, val, unit) in enumerate(rows, start=start_row):
        fill = _ALT_FILL if i % 2 == 0 else None
        is_section = label.startswith("---")

        label_cell = ws.cell(row=i, column=1, value=label)
        label_cell.font = Font(bold=True, size=10) if is_section else _NORMAL_FONT

        ws.cell(row=i, column=2, value=prov if not is_section else "").font = _NORMAL_FONT

        # Write actual value; None → placeholder dash
        cell_val = val if val is not None else "—"
        ws.cell(row=i, column=3, value=cell_val).font = _NORMAL_FONT

        ws.cell(row=i, column=4, value=unit).font = _NORMAL_FONT

        if fill:
            for col in range(1, 5):
                ws.cell(row=i, column=col).fill = fill


def _write_assumptions(ws, result: ESHResult) -> None:
    ws.title = "Assumptions"
    _set_col_widths(ws, {"A": 36, "B": 18, "C": 10})

    ws["A1"] = "Baked-in Assumptions"
    ws["A1"].font = _TITLE_FONT

    _header_row(ws, 1, ["Parameter", "Value", "Source"])

    assumption_rows = [
        ("Shift duration (s)",              SHIFT_DURATION_S,             "ISO/vibration.py"),
        ("HAV EAV (m/s²)",                  HAV_EAV,                      "ISO 5349-1"),
        ("HAV ELV (m/s²)",                  HAV_ELV,                      "ISO 5349-1"),
        ("Manual MSD IR (per 10k FTE)",     MANUAL_MSD_IR,                "BLS SOII 2022"),
        ("Robot MSD IR (per 10k FTE)",      ROBOT_MSD_IR,                 "Midpoint estimate"),
        ("Total claim cost (USD)",          TOTAL_CLAIM_COST_USD,         "NCCI 2022-23"),
        ("Wage inflation rate",             WAGE_INFLATION_RATE,          "Default"),
        ("Robot load/unload fraction",      ROBOT_LOAD_UNLOAD_FRACTION,   "Default"),
    ]

    for i, (label, value, source) in enumerate(assumption_rows, start=2):
        fill = _ALT_FILL if i % 2 == 0 else None
        for col, val in enumerate([label, value, source], start=1):
            cell = ws.cell(row=i, column=col, value=val)
            cell.font = _NORMAL_FONT
            if fill:
                cell.fill = fill


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def result_to_excel(result: ESHResult) -> bytes:
    """Serialize an ESHResult to an Excel workbook (.xlsx) as raw bytes."""
    wb = Workbook()

    # openpyxl creates one default sheet; use it for Summary then add the rest
    ws_summary = wb.active
    _write_summary(ws_summary, result)

    ws_exposure = wb.create_sheet()
    _write_exposure(ws_exposure, result)

    ws_assumptions = wb.create_sheet()
    _write_assumptions(ws_assumptions, result)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
