from flask import Flask, render_template, request, jsonify, abort
from database.db import init_db, insert_telemetry, get_project_by_key, get_all_projects, fetch_metrics
from services.advanced_monitor import (
    get_accuracy_trend,
    get_confusion_matrix,
    get_data_drift,
    get_outliers,
    get_concept_drift,
    get_latency_trend,
    get_feature_drift,
    get_class_distribution,
    get_model_calibration,
    get_fp_fn_trends
)
import os

app = Flask(__name__)

# Initialize database on startup
init_db()

@app.route('/')
def home():
    """Platform landing page."""
    return render_template("index.html")

@app.route('/dashboard')
def dashboard():
    """Observability Dashboard UI."""
    return render_template("dashboard.html")

# --- CORE TELEMETRY API --- #

@app.route('/api/v1/telemetry', methods=['POST'])
def telemetry():
    """
    Ingest prediction logs from external models.
    Expected JSON:
    {
        "api_key": "...",
        "prediction": "fraud",
        "confidence": 0.95,
        "actual": "fraud", (optional)
        "latency_ms": 120,
        "features": {"amount": 500.0, "age": 32}
    }
    """
    data = request.json
    if not data or "api_key" not in data or "prediction" not in data:
        return jsonify({"error": "Missing required fields: api_key, prediction"}), 400

    project = get_project_by_key(data["api_key"])
    if not project:
        return jsonify({"error": "Invalid API Key"}), 401

    insert_telemetry(
        project_id=project["id"],
        prediction=data["prediction"],
        actual=data.get("actual"),
        confidence=data.get("confidence"),
        latency_ms=data.get("latency_ms", 0.0),
        features_dict=data.get("features", {})
    )

    return jsonify({"status": "success", "message": "Telemetry logged."}), 201

# --- REPORTING / UI APIs --- #

@app.route('/api/projects')
def get_projects():
    return jsonify(get_all_projects())

@app.route('/metrics/summary')
def summary():
    project_id = request.args.get("project_id", 1, type=int)
    return jsonify(fetch_metrics(project_id))

@app.route('/metrics/accuracy-trend')
def accuracy_trend():
    project_id = request.args.get("project_id", 1, type=int)
    return jsonify(get_accuracy_trend(project_id))

@app.route('/metrics/confusion-matrix')
def confusion_matrix():
    project_id = request.args.get("project_id", 1, type=int)
    return jsonify(get_confusion_matrix(project_id))

@app.route('/metrics/data-drift')
def data_drift():
    project_id = request.args.get("project_id", 1, type=int)
    return jsonify(get_data_drift(project_id))

@app.route('/metrics/outliers')
def outliers():
    project_id = request.args.get("project_id", 1, type=int)
    return jsonify(get_outliers(project_id))

@app.route('/metrics/concept-drift')
def concept_drift():
    project_id = request.args.get("project_id", 1, type=int)
    return jsonify(get_concept_drift(project_id))

@app.route('/metrics/latency-trend')
def latency_trend():
    project_id = request.args.get("project_id", 1, type=int)
    return jsonify(get_latency_trend(project_id))

@app.route('/metrics/feature-drift')
def feature_drift():
    project_id = request.args.get("project_id", 1, type=int)
    return jsonify(get_feature_drift(project_id))

@app.route('/metrics/class-distribution')
def class_distribution():
    project_id = request.args.get("project_id", 1, type=int)
    return jsonify(get_class_distribution(project_id))

@app.route('/metrics/model-calibration')
def model_calibration():
    project_id = request.args.get("project_id", 1, type=int)
    return jsonify(get_model_calibration(project_id))

@app.route('/metrics/fp-fn-trends')
def fp_fn_trends():
    project_id = request.args.get("project_id", 1, type=int)
    return jsonify(get_fp_fn_trends(project_id))

@app.route('/api/report/download')
def download_report():
    from services.reporting import generate_project_report
    from flask import Response
    project_id = request.args.get("project_id", 1, type=int)
    report_json = generate_project_report(project_id)
    
    return Response(
        report_json,
        mimetype="application/json",
        headers={"Content-disposition": f"attachment; filename=project_{project_id}_deep_report.json"}
    )

if __name__ == "__main__":
    app.run(debug=True)
