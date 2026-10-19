"""Local-only test: retain a task across database and API container restarts."""
import json
import subprocess
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE = "http://localhost:8080"
def call(path, method="GET", data=None):
    req = Request(BASE + path, method=method,
                  data=json.dumps(data).encode() if data is not None else None,
                  headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=10) as response:
        body = response.read()
        return json.loads(body) if body else None

def wait_ready():
    for _ in range(30):
        try:
            if call("/api/readyz")["status"] == "ready":
                return
        except (HTTPError, URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(2)
    raise RuntimeError("Application did not recover within 60 seconds")

task = call("/api/tasks", "POST", {"title": "Restart recovery verification"})
try:
    for service in ("db", "api"):
        subprocess.run(["docker", "compose", "restart", service], check=True)
        wait_ready()
        tasks = call("/api/tasks")
        if not any(row["id"] == task["id"] and row["title"] == task["title"] for row in tasks):
            raise AssertionError("Task lost after restarting " + service)
        print("PASS: task retained after " + service + " restart")
finally:
    wait_ready()
    call("/api/tasks/" + str(task["id"]), "DELETE")
