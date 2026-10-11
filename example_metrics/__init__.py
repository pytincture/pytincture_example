"""Persistent, private login counts for the public example.

This package lives outside example/ so it is never shipped to the browser.
No emails, passwords, IP addresses or raw session tokens are stored.
"""

import hashlib
import hmac
import logging
import re
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import Response


COOKIE = "pytincture_example_visitor"
LOGGER = logging.getLogger(__name__)


class LoginStore:
    def __init__(self, database):
        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS logins ("
                "session_key TEXT PRIMARY KEY, browser_key TEXT NOT NULL, "
                "logged_at TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS logins_logged_at ON logins(logged_at)"
            )
            connection.commit()

    def connect(self):
        return sqlite3.connect(self.database, timeout=5)

    def record(self, session_id, browser_id):
        session_key = hashlib.sha256(session_id.encode()).hexdigest()
        browser_key = hashlib.sha256(browser_id.encode()).hexdigest()
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with closing(self.connect()) as connection:
            connection.execute(
                "INSERT OR IGNORE INTO logins VALUES (?, ?, ?)",
                (session_key, browser_key, now),
            )
            connection.commit()

    def report(self, days=30):
        since = (datetime.now(timezone.utc) - timedelta(days=days - 1)).date().isoformat()
        with closing(self.connect()) as connection:
            total, browsers, first, last = connection.execute(
                "SELECT COUNT(*), COUNT(DISTINCT browser_key), "
                "MIN(logged_at), MAX(logged_at) FROM logins"
            ).fetchone()
            daily = connection.execute(
                "SELECT substr(logged_at, 1, 10), COUNT(*), COUNT(DISTINCT browser_key) "
                "FROM logins WHERE logged_at >= ? "
                "GROUP BY substr(logged_at, 1, 10) ORDER BY 1 DESC",
                (since,),
            ).fetchall()
        return {
            "successful_logins": total,
            "unique_browsers": browsers,
            "first_login_utc": first,
            "last_login_utc": last,
            "daily": [
                {"date_utc": date, "successful_logins": count, "unique_browsers": unique}
                for date, count, unique in daily
            ],
        }


class LoginMetricsMiddleware:
    def __init__(self, app, store, secret, secure=False):
        self.app = app
        self.store = store
        self.secret = secret.encode()
        self.secure = secure

    def sign(self, visitor):
        digest = hmac.new(self.secret, visitor.encode(), hashlib.sha256).hexdigest()
        return visitor + "." + digest

    def visitor(self, cookie):
        if cookie and re.fullmatch(r"[a-f0-9]{32}\.[a-f0-9]{64}", cookie):
            visitor = cookie.split(".", 1)[0]
            if hmac.compare_digest(cookie, self.sign(visitor)):
                return visitor
        return secrets.token_hex(16)

    async def __call__(self, scope, receive, send):
        if not (
            scope["type"] == "http"
            and scope["method"] == "POST"
            and scope["path"] == "/py_ui/auth/user"
        ):
            return await self.app(scope, receive, send)

        cookie = Request(scope).cookies.get(COOKIE)

        async def tracked_send(message):
            session = scope.get("session", {})
            if (
                message["type"] == "http.response.start"
                and message["status"] == 303
                and session.get("user", {}).get("application") == "py_ui"
                and session.get("session_id")
            ):
                visitor = self.visitor(cookie)
                try:
                    await run_in_threadpool(self.store.record, session["session_id"], visitor)
                    response = Response()
                    response.set_cookie(
                        COOKIE, self.sign(visitor), max_age=365 * 24 * 60 * 60,
                        httponly=True, secure=self.secure, samesite="lax",
                    )
                    message["headers"] = list(message.get("headers", [])) + [
                        header for header in response.raw_headers if header[0] == b"set-cookie"
                    ]
                except sqlite3.Error:
                    LOGGER.exception("Could not persist example login metrics")
            await send(message)

        await self.app(scope, receive, tracked_send)
