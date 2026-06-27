import math
import json
from database.db import get_db_connection

def get_accuracy_trend(project_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, timestamp, is_correct FROM predictions WHERE project_id = ? ORDER BY id ASC", 
        (project_id,)
    )
    rows = cursor.fetchall()
    conn.close()

    trend = []
    running_total = 0
    running_correct = 0
    for row in rows:
        if row["is_correct"] is not None:
            running_total += 1
            if row["is_correct"] == 1:
                running_correct += 1
            accuracy = round((running_correct / running_total) * 100, 2)
            trend.append({
                "id": row["id"],
                "label": f"#{row['id']}",
                "timestamp": row["timestamp"],
                "accuracy": accuracy,
                "total": running_total,
                "correct": running_correct
            })
    return trend

def get_confusion_matrix(project_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT prediction, actual FROM predictions WHERE project_id = ? AND actual IS NOT NULL", 
        (project_id,)
    )
    rows = cursor.fetchall()
    conn.close()

    classes = set()
    for row in rows:
        classes.add(row["prediction"])
        classes.add(row["actual"])
    classes = sorted(list(classes))
    
    matrix = [[0] * len(classes) for _ in range(len(classes))]
    class_idx = {c: i for i, c in enumerate(classes)}

    for row in rows:
        p_idx = class_idx[row["prediction"]]
        a_idx = class_idx[row["actual"]]
        matrix[a_idx][p_idx] += 1  # Rows: actual, Cols: prediction

    return {
        "labels": classes,
        "matrix": matrix
    }

def get_data_drift(project_id):
    # Base implementation: check shift in average confidence.
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT confidence FROM predictions WHERE project_id = ? AND confidence IS NOT NULL ORDER BY id", (project_id,))
    rows = [r["confidence"] for r in cursor.fetchall()]
    conn.close()
    
    if len(rows) < 40:
        return {"drift": False, "message": "Not enough data to calculate confidence drift."}
        
    old = rows[:len(rows)//2]
    new = rows[len(rows)//2:]
    
    old_m = sum(old) / len(old)
    new_m = sum(new) / len(new)
    diff = abs(new_m - old_m)
    
    return {
        "drift": diff > 0.15,
        "old_mean": round(old_m, 4),
        "new_mean": round(new_m, 4),
        "difference_score": round(diff, 4),
        "threshold": 0.15,
        "message": "Shift in prediction probability distributions."
    }

def get_outliers(project_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, prediction, actual, confidence, is_correct, timestamp FROM predictions WHERE project_id = ? AND is_outlier = 1 ORDER BY timestamp DESC LIMIT 50",
        (project_id,)
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {
        "count": len(rows),
        "records": rows,
        "low_threshold": 0.3,
        "high_threshold": 0.95
    }

def get_concept_drift(project_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_correct FROM predictions WHERE project_id = ? AND is_correct IS NOT NULL", (project_id,))
    rows = [r["is_correct"] for r in cursor.fetchall()]
    conn.close()
    
    if len(rows) < 20:
        return {"drift_detected": False, "message": "Not enough data."}
        
    overall_acc = sum(rows) / len(rows)
    recent = rows[-20:]
    recent_acc = sum(recent) / len(recent)
    drift = (overall_acc - recent_acc) > 0.15
    return {
        "drift_detected": drift,
        "overall_accuracy": round(overall_acc * 100, 2),
        "recent_accuracy": round(recent_acc * 100, 2),
        "message": "Caution: Concept Drift." if drift else "Stable."
    }

def get_latency_trend(project_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, latency_ms FROM predictions WHERE project_id = ? ORDER BY id ASC", (project_id,))
    rows = [{"id": r["id"], "latency": round(r["latency_ms"], 2)} for r in cursor.fetchall()]
    conn.close()
    return rows

def get_feature_drift(project_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT features FROM predictions WHERE project_id = ?", (project_id,))
    rows = cursor.fetchall()
    conn.close()
    
    if len(rows) < 20:
        return {"sufficient_data": False}
        
    all_features = []
    for r in rows:
        try:
            f = json.loads(r["features"])
            if isinstance(f, dict): all_features.append(f)
        except:
            pass
            
    if not all_features:
         return {"sufficient_data": False}
         
    recent = all_features[-20:]
    keys = list(all_features[0].keys())[:3] # Analyze up to top 3 feature keys
    
    res_overall = {}
    res_recent = {}
    for k in keys:
        ov = [f.get(k, 0) for f in all_features if isinstance(f.get(k, 0), (int, float))]
        rc = [f.get(k, 0) for f in recent if isinstance(f.get(k, 0), (int, float))]
        if ov: res_overall[k] = round(sum(ov)/len(ov), 2)
        if rc: res_recent[k] = round(sum(rc)/len(rc), 2)
        
    return {
        "sufficient_data": True,
        "overall": res_overall,
        "recent": res_recent
    }

def get_class_distribution(project_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT prediction, COUNT(*) as count FROM predictions WHERE project_id = ? GROUP BY prediction", (project_id,))
    rows = cursor.fetchall()
    conn.close()
    return {r["prediction"]: r["count"] for r in rows}

def get_model_calibration(project_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT confidence, is_correct FROM predictions WHERE project_id = ? AND is_correct IS NOT NULL AND confidence IS NOT NULL", (project_id,))
    rows = cursor.fetchall()
    conn.close()
    
    bins = {"0.0-0.3": [0,0], "0.3-0.6": [0,0], "0.6-0.8": [0,0], "0.8-1.0": [0,0]} # [correct, total]
    for r in rows:
        c = r["confidence"]
        if c < 0.3: b = "0.0-0.3"
        elif c < 0.6: b = "0.3-0.6"
        elif c < 0.8: b = "0.6-0.8"
        else: b = "0.8-1.0"
        
        bins[b][1] += 1
        if r["is_correct"] == 1: bins[b][0] += 1
            
    return {b: round((d[0]/d[1])*100, 2) if d[1]>0 else 0.0 for b, d in bins.items()}

def get_fp_fn_trends(project_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT prediction, actual FROM predictions WHERE project_id = ? AND actual IS NOT NULL AND prediction != actual", (project_id,))
    rows = cursor.fetchall()
    conn.close()
    
    pairs = {}
    for r in rows:
        pair = f"Pred: {r['prediction']} | Act: {r['actual']}"
        pairs[pair] = pairs.get(pair, 0) + 1
        
    sorted_pairs = sorted(pairs.items(), key=lambda x: x[1], reverse=True)
    
    top1 = {"name": sorted_pairs[0][0], "count": sorted_pairs[0][1]} if len(sorted_pairs) > 0 else {"name": "None", "count": 0}
    top2 = {"name": sorted_pairs[1][0], "count": sorted_pairs[1][1]} if len(sorted_pairs) > 1 else {"name": "None", "count": 0}
    
    return {"top1": top1, "top2": top2}
