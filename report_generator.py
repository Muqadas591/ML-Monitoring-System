import sqlite3
import json
import secrets

DB_NAME = "database/predictions.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        api_key TEXT UNIQUE NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        prediction TEXT NOT NULL,
        actual TEXT,
        confidence REAL,
        is_correct INTEGER,
        is_outlier INTEGER DEFAULT 0,
        latency_ms REAL DEFAULT 0,
        features TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects (id)
    )
    """)

    # Create a default project if none exists
    cursor.execute("SELECT COUNT(*) FROM projects")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO projects (name, api_key) VALUES (?, ?)", ("Default Project", "default-api-key"))

    conn.commit()
    conn.close()

def get_project_by_key(api_key):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM projects WHERE api_key = ?", (api_key,))
    project = cursor.fetchone()
    conn.close()
    return project

def get_all_projects():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, api_key FROM projects")
    projects = cursor.fetchall()
    conn.close()
    return [dict(p) for p in projects]

def create_project(name):
    conn = get_db_connection()
    cursor = conn.cursor()
    api_key = secrets.token_hex(16)
    try:
        cursor.execute("INSERT INTO projects (name, api_key) VALUES (?, ?)", (name, api_key))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()

def insert_telemetry(project_id, prediction, actual, confidence, latency_ms, features_dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    is_correct = None
    if actual:
        is_correct = 1 if str(prediction).lower() == str(actual).lower() else 0
        
    is_outlier = 1 if confidence and (confidence < 0.3 or confidence > 0.95) else 0
    features_json = json.dumps(features_dict) if features_dict else "{}"

    cursor.execute("""
    INSERT INTO predictions (project_id, prediction, actual, confidence, is_correct, is_outlier, latency_ms, features)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (project_id, prediction, actual, confidence, is_correct, is_outlier, latency_ms, features_json))

    conn.commit()
    conn.close()

def fetch_metrics(project_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM predictions WHERE project_id = ?", (project_id,))
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM predictions WHERE is_correct = 1 AND project_id = ?", (project_id,))
    correct = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM predictions WHERE is_correct = 0 AND project_id = ?", (project_id,))
    wrong = cursor.fetchone()[0]

    accuracy = (correct / (correct + wrong)) if (correct + wrong) > 0 else 0

    conn.close()

    return {
        "total": total,
        "correct": correct,
        "wrong": wrong,
        "accuracy": round(accuracy * 100, 2)
    }

