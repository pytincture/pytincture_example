"""Load-test the example's authenticated Pytincture BFF path."""

from __future__ import annotations

import argparse
import asyncio
import json
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import httpx


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "example"
DEFAULT_BASE_URL = "http://127.0.0.1:8070"
EMAIL = "demo@example.com"
PASSWORD = "demo-password"
BFF_PATH = "/classcall/py_ui_data.py/py_ui_data/ping"


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = max(
        0,
        min(len(ordered) - 1, int(len(ordered) * fraction + 0.999999) - 1),
    )
    return ordered[index]


def summarize(values: list[float]) -> dict[str, float | int]:
    return {
        "count": len(values),
        "min_ms": round(min(values), 3),
        "median_ms": round(percentile(values, 0.50), 3),
        "p95_ms": round(percentile(values, 0.95), 3),
        "p99_ms": round(percentile(values, 0.99), 3),
        "max_ms": round(max(values), 3),
    }


def wait_for_service(base_url: str, timeout: float = 30.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urlopen(f"{base_url}/healthz", timeout=1) as response:
                return json.load(response)
        except (OSError, URLError):
            time.sleep(0.25)
    raise RuntimeError("Pytincture example did not become healthy")


async def prepare_client(base_url: str) -> tuple[httpx.AsyncClient, float, float]:
    client = httpx.AsyncClient(
        base_url=base_url,
        follow_redirects=False,
        timeout=httpx.Timeout(30),
    )
    try:
        login_started = time.perf_counter()
        login = await client.post(
            "/py_ui/auth/user",
            data={"email": EMAIL, "password": PASSWORD},
        )
        login_ms = (time.perf_counter() - login_started) * 1000
        if login.status_code != 303 or login.headers.get("location") != "/py_ui":
            raise RuntimeError(
                f"login returned HTTP {login.status_code}: {login.text[:200]}"
            )

        app_started = time.perf_counter()
        app = await client.get("/py_ui")
        app_ms = (time.perf_counter() - app_started) * 1000
        app.raise_for_status()
        if "pytincture.js" not in app.text:
            raise RuntimeError(
                "authenticated Pytincture application HTML was not returned"
            )

        csrf = client.cookies.get("pytincture_csrf")
        if not csrf:
            raise RuntimeError("login did not issue the CSRF cookie")
        client.headers["X-CSRF-Token"] = csrf
        return client, login_ms, app_ms
    except Exception:
        await client.aclose()
        raise


async def run_worker(
    client: httpx.AsyncClient,
    worker_id: int,
    request_count: int,
    start: asyncio.Event,
    latencies: list[float],
    errors: list[str],
) -> None:
    await start.wait()
    for sequence in range(request_count):
        value = worker_id * 1_000_000 + sequence
        began = time.perf_counter()
        try:
            response = await client.post(BFF_PATH, json={"kwargs": {"value": value}})
            response.raise_for_status()
            if response.json() != {"value": value}:
                raise RuntimeError(f"unexpected BFF response: {response.text[:200]}")
        except Exception as exc:
            if len(errors) < 20:
                errors.append(f"worker {worker_id}, request {sequence}: {exc}")
        finally:
            latencies.append((time.perf_counter() - began) * 1000)


async def exercise(
    base_url: str,
    users: int,
    requests: int,
) -> dict:
    async with httpx.AsyncClient(base_url=base_url, timeout=10) as anonymous:
        rejected = await anonymous.post(
            BFF_PATH,
            json={"kwargs": {"value": "unauthenticated"}},
        )
    if rejected.status_code != 401:
        raise RuntimeError(
            f"unauthenticated BFF call returned HTTP {rejected.status_code}, not 401"
        )

    prepared = await asyncio.gather(
        *(prepare_client(base_url) for _ in range(users))
    )
    clients = [entry[0] for entry in prepared]
    login_latencies = [entry[1] for entry in prepared]
    app_latencies = [entry[2] for entry in prepared]
    latencies: list[float] = []
    errors: list[str] = []
    start = asyncio.Event()
    quotient, remainder = divmod(requests, users)
    tasks = [
        asyncio.create_task(
            run_worker(
                client,
                worker_id,
                quotient + (1 if worker_id < remainder else 0),
                start,
                latencies,
                errors,
            )
        )
        for worker_id, client in enumerate(clients)
    ]
    began = time.perf_counter()
    start.set()
    try:
        await asyncio.gather(*tasks)
    finally:
        await asyncio.gather(*(client.aclose() for client in clients))
    elapsed = time.perf_counter() - began
    return {
        "unauthenticated_bff_status": rejected.status_code,
        "session_login": summarize(login_latencies),
        "authenticated_app_html": summarize(app_latencies),
        "authenticated_bff": {
            **summarize(latencies),
            "elapsed_seconds": round(elapsed, 3),
            "requests_per_second": round(requests / elapsed, 3),
            "error_count": len(errors),
            "error_rate": round(len(errors) / requests, 6),
            "errors": errors,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--users", type=int, default=20)
    parser.add_argument("--requests", type=int, default=500)
    parser.add_argument("--p95-budget-ms", type=float, default=500)
    parser.add_argument("--minimum-rps", type=float, default=20)
    parser.add_argument("--output", type=Path, default=Path("load-results.json"))
    parser.add_argument("--external-service", action="store_true")
    args = parser.parse_args()
    if args.users < 1 or args.requests < args.users:
        parser.error("requests must be at least users, and both must be positive")

    service = None
    service_log = None
    if not args.external_service:
        service_log = tempfile.TemporaryFile(mode="w+t")
        service = subprocess.Popen(
            [sys.executable, "run.py"],
            cwd=EXAMPLE,
            stdout=service_log,
            stderr=subprocess.STDOUT,
            text=True,
        )

    try:
        health = wait_for_service(args.base_url)
        results = asyncio.run(exercise(args.base_url, args.users, args.requests))
        bff = results["authenticated_bff"]
        failures = []
        if bff["error_count"]:
            failures.append(f"{bff['error_count']} BFF requests failed")
        if bff["p95_ms"] > args.p95_budget_ms:
            failures.append(
                f"BFF p95 {bff['p95_ms']} ms exceeded {args.p95_budget_ms} ms"
            )
        if bff["requests_per_second"] < args.minimum_rps:
            failures.append(
                f"throughput {bff['requests_per_second']} rps was below "
                f"{args.minimum_rps} rps"
            )
        evidence = {
            "schema_version": 1,
            "generated_at": (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            ),
            "target": args.base_url,
            "health": health,
            "configuration": {
                "users": args.users,
                "requests": args.requests,
                "p95_budget_ms": args.p95_budget_ms,
                "minimum_requests_per_second": args.minimum_rps,
            },
            **results,
            "status": "failed" if failures else "passed",
            "failures": failures,
        }
        args.output.write_text(f"{json.dumps(evidence, indent=2)}\n")
        print(json.dumps(evidence, indent=2))
        if failures:
            raise SystemExit("; ".join(failures))
    finally:
        if service is not None:
            service.send_signal(signal.SIGINT)
            try:
                service.wait(timeout=10)
            except subprocess.TimeoutExpired:
                service.kill()
                service.wait()
            service_log.seek(0)
            output = service_log.read()
            service_log.close()
            if service.returncode not in (0, -signal.SIGINT):
                raise RuntimeError(
                    f"Pytincture example exited with {service.returncode}:\n{output}"
                )


if __name__ == "__main__":
    main()
