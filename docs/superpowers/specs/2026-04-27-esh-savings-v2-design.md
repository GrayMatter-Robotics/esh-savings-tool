# ESH Savings — System Design v2.0

> Quantify the Environment, Safety & Health dollar savings of deploying robot sanding versus continued human manual sanding — grounded in published ergonomic standards, industry injury cost data, and customer-provided injury history.
> `pip install esh-savings && esh-savings serve`

**Date:** 2026-04-27
**PRD Reference:** ESH Savings Model — PRD v2.0 (April 2026)
**Status:** Approved for implementation

---

## 1. Problem Statement

Solutions Engineers need a credible, defensible dollar figure for the ESH savings that a GrayMatter robot sanding cell delivers. Today this number either doesn't appear in proposals or is estimated informally, weakening the business case.

- **No quantified ESH savings** — Proposals lack a per-operator, per-year injury cost estimate backed by published standards.
- **Compliance risk is invisible** — Manual sanding regularly exceeds OSHA/ISO vibration and force thresholds; SEs have no tool to show this to customers.
- **Unauditable estimates** — Ad-hoc spreadsheets mix validated figures with guesses and don't distinguish between them, creating liability if challenged.
- **Multi-jurisdiction gap** — US, EU, and UK have different thresholds and legal consequences; a single-jurisdiction tool leaves revenue on the table.

`esh-savings` solves these problems by running recorded sensor data through a five-stage pipeline that computes ergonomic risk scores, monetizes the risk delta (manual minus robot), and produces a jurisdiction-aware dynamic Excel workbook with full provenance on every number.

---

## 2. Design Principles

1. **Sensor-agnostic core** — The pipeline operates on a normalized `SandingSession` model; format-specific details (HDF5, MCAP, RRD) stay in ingestion adapters.

2. **Jurisdiction-pluggable** — Standards evaluation is parameterized by a `JurisdictionAdapter` protocol. Adding EU or UK support means writing one adapter file without touching the core pipeline.

3. **Assumption-transparent** — Every computed value carries a `ProvenanceTag` (MEASURED / COMPUTED / DEFAULT / ESTIMATED). ESTIMATED values surface as visible warnings in both the UI and Excel Sheet 5.

4. **Standards-traceable** — No threshold, cost, or coefficient is a magic number. Every constant in `constants/` cites its source standard and publication year.

5. **Override-friendly defaults** — All `[D]` defaults are named constants overridable through the web UI and directly in the Excel workbook (Sheet 5 input cells).

6. **Offline-first** — The full pipeline runs on pre-recorded session files. No live sensor connection is required. SEs can run this from a laptop in a customer meeting.

7. **Customer-anchored costs** — SE-provided injury history and WC costs replace BLS population statistics as the primary cost calibration anchor when available.

8. **Analysis-configurable** — SEs select which sensor channels to include per run (vibration, force, orientation). Excluded channels render as "Not analysed" in the Excel; the ESH score renormalizes across included components.

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                   Solutions Engineers (Browser)                      │
│   Upload file · Set jurisdiction · Select data types                 │
│   Enter SE inputs · Override constants · Download Excel              │
├─────────────────────────────────────────────────────────────────────┤
│                    esh-savings  (Python package)                     │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │                        API Layer                                │ │
│ │   api/   FastAPI  —  /upload  /compute  /report  /excel         │ │
│ │                      /customers  /calibration  /feedback        │ │
│ ├─────────────────────────────────────────────────────────────────┤ │
│ │                    Intelligence Layer                           │ │
│ │   provenance/    calibration/    feedback/    audit/            │ │
│ ├─────────────────────────────────────────────────────────────────┤ │
│ │                    Reporting Layer                              │ │
│ │   reporting/json.py              reporting/excel.py  (5 sheets) │ │
│ ├─────────────────────────────────────────────────────────────────┤ │
│ │              Pipeline Orchestrator                              │ │
│ │   pipeline.py — Pipeline(config, se_inputs, adapter).run()      │ │
│ ├─────────────────────────────────────────────────────────────────┤ │
│ │                 Core Pipeline  (5 Stages)                       │ │
│ │  ingestion/  features/  standards/  cost_calibration/  savings/ │ │
│ ├─────────────────────────────────────────────────────────────────┤ │
│ │                       Foundation                                │ │
│ │   models/  (Pydantic v2)     constants/  ([V][D][E] tagged)     │ │
│ └─────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│                          Infrastructure                              │
│  .hdf5 · .mcap · .rrd  ·  h5py · mcap · rerun-sdk (≥ 0.16)         │
│  NumPy · SciPy · Pydantic v2 · FastAPI · Jinja2 · openpyxl          │
│  SQLite  (calibration store + customer table + audit log)            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Components

### 4.1 Foundation

#### `models/`

All data contracts between pipeline stages as Pydantic v2 models. Nothing flows between stages as a raw dict or array.

**`models/session.py` — `SandingSession`**

Normalized sensor time-series for one pass (one operator + one sander + one part).

```python
class SandingSession(BaseModel):
    force_xyz:      np.ndarray   # [timestamps × 3], N
    torque_xyz:     np.ndarray   # [timestamps × 3], Nm
    accel_xyz:      np.ndarray   # [timestamps × 3], m/s² (vibration)
    position_xyz:   np.ndarray | None  # [timestamps × 3], mm — ingested but not analysed
    orientation:    np.ndarray | None  # [timestamps × 4], quaternion (w,x,y,z)
    timestamps:     np.ndarray   # [timestamps], s
    metadata:       SessionMetadata    # material, jurisdiction, se_id
```

`position_xyz` is ingested from the file if present but not used in any pipeline computation (face segmentation removed). `orientation` drives arm elevation and wrist pronation when `include_orientation = True`.

**`models/features.py` — `ExposureFeatures`**

```python
class ExposureFeatures(BaseModel):
    # Vibration (None when include_vibration = False)
    ahv:            float | None   # frequency-weighted RMS, m/s²
    a8:             float | None   # daily normalized dose, m/s²
    # Force (None when include_force = False)
    hal:            float | None   # Hand Activity Level
    fz_mean:        float | None   # N
    fz_p50:         float | None   # N
    fz_p90:         float | None   # N
    duty_cycle:     float | None   # 0–1
    repetition_rate: float | None  # actions/min
    si_factors:     SIFactors | None
    # Orientation (None when include_orientation = False)
    arm_elevation_deg:   float | None  # [D] from tool axis pitch
    wrist_pronation_deg: float | None  # [D] from roll around tool axis
```

**`models/scores.py` — `RiskScores`**

Fields are `None` when the corresponding `AnalysisConfig` flag is `False`. The ESH composite score in Stage 5 renormalizes across non-None components.

**`models/result.py` — `ESHResult`**

```python
class ESHResult(BaseModel):
    esh_risk_score_manual:          float
    esh_risk_score_robot:           float
    risk_reduction_pct:             float
    annual_injury_cost_manual:      float
    annual_injury_cost_robot:       float
    emr_savings_annual_usd:         float
    absenteeism_savings_annual_usd: float
    annual_esh_savings_usd:         float   # = injury delta + EMR + absenteeism
    y1_cost_manual:  float;  y1_cost_robot:  float
    y2_cost_manual:  float;  y2_cost_robot:  float
    y3_cost_manual:  float;  y3_cost_robot:  float
    y4_cost_manual:  float;  y4_cost_robot:  float
    y5_cost_manual:  float;  y5_cost_robot:  float
    compliance_status:      ComplianceStatus
    havs_onset_estimate:    float | None
    payback_contribution_years: float
    provenance_map: dict[str, ProvenanceTag]
```

**`models/config.py` — `AnalysisConfig`**

```python
class AnalysisConfig(BaseModel):
    include_vibration:   bool = True
    include_force:       bool = True
    include_orientation: bool = True
```

Disabled components are excluded from the ESH composite score (which renormalizes to 100 across enabled components) and render as "Not analysed" in Excel.

**`models/se_inputs.py` — `SEProvidedInputs`**

```python
class SEProvidedInputs(BaseModel):
    customer_id:            str
    operator_count:         int
    injury_history:         dict[int, int]   # {year: injury_count}
    wc_cost_paid_usd:       float | None     # cumulative; None = use NCCI benchmark
    wc_base_premium_usd:    float | None     # annual; None = estimate from payroll
    shift_duration_s:       float = 28800
```

**`models/calibration_result.py` — `CostCalibration`**

```python
class CostCalibration(BaseModel):
    cost_per_claim_usd:             float
    calibration_source:             Literal["customer", "blend", "benchmark"]
    emr_savings_annual_usd:         float
    absenteeism_cost_annual_usd:    float
    exposure_history_mismatch:      bool
```

#### `constants/`

All numeric thresholds, coefficients, and cost figures as named Python constants with source citations.

**New constants in `constants/economics.py`:**

| Constant | Value | Unit | Tag | Source |
|---|---|---|---|---|
| `WAGE_INFLATION_RATE` | 0.03 | /yr | `[D]` | SE-adjustable; standard US wage growth assumption |
| `EMR_DELTA_ESTIMATE` | 0.15 | — | `[E]` | Midpoint of 0.10–0.20 range; no sanding-robot-specific EMR study |
| `ABSENTEEISM_OT_MULT` | 1.5 | — | `[V]` | OT coverage multiplier (FBLR × 1.5); standard overtime rate |
| `FBLR_DEFAULT_USD` | 35.0 | USD/hr | `[D]` | Fully burdened labor rate; override with customer rate |
| `NCCI_WC_RATE_PER_100` | 4.35 | USD/100 | `[D]` | Class code 3632 midpoint ($3.50–$5.20); used when base premium not provided |

---

### 4.2 Pipeline Orchestrator

#### `pipeline.py`

Single entry point for the pipeline. Owns `AnalysisConfig` and `SEProvidedInputs`. Stage 1 (ingestion) is called by the API layer before constructing the `Pipeline`, keeping file I/O and validation separate from computation.

```python
class Pipeline:
    def __init__(
        self,
        config: AnalysisConfig,
        se_inputs: SEProvidedInputs,
        adapter: JurisdictionAdapter,
    ): ...

    def run(self, session: SandingSession) -> ESHResult:
        features    = self._stage2_features(session)
        scores      = self._stage3_standards(features)
        calibration = self._stage4_cost_calibration(scores)
        result      = self._stage5_savings(scores, calibration)
        return result
```

Each `_stageN` method checks `self.config` before computing a component. Fields that are skipped are set to `None` on the output model — never to zero.

---

### 4.3 Core Pipeline

#### Stage 1 — Ingestion (`ingestion/`)

Reads a raw session file and produces a `SandingSession`. All five channel groups (force XYZ, torque XYZ, vibration XYZ, position XYZ, orientation) are read from the same file. `AnalysisConfig` does not affect what the reader attempts — it loads everything present. Missing channels set the corresponding field to `None` and emit a warning; the `Pipeline` then forces the matching `AnalysisConfig` flag to `False` for that run.

```python
session = load_session("run.hdf5")   # auto-detects format; loads all available channels
```

Readers:
- `hdf5_reader.py` — HSPI HDF5; expects `force/xyz`, `imu/accel_xyz`, `position/xyz`, `imu/orientation`, `timestamps`
- `mcap_reader.py` — MCAP container; expects `/force_torque`, `/imu/data`, `/position`, `/orientation` topics
- `rrd_reader.py` — Rerun `.rrd` via `rerun-sdk ≥ 0.16`; maps entity paths to all five channel groups

All readers resample all channels to a common timestamp grid (linear interpolation).

#### Stage 2 — Feature Extraction (`features/extractor.py`)

Derives ergonomic exposure parameters from `SandingSession` per `AnalysisConfig`. Fields not enabled by config are `None` in the output.

**Vibration-gated:**
- Active-sanding window detection via vibration RMS threshold
- `ahv = √(awx² + awy² + awz²)` — frequency-weighted RMS per ISO 8041-1
- `A(8) = ahv × √(T / SHIFT_DURATION_S)` — daily normalized dose per ISO 5349-1

**Force-gated:**
- Push force percentiles (mean, P50, P90) from Fz time-series
- HAL from duty cycle and repetition rate (ACGIH TLV Booklet)
- Strain Index factors — `%MVC` from Fz, duty cycle, repetition rate from signal envelope

**Orientation-gated:**
- `arm_elevation_deg` — `arcsin(R @ [0,0,1])[2] × 180/π`; tool axis pitch in world frame; RULA upper arm proxy `[D]`
- `wrist_pronation_deg` — roll component around tool axis; RULA wrist twist proxy `[D]`
- Remaining RULA inputs (lower arm, wrist flexion/extension, neck, trunk, leg) use fixed default posture `[E]`

No face segmentation. No position-based computation. `position_xyz` on `SandingSession` is not read by the feature extractor.

#### Stage 3 — Standards Evaluation (`standards/evaluator.py`)

Applies jurisdiction-specific thresholds to `ExposureFeatures`. Returns `RiskScores`. Fields that are `None` in `ExposureFeatures` produce `None` risk scores.

**Key computations:**
- Vibration: A(8) vs. EAV and ELV; compliance margin as % below/above threshold
- HAVS onset: `Dy(10%) = 31.8 × A(8)^-1.06` (ISO 5349-1 Annex C)
- SI: multiplied across all 6 factors; SI ≥ 7 flagged hazardous
- RULA: sensor-derived arm elevation and wrist pronation combined with fixed defaults for remaining joints
- US regulatory cost: `P(inspection) × P(citation|inspection) × E(penalty)`
- EU/UK regulatory cost: binary flag (above ELV = exposure prohibited)

#### Stage 4 — Cost Calibration (`cost_calibration/calibrator.py`) — NEW

Anchors expected injury cost to SE-provided customer history.

**Cost-per-claim derivation:**
- ≥ 2 years of SE history: `cost_per_claim = wc_cost_paid / total_injuries` → source = "customer"
- < 2 years: 70% NCCI $55K + 30% customer-derived → source = "blend"
- No history: pure NCCI $55K benchmark → source = "benchmark"

**EMR savings:**
- `emr_savings = EMR_DELTA_ESTIMATE × wc_base_premium`
- If `wc_base_premium` not provided: estimated as `operator_count × FBLR_DEFAULT_USD × 2080 / 100 × NCCI_WC_RATE_PER_100`

**Absenteeism cost:**
- `absenteeism = injuries_per_year × MEDIAN_DAYS_AWAY × FBLR_DEFAULT_USD × ABSENTEEISM_OT_MULT`
- Computed separately for manual and robot scenarios

**Mismatch flag:**
- `exposure_history_mismatch = True` when `measured_a8 < HAV_EAV` AND `si_score < STRAIN_INDEX_HAZARD` AND `customer_injuries_per_year > 2`
- Surfaces as a warning banner in Excel Sheet 4

#### Stage 5 — Savings & Forecast (`savings/calculator.py`)

Monetizes the risk delta and produces `ESHResult`.

**ESH composite score (renormalized across enabled components):**
```
score = Σ(weight_i × score_i for enabled_i) / Σ(weight_i for enabled_i) × 100
```
Default weights: vibration 40%, force 30%, posture/RULA 30%.

**Annual savings:**
```
annual_esh_savings = injury_cost_delta + emr_savings_annual + absenteeism_savings_annual
```

**Y1/Y2/Y5 forecast:**
```
cost_yN_manual = base_manual_cost × (1 + WAGE_INFLATION_RATE)^N
cost_yN_robot  = base_robot_cost  × (1 + WAGE_INFLATION_RATE)^N
```
Three cost lines projected separately: injury claim cost, EMR premium component, absenteeism cost.

---

### 4.4 Intelligence Layer

#### `intelligence/calibration.py`

SQLite store extended with a `customers` table:

```sql
CREATE TABLE customers (
    customer_id         TEXT PRIMARY KEY,
    operator_count      INTEGER,
    injury_history      TEXT,    -- JSON: {"2023": 3, "2024": 2}
    wc_cost_paid_usd    REAL,
    wc_base_premium_usd REAL,
    shift_duration_s    REAL DEFAULT 28800,
    updated_at          TEXT
);
```

Existing `constants` table (constant overrides) and `audit` table unchanged in structure.

#### `intelligence/audit.py`

Each run log row gains two new columns: `analysis_config_json` (flags active for this run) and `se_inputs_customer_id` (FK to `customers`). Ensures exact reproduction of any historical proposal.

#### `intelligence/provenance.py`

`arm_elevation_deg` and `wrist_pronation_deg` tag as `[D]` when orientation is enabled. Fixed-default RULA inputs tag as `[E]`. Unchanged otherwise.

#### `intelligence/feedback.py`

Unchanged.

---

### 4.5 Reporting Layer

#### `reporting/json.py`

Unchanged. Serializes `ESHResult` (including provenance map) to typed JSON dict. Handoff contract for Tool 2 (Reachability) and Tool 3 (Doability).

#### `reporting/excel.py` — replaces `pdf.py`

Generates a 5-sheet `openpyxl` workbook. **Dynamic with formulas** — the SE can change `[D]` input cells and the workbook recalculates without a pipeline re-run.

**Cell types:**
- **Input cells** (yellow fill, unlocked) — `[D]` constants in Sheet 5; SE actuals in Sheet 4 left side
- **Sensor cells** (grey fill, locked) — all pipeline-measured values in Sheet 3; cannot be edited
- **Formula cells** (white fill, locked) — Sheet 1, Sheet 2, Sheet 4 right side; Excel formulas referencing named ranges

**Named ranges** (examples):
```
SHIFT_DURATION_S     → Sheet5!B4
WAGE_INFLATION_RATE  → Sheet5!B5
FBLR_USD             → Sheet5!B6
INDIRECT_MULTIPLIER  → Sheet5!B7
OPERATOR_COUNT       → Sheet5!B8
EMR_DELTA            → Sheet5!B9
A8_AGGREGATE         → Sheet3!C4
SI_SCORE             → Sheet3!C8
COST_PER_CLAIM       → Sheet3!C12
```

**Sheet 1 — Summary**

Formula cells only. Pulls from Sheet 4 totals and Sheet 2 risk scores.

| Cell | Value |
|---|---|
| ESH Risk Score — Manual | `=Sheet2!risk_score_manual` |
| ESH Risk Score — Robot | `=Sheet2!risk_score_robot` |
| Risk Reduction % | `=(Manual - Robot) / Manual × 100` |
| Annual ESH Dollar Savings | `=Sheet4!annual_savings_y1` |
| 5-Year Cumulative Savings | `=Sheet4!y1+y2+y3+y4+y5` |
| ESH Savings as Payback Contribution | `=annual_savings / robot_system_cost` |

**Sheet 2 — Risk Detail**

Per injury type: description, risk score (formula from Sheet 3 values + Sheet 5 thresholds), RAG status, supporting metric, HAVS onset years. Disabled channels show grey fill + "Not analysed."

| Risk Type | Gated by |
|---|---|
| HAVS | `include_vibration` |
| Shoulder MSD | `include_force` |
| Wrist / Forearm | `include_force` |
| RULA | always shown; `[D]` source when `include_orientation`, else `[E]` |
| Regulatory compliance | `include_vibration` and/or `include_force` |

**Sheet 3 — Exposure Data**

Sensor-derived values written as static numbers (locked). These are measurements from the pipeline and cannot be changed in the workbook. Includes: `ahv`, `A(8)`, force percentiles (mean, P50, P90 Fz), HAL, duty cycle, repetition rate, `arm_elevation_deg`, `wrist_pronation_deg`, SI factor components.

**Sheet 4 — Cost History & Forecast**

Left side: SE-entered actuals (Y-3 → Y0) — editable input cells (yellow). Right side: Y1, Y2, Y5 projections as Excel formulas referencing Sheet 3 sensor values and Sheet 5 parameters.

Three cost lines per year: injury claim cost, EMR premium component, absenteeism cost.

If `exposure_history_mismatch = True`, a yellow warning banner at top: *"Measured exposure levels do not fully explain the reported claim history — review with customer before presenting."*

**Sheet 5 — Assumptions**

The parameter hub. Every constant used in this run.

| Constant type | Fill | Editable |
|---|---|---|
| `[V]` validated | Grey | Locked — cannot be changed |
| `[D]` default | Yellow | Unlocked — SE can override |
| `[E]` estimated | Orange | Unlocked — flagged "Estimate — verify before presenting" |

Also includes `AnalysisConfig` flags (which channels were active) and the `calibration_source` for cost-per-claim. Mandatory — cannot be deleted.

---

### 4.6 API Layer

#### `api/`

```
POST  /upload                  # multipart file upload → session_id
POST  /compute                 # session_id + jurisdiction + customer_id
                               #   + analysis_config + overrides → ESHResult JSON
GET   /report/{id}             # ESHResult JSON (Tool 2/3 handoff — unchanged)
GET   /excel/{id}              # Excel workbook download
GET   /customers               # list saved customers
POST  /customers               # create/update customer SE inputs
GET   /customers/{id}          # retrieve one customer
GET   /calibration             # current constant overrides
POST  /calibration             # save constant override
GET   /feedback                # proposal history + accuracy metrics
POST  /feedback/{id}           # mark Won/Lost/Pending
```

Dashboard additions:
1. **Customer selector** — SE picks or creates a customer before computing; loads saved SE inputs
2. **Analysis config panel** — three checkboxes (Vibration / Force / Orientation) with a warning if any channel is unchecked
3. Excel download button replaces PDF button

---

## 5. Pipeline Data Flow

```
Raw file (.hdf5 / .mcap / .rrd)
         │  all channels loaded (force, torque, vibration, position, orientation)
         ▼  ingestion/detector.py → correct reader
  SandingSession
    force_xyz, torque_xyz, accel_xyz  ← always loaded
    position_xyz                       ← loaded if present; not used in pipeline
    orientation                        ← loaded if present; used when include_orientation
         │
         ▼  Pipeline._stage2_features()   [AnalysisConfig gates each group]
  ExposureFeatures
    ahv, a8                  ← MEASURED   (vibration)
    fz_p50, fz_p90, hal      ← MEASURED   (force)
    si_factors               ← COMPUTED   (force)
    arm_elevation_deg        ← COMPUTED [D] (orientation)
    wrist_pronation_deg      ← COMPUTED [D] (orientation)
         │
         ▼  Pipeline._stage3_standards(features, adapter)
  RiskScores
    a8_vs_eav, a8_vs_elv     ← COMPUTED
    havs_onset_years         ← COMPUTED
    si_score                 ← COMPUTED
    rula_score               ← COMPUTED [D/E] (partial sensor, partial default)
    regulatory_cost          ← COMPUTED (US) / DEFAULT flag (EU/UK)
         │
         ▼  Pipeline._stage4_cost_calibration(scores, se_inputs)
  CostCalibration
    cost_per_claim_usd       ← customer / blend / benchmark
    emr_savings_annual_usd   ← COMPUTED [E]
    absenteeism_cost         ← COMPUTED [D]
    exposure_history_mismatch← flag
         │
         ▼  Pipeline._stage5_savings(scores, calibration)
  ESHResult                               provenance_map: dict[str, ProvenanceTag]
    esh_risk_score_manual/robot
    risk_reduction_pct
    annual_esh_savings_usd              ← injury delta + EMR + absenteeism
    y1/y2/y5 cost_manual / cost_robot   ← WAGE_INFLATION_RATE compounded
    compliance_status
    havs_onset_estimate
    payback_contribution_years
         │
         ├──▶  reporting/json.py  →  JSON dict (Tool 2 / Tool 3 handoff)
         └──▶  reporting/excel.py →  5-sheet workbook (dynamic, SE-editable)
```

---

## 6. Package Structure

```
esh-savings/
├── src/
│   └── esh_savings/
│       ├── __init__.py
│       ├── models/
│       │   ├── session.py               # SandingSession, SessionMetadata
│       │   ├── features.py              # ExposureFeatures, SIFactors
│       │   ├── scores.py                # RiskScores, ComplianceStatus
│       │   ├── result.py                # ESHResult, ProvenanceTag
│       │   ├── config.py                # AnalysisConfig
│       │   ├── calibration_result.py    # CostCalibration
│       │   └── se_inputs.py             # SEProvidedInputs
│       ├── constants/
│       │   ├── vibration.py             # HAV_EAV, HAV_ELV, SHIFT_DURATION_S, ...
│       │   ├── ergonomics.py            # SNOOK_PUSH_LIMIT_N, STRAIN_INDEX_HAZARD, ...
│       │   ├── economics.py             # DIRECT_CLAIM_COST_USD, MANUAL_MSD_IR,
│       │   │                            #   WAGE_INFLATION_RATE, EMR_DELTA_ESTIMATE,
│       │   │                            #   ABSENTEEISM_OT_MULT, FBLR_DEFAULT_USD,
│       │   │                            #   NCCI_WC_RATE_PER_100
│       │   └── regulatory.py            # OSHA_*, HSE_POINTS_*, ...
│       ├── pipeline/
│       │   ├── __init__.py              # Pipeline orchestrator class
│       │   ├── ingestion/
│       │   │   ├── detector.py          # auto-detect format from path/magic bytes
│       │   │   ├── hdf5_reader.py       # all 5 channel groups → SandingSession
│       │   │   ├── mcap_reader.py       # all 5 channel groups → SandingSession
│       │   │   ├── rrd_reader.py        # all 5 channel groups → SandingSession
│       │   │   └── config.py            # IngestionConfig (topic names, dataset paths)
│       │   ├── features.py              # SandingSession → ExposureFeatures
│       │   │                            #   (no face segmentation; position not used)
│       │   ├── standards/
│       │   │   ├── evaluator.py         # evaluate(features, adapter) → RiskScores
│       │   │   └── jurisdictions/
│       │   │       ├── __init__.py      # registry
│       │   │       ├── us.py            # USAdapter
│       │   │       ├── eu.py            # EUAdapter
│       │   │       └── uk.py            # UKAdapter
│       │   ├── cost_calibration.py      # SEProvidedInputs + RiskScores → CostCalibration
│       │   └── savings.py               # RiskScores + CostCalibration → ESHResult
│       ├── intelligence/
│       │   ├── provenance.py            # ProvenanceTag injection
│       │   ├── calibration.py           # SQLite: constants + customers tables
│       │   ├── feedback.py              # proposal outcome tracking
│       │   └── audit.py                 # append-only run log
│       ├── reporting/
│       │   ├── json.py                  # ESHResult → dict/JSON
│       │   └── excel.py                 # ESHResult → 5-sheet openpyxl workbook
│       └── api/
│           ├── app.py                   # FastAPI application
│           ├── routes/
│           │   ├── compute.py           # /upload, /compute, /report, /excel
│           │   ├── customers.py         # /customers GET/POST/GET{id}
│           │   ├── calibration.py       # /calibration GET/POST
│           │   └── feedback.py          # /feedback GET/POST
│           └── templates/
│               └── dashboard.html       # customer selector + analysis config panel
├── tests/
│   ├── test_ingestion.py
│   ├── test_features.py
│   ├── test_standards.py
│   ├── test_cost_calibration.py
│   ├── test_savings.py
│   ├── test_pipeline.py
│   └── fixtures/                        # sample .hdf5, .mcap, .rrd test files
├── pyproject.toml
└── README.md
```

---

## 7. Constants Reference

### Vibration — `constants/vibration.py`

| Constant | Value | Unit | Tag | Source |
|---|---|---|---|---|
| `HAV_EAV` | 2.5 | m/s² | `[V]` | ISO 5349-1:2001 §6.2; EU Dir 2002/44/EC |
| `HAV_ELV` | 5.0 | m/s² | `[V]` | ISO 5349-1:2001 §6.2; EU Dir 2002/44/EC |
| `SHIFT_DURATION_S` | 28 800 | s | `[D]` | Standard 8-hr shift; override to 36 000 or 43 200 |
| `HAVS_ONSET_COEFF` | 31.8 | — | `[V]` | ISO 5349-1:2001 Annex C |
| `HAVS_ONSET_EXP` | −1.06 | — | `[V]` | ISO 5349-1:2001 Annex C |
| `HSE_POINTS_EAV` | 100 | pts | `[V]` | UK Control of Vibration at Work Regs 2005 |
| `HSE_POINTS_ELV` | 400 | pts | `[V]` | UK Control of Vibration at Work Regs 2005 |

### Force Ergonomics — `constants/ergonomics.py`

| Constant | Value | Unit | Tag | Source |
|---|---|---|---|---|
| `SNOOK_PUSH_LIMIT_N` | 129 | N | `[V]` | Snook & Ciriello 1991 |
| `ISO_INITIAL_PUSH_N` | 250 | N | `[V]` | ISO 11228-2:2007 |
| `ISO_SUSTAINED_PUSH_N` | 150 | N | `[V]` | ISO 11228-2:2007 |
| `OCRA_VIBRATION_MULTIPLIER` | 0.80 | — | `[V]` | ISO 11228-3:2007 |
| `STRAIN_INDEX_HAZARD` | 7 | — | `[V]` | Moore & Garg 1995 |
| `RULA_DEFAULT_POSTURE_SCORE` | 3 | — | `[E]` | Fixed default for joints not derived from sensor |

### Injury Cost & Incidence — `constants/economics.py`

| Constant | Value | Unit | Tag | Source |
|---|---|---|---|---|
| `DIRECT_CLAIM_COST_USD` | 55 115 | USD | `[V]` | NCCI 2022–23; secondary benchmark only |
| `INDIRECT_MULTIPLIER` | 1.1 | — | `[V]` | OSHA Safety Pays |
| `TOTAL_CLAIM_COST_USD` | 115 000 | USD | `[V]` | = `DIRECT × (1 + INDIRECT_MULTIPLIER)` |
| `MANUAL_MSD_IR` | 41 | per 10 000 FTE | `[D]` | BLS SOII 2022; replaced by SE actuals when available |
| `ROBOT_MSD_IR` | 5 | per 10 000 FTE | `[E]` | ~12% of full-shift exposure; no peer-reviewed data |
| `ROBOT_LOAD_UNLOAD_FRACTION` | 0.15 | — | `[D]` | Single-station cell |
| `MEDIAN_DAYS_AWAY` | 12 | days | `[V]` | BLS SOII 2022, manufacturing |
| `WAGE_INFLATION_RATE` | 0.03 | /yr | `[D]` | SE-adjustable |
| `EMR_DELTA_ESTIMATE` | 0.15 | — | `[E]` | Midpoint 0.10–0.20; no sanding-robot EMR study |
| `ABSENTEEISM_OT_MULT` | 1.5 | — | `[V]` | Standard OT rate |
| `FBLR_DEFAULT_USD` | 35.0 | USD/hr | `[D]` | Override with customer rate |
| `NCCI_WC_RATE_PER_100` | 4.35 | USD/100 | `[D]` | Class code 3632 midpoint |

### Regulatory — `constants/regulatory.py`

| Constant | Value | Unit | Tag | Source |
|---|---|---|---|---|
| `OSHA_INSPECTION_PROB` | 0.03 | /yr | `[D]` | Baseline |
| `OSHA_CITATION_PROB` | 0.65 | — | `[D]` | P(citation \| inspection) |
| `OSHA_EXPECTED_PENALTY_USD` | 8 000 | USD | `[D]` | Expected given citation |
| `OSHA_SERIOUS_MAX_USD` | 16 550 | USD | `[V]` | OSHA Jan 2025 |
| `OSHA_WILLFUL_MAX_USD` | 165 514 | USD | `[V]` | OSHA Jan 2025 |
| `OSHA_FAILURE_ABATE_USD` | 16 550 | USD/day | `[V]` | OSHA Jan 2025 |

---

## 8. Extension Points

### JurisdictionAdapter Protocol

```python
class JurisdictionAdapter(Protocol):
    name: str
    hav_eav: float
    hav_elv: float

    def regulatory_cost(self, features: ExposureFeatures) -> float: ...
    def compliance_flags(self, features: ExposureFeatures) -> dict[str, bool]: ...
```

Bundled: `pipeline/standards/jurisdictions/us.py`, `eu.py`, `uk.py`. To add Canada: create `ca.py`, register in `jurisdictions/__init__.py`, appears in dashboard dropdown automatically.

Public import paths:
```python
from esh_savings.pipeline import Pipeline
from esh_savings.pipeline.ingestion import load_session
from esh_savings.pipeline.standards.jurisdictions.us import USAdapter
```

### IngestionConfig Overrides

MCAP topic names and HDF5 dataset paths are configurable via `IngestionConfig`, allowing the same reader to handle files from different recorders without code changes.

---

## 9. Implementation Phases

| Phase | Scope | Deliverable |
|---|---|---|
| **1 — MVP** | HDF5 ingestion (vibration + force) + features + standards (US) + basic savings + JSON + Excel skeleton (Sheets 1, 3, 5) | Vibration-only and force-only runs produce a readable Excel |
| **2 — Full Pipeline** | MCAP + RRD readers + Stage 4 cost calibration + full Excel (all 5 sheets with formulas) + customer SQLite store | Full dynamic Excel with SE inputs and Y1/Y2/Y5 forecast |
| **3 — Orientation + Intelligence** | Orientation channel + arm elevation/wrist pronation + provenance tagging + audit log + feedback loop | RULA partially sensor-derived; proposals fully auditable |
| **4 — Multi-jurisdiction + Branding** | EU and UK adapters + SE/GrayMatter Excel branding + accuracy dashboard | International proposals |

---

## 10. Running the Web App

```bash
pip install esh-savings          # HDF5 + US only
pip install esh-savings[mcap]    # add MCAP support
pip install esh-savings[rerun]   # add RRD support (rerun-sdk >= 0.16)
pip install esh-savings[all]     # all formats

esh-savings serve                # dashboard at http://localhost:8000
```

**Workflow:**
1. Select or create a customer — enter operator count, injury history, WC costs
2. Upload session file (`.hdf5`, `.mcap`, `.rrd`)
3. Select jurisdiction (US default) and analysis channels (Vibration / Force / Orientation)
4. Override any `[D]` constants if needed
5. Compute — pipeline runs in < 5 seconds
6. Review results in dashboard
7. Download Excel workbook — all `[D]` cells are editable for sensitivity analysis

---

## 11. Technology Stack

| Layer | Technology | Notes |
|---|---|---|
| Language | Python 3.11+ | |
| Data models | Pydantic v2 | Strict typing at every stage boundary |
| Signal processing | NumPy + SciPy | FFT for frequency-weighted A(8), resampling, percentiles |
| HDF5 ingestion | h5py | |
| MCAP ingestion | mcap (pip) | |
| RRD ingestion | rerun-sdk ≥ 0.16 | Pin `rerun-sdk>=0.16,<0.18` until DataFrame API stabilizes |
| Web framework | FastAPI | |
| Dashboard UI | Jinja2 | No JS build step |
| Excel generation | openpyxl | Dynamic workbook with named ranges, formulas, cell protection |
| Persistence | SQLite | `constants` + `customers` + `audit` tables |
| Package manager | uv | |
| Testing | pytest | Unit tests per pipeline stage + fixture session files |

**Removed:** ReportLab

---

## 12. Open Questions

> **Q1 — Tool-to-Tool handoff contract**
> How does `ESHResult` JSON reach Tool 2 (Reachability) and Tool 3 (Doability)? The JSON schema from `reporting/json.py` is the de facto contract. Needs a decision before Phase 1 ships so the schema is stable.

> **Q2 — RRD reader API stability**
> `rerun-sdk` DataFrame API added in 0.16; may change in 0.17+. Gate behind `pip install esh-savings[rerun]` and pin `rerun-sdk>=0.16,<0.18`.

> **Q3 — Calibration store: per-machine vs. shared**
> Per-SE SQLite loses cross-SE learning. Start per-machine (Phase 1–3), design schema to be exportable, add shared sync endpoint in Phase 4 if team grows.

> **Q4 — MCAP topic schema**
> Must define canonical topic convention for position and orientation topics before Phase 2 ships, or `IngestionConfig` overrides become the primary interface.

> **Q5 — Excel branding**
> GrayMatter logo and customer-specific cover sheet deferred to Phase 4. Needs SE input on standard proposal format.

---

## 13. Related Documents

- ESH Savings Model — PRD v2.0 (April 2026) — source of truth
- HSPI System — primary source of `.hdf5` session files
- Solutions Engineering Agent — Tool 2 (Reachability) and Tool 3 (Doability) receive `ESHResult` JSON

**Standards cited:**
- ISO 5349-1:2001, ISO 5349-2:2001, ISO 8041-1:2017
- ISO 11228-2:2007, ISO 11228-3:2007
- ACGIH TLV Booklet (current)
- EU Directive 2002/44/EC
- UK Control of Vibration at Work Regulations 2005
- Moore & Garg 1995 (Strain Index)
- McAtamney & Corlett 1993 (RULA)
- NCCI Annual Statistical Bulletin 2022–23
- BLS SOII 2022
- OSHA Safety Pays
- Snook & Ciriello 1991
- Circadian Technologies — Absenteeism: The Bottom-Line Killer
- NSC Injury Facts 2024
- NIOSH Publication 89-106
- Liberty Mutual 2025 Workplace Safety Index
