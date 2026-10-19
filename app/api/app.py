import json
import logging
import os
import time
import uuid
from contextlib import contextmanager

import boto3
import psycopg
from flask import Flask, g, jsonify, request

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 4096

@app.before_request
def begin_request():
    g.request_id = str(uuid.uuid4())
    g.started = time.monotonic()

@app.after_request
def finish_request(response):
    response.headers["X-Request-ID"] = g.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    app.logger.info(json.dumps({
        "event": "http_request", "request_id": g.request_id,
        "method": request.method,
        "route": str(request.url_rule) if request.url_rule else "unmatched",
        "status": response.status_code,
        "duration_ms": round((time.monotonic() - g.started) * 1000, 2),
    }))
    return response

logging.basicConfig(level=logging.INFO, format='%(message)s')

@contextmanager
def database():
    password = os.getenv("DB_PASSWORD")
    user = os.getenv("DB_USER", "platform")
    if os.getenv("DB_SECRET_ARN"):
        secret = json.loads(boto3.client("secretsmanager").get_secret_value(
            SecretId=os.environ["DB_SECRET_ARN"])["SecretString"])
        password, user = secret["password"], secret["username"]
    with psycopg.connect(host=os.getenv("DB_HOST", "db"),
                          dbname=os.getenv("DB_NAME", "platform"), user=user,
                          password=password, connect_timeout=5,
                          sslmode=os.getenv("DB_SSLMODE", "require"),
                          options="-c statement_timeout=5000 -c lock_timeout=5000") as conn:
        # Serialize first-use schema creation across workers and tasks.
        conn.execute("SELECT pg_advisory_xact_lock(314159)")
        conn.execute("""CREATE TABLE IF NOT EXISTS tasks (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            title VARCHAR(200) NOT NULL, done BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""")
        conn.commit()  # Release the schema lock before executing application queries.
        yield conn

@app.get("/healthz")
def health():
    return jsonify(status="ok")

@app.get("/api/readyz")
def ready():
    with database() as conn:
        conn.execute("SELECT 1")
    return jsonify(status="ready")

@app.route("/api/tasks", methods=["GET", "POST"])
def tasks():
    if request.method == "POST":
        payload = request.get_json(silent=True)
        title = payload.get("title") if isinstance(payload, dict) else None
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 200:
            return jsonify(error="Title must contain 1 to 200 characters"), 400
        with database() as conn:
            row = conn.execute("INSERT INTO tasks(title) VALUES (%s) RETURNING id, title, done", (title.strip(),)).fetchone()
        return jsonify(dict(zip(("id", "title", "done"), row))), 201
    with database() as conn:
        rows = conn.execute("SELECT id, title, done FROM tasks ORDER BY id DESC LIMIT 100").fetchall()
    return jsonify([dict(zip(("id", "title", "done"), row)) for row in rows])

@app.route("/api/tasks/<int:task_id>", methods=["PATCH", "DELETE"])
def task(task_id):
    payload = request.get_json(silent=True)
    if request.method == "PATCH" and (not isinstance(payload, dict) or type(payload.get("done")) is not bool):
        return jsonify(error="done must be a boolean"), 400
    with database() as conn:
        if request.method == "DELETE":
            row = conn.execute("DELETE FROM tasks WHERE id=%s RETURNING id", (task_id,)).fetchone()
        else:
            row = conn.execute("UPDATE tasks SET done=%s WHERE id=%s RETURNING id", (payload["done"], task_id)).fetchone()
    return ("", 204) if row else (jsonify(error="Task not found"), 404)

@app.errorhandler(Exception)
def failure(error):
    from werkzeug.exceptions import HTTPException
    if isinstance(error, HTTPException):
        return jsonify(error=error.description), error.code
    app.logger.exception("request_failed")
    return jsonify(error="Service temporarily unavailable"), 503
