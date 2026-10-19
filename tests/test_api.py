import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

spec = importlib.util.spec_from_file_location("api", Path(__file__).parents[1] / "app/api/app.py")
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)

class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = api.app.test_client()
    def test_health_is_independent_of_database(self):
        with patch.object(api, "database", side_effect=RuntimeError()):
            self.assertEqual(self.client.get("/healthz").status_code, 200)
            self.assertEqual(self.client.get("/api/readyz").status_code, 503)
    def test_invalid_titles(self):
        for payload in [{}, {"title":" "}, {"title":"x"*201}, [], {"title":42}]:
            self.assertEqual(self.client.post("/api/tasks", json=payload).status_code, 400)
    def test_patch_requires_boolean(self):
        self.assertEqual(self.client.patch("/api/tasks/1", json={"done":"false"}).status_code, 400)
    def test_create_uses_bound_parameters(self):
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = (1, "'; DROP TABLE tasks;", False)
        with patch.object(api, "database") as db:
            db.return_value.__enter__.return_value = conn
            response = self.client.post("/api/tasks", json={"title":"'; DROP TABLE tasks;"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(conn.execute.call_args.args[1], ("'; DROP TABLE tasks;",))
    def test_request_tracing_and_cache_headers(self):
        first = self.client.get("/healthz")
        second = self.client.get("/healthz")
        self.assertNotEqual(first.headers["X-Request-ID"], second.headers["X-Request-ID"])
        self.assertEqual(first.headers["Cache-Control"], "no-store")
        self.assertEqual(first.headers["X-Content-Type-Options"], "nosniff")
    def test_oversized_body_is_rejected(self):
        self.assertEqual(self.client.post("/api/tasks", json={"title":"x"*5000}).status_code, 413)
    def test_unknown_route_preserves_http_status(self):
        self.assertEqual(self.client.get("/api/missing").status_code, 404)
    def test_failure_does_not_expose_database_details(self):
        with patch.object(api, "database", side_effect=RuntimeError("internal-db-password")):
            response = self.client.get("/api/tasks")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b"internal-db-password", response.data)
    def test_missing_task(self):
        with patch.object(api, "database") as db:
            db.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = None
            self.assertEqual(self.client.delete("/api/tasks/99").status_code, 404)

if __name__ == "__main__":
    unittest.main()
