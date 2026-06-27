# ML Monitoring System

Flask-based ML observability service for collecting prediction telemetry, tracking performance/drift metrics, and exporting a deep JSON report.

## What This Project Does

- Ingests model telemetry through a REST API (`/api/v1/telemetry`)
- Stores events in SQLite (`database/predictions.db`)
- Serves a dashboard (`/dashboard`) with:
- Summary metrics (total/correct/wrong/accuracy)
- Accuracy trend
- Confusion matrix
- Data drift (confidence mean shift)
- Concept drift
- Latency trend
- Feature drift snapshot
- Class distribution
- Calibration bins
- Top FP/FN error pairs
- Exports a deep report JSON (`/api/report/download`)
- Includes a small Python SDK (`sdk/ml_monitor.py`) and load simulator (`sdk/test_integration.py`)

## Tech Stack

- Python 3
- Flask
- SQLite
- Chart.js (frontend chart rendering)

## Project Structure

```text
ml-monitoring-system/
|- app.py                       # Flask app and API routes
|- database/
|  |- db.py                     # DB init + CRUD + summary metrics
|  `- schema.sql                # Legacy schema snippet
|- services/
|  |- advanced_monitor.py       # Drift, trends, calibration, confusion matrix
|  |- reporting.py              # Deep report JSON builder
|  |- retrain_advisor.py        # Simple retrain recommendation helper
|  |- retrain_dataset.py        # Retrain-candidate storage/sync logic (not wired to routes)
|  `- monitor.py                # Low-confidence utility
|- sdk/
|  |- ml_monitor.py             # Client SDK for telemetry logging
|  `- test_integration.py       # Sends 100 synthetic logs
|- templates/                   # Flask HTML templates
|- static/                      # CSS/JS/assets
`- requirements.txt
```

## Setup

1. Create and activate a virtual environment.
2. Install dependencies.
3. Run the Flask app.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

App URL: `http://127.0.0.1:5000`

## Default Project/API Key

On startup, `init_db()` creates a default project if none exists:

- Name: `Default Project`
- API Key: `default-api-key`

## Telemetry API

### POST `/api/v1/telemetry`

Logs one prediction event.

Example request:

```json
{
  "api_key": "default-api-key",
  "prediction": "fraud",
  "actual": "safe",
  "confidence": 0.42,
  "latency_ms": 118.4,
  "features": {
    "tx_amount": 250.0,
    "user_age": 32
  }
}
```

Success response:

```json
{
  "status": "success",
  "message": "Telemetry logged."
}
```

Validation behavior:

- Missing `api_key` or `prediction` returns HTTP `400`
- Invalid API key returns HTTP `401`

## Dashboard and Metrics Endpoints

- `GET /` - landing page
- `GET /dashboard` - observability dashboard UI
- `GET /api/projects` - project list
- `GET /metrics/summary?project_id=1`
- `GET /metrics/accuracy-trend?project_id=1`
- `GET /metrics/confusion-matrix?project_id=1`
- `GET /metrics/data-drift?project_id=1`
- `GET /metrics/outliers?project_id=1`
- `GET /metrics/concept-drift?project_id=1`
- `GET /metrics/latency-trend?project_id=1`
- `GET /metrics/feature-drift?project_id=1`
- `GET /metrics/class-distribution?project_id=1`
- `GET /metrics/model-calibration?project_id=1`
- `GET /metrics/fp-fn-trends?project_id=1`
- `GET /api/report/download?project_id=1` - downloadable deep JSON report

## SDK Usage

```python
from sdk.ml_monitor import MLMonitorClient

client = MLMonitorClient(api_key="default-api-key", host="http://127.0.0.1:5000", verify_ssl=False)
client.log_prediction(
    prediction="fraud",
    actual="safe",
    confidence=0.73,
    features={"tx_amount": 199.5, "user_age": 41},
    execution_time_ms=92.6
)
```

Run simulator:

```powershell
python sdk\test_integration.py
```

## Data Model (Current Runtime Schema)

`database/db.py` creates:

- `projects(id, name, api_key, created_at)`
- `predictions(id, project_id, prediction, actual, confidence, is_correct, is_outlier, latency_ms, features, timestamp)`

Derived fields:

- `is_correct`: set when `actual` is provided
- `is_outlier`: `1` when confidence `< 0.3` or `> 0.95`

## Known Gaps / Notes From Code Audit

- `requirements.txt` is missing `requests` (required by `sdk/ml_monitor.py`).
- Retrain UI/API assets exist (`templates/retrain_candidates.html`, `static/js/retrain_candidates.js`) but corresponding Flask routes are not present in `app.py`.
- `services/retrain_dataset.py` expects an `image_path` column in `predictions`, but runtime schema in `database/db.py` does not include that column.
- `database/schema.sql` does not match the runtime schema used by `database/db.py` and appears to be a legacy file.
- `reports/report_generator.py` calls `fetch_metrics()` without required `project_id` and appears unused by the Flask app.

## Quick Smoke Test

1. Start server: `python app.py`
2. Send telemetry (via SDK or HTTP POST).
3. Open `http://127.0.0.1:5000/dashboard`
4. Verify charts and summary populate.
5. Download report from `/api/report/download?project_id=1`
