"""Login counts survive restarts and distinguish returning browsers."""

import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from starlette.testclient import TestClient

from example_metrics import COOKIE, LoginMetricsMiddleware, LoginStore


class LoginMetricsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.database = Path(self.directory.name) / "logins.sqlite3"
        self.store = LoginStore(self.database)
        self.sequence = 0

        async def application(scope, receive, send):
            self.sequence += 1
            scope["session"] = {
                "session_id": str(self.sequence),
                "user": {"application": "py_ui"},
            }
            status = 401 if dict(scope["headers"]).get(b"x-fail") else 303
            await send({"type": "http.response.start", "status": status, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        self.middleware = LoginMetricsMiddleware(application, self.store, "test-secret", secure=True)

    def client(self):
        return TestClient(self.middleware, base_url="https://testserver", follow_redirects=False)

    def test_returning_and_new_browsers_and_restart(self):
        client = self.client()
        first = client.post("/py_ui/auth/user")
        self.assertEqual(first.status_code, 303)
        cookie = first.headers["set-cookie"]
        for attribute in ("HttpOnly", "Secure", "SameSite=lax"):
            self.assertIn(attribute, cookie)
        client.post("/py_ui/auth/user")
        self.client().post("/py_ui/auth/user")
        report = LoginStore(self.database).report()
        self.assertEqual(report["successful_logins"], 3)
        self.assertEqual(report["unique_browsers"], 2)
        self.assertEqual(report["daily"][0]["successful_logins"], 3)

    def test_failed_login_and_other_requests_are_not_counted(self):
        client = self.client()
        client.post("/py_ui/auth/user", headers={"x-fail": "yes"})
        client.get("/py_ui/auth/user")
        client.post("/py_ui/auth/logout")
        self.assertEqual(self.store.report()["successful_logins"], 0)
        self.assertNotIn(COOKIE, client.cookies)

    def test_cookie_tampering_does_not_select_another_browser(self):
        visitor = "a" * 32
        valid = self.middleware.sign(visitor)
        self.assertEqual(self.middleware.visitor(valid), visitor)
        self.assertNotEqual(self.middleware.visitor(valid[:-1] + ("0" if valid[-1] != "0" else "1")), visitor)
        self.assertNotEqual(self.middleware.visitor(visitor), visitor)

    def test_duplicate_session_not_counted_and_credentials_not_stored(self):
        self.store.record("session-token", "visitor-cookie")
        self.store.record("session-token", "visitor-cookie")
        self.assertEqual(self.store.report()["successful_logins"], 1)
        with closing(self.store.connect()) as connection:
            row = connection.execute("SELECT * FROM logins").fetchone()
        self.assertNotIn("session-token", row)
        self.assertNotIn("visitor-cookie", row)


if __name__ == "__main__":
    unittest.main()
