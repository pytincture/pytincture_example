"""Load-test the example's authenticated Pytincture BFF path."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
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
# Pytincture 1.0.0rc5 namespaces classcall routes under the application:
# /{application}/classcall/{module}/{class}/{method}. The unprefixed path
# rc1 served is gone, and an unmatched route 404s before authentication
# runs -- which is why a stale path reads as "404, not 401" below.
APPLICATION = "py_ui"
PAGINATED_BFF_PATH = (
    f"/{APPLICATION}/classcall/py_ui_data.py/py_ui_data/dataset_page"
)
LOGIN_CSRF_FIELD = re.compile(
    r'name="login_csrf_token"\s+value="([^"]+)"'
)
# rc5 renamed the CSRF cookie and varies it by deployment: the __Host- form
# under HTTPS, the dev form when session_https_only is False. rc1's
# "pytincture_csrf" no longer exists. Accept whichever this deployment issued.
CSRF_COOKIE_NAMES = ("__Host-pytincture-csrf", "pytincture-dev-csrf")
# See service_environment(). Fixed widenings; the concurrency-shaped limits
# are scaled to the profile in that function.
LOAD_PROFILE_LIMITS = {
    "AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS": "60",
    "AUTH_PASSWORD_HASH_MAX_CONCURRENCY": "8",
    "AUTH_PASSWORD_HASH_QUEUE_TIMEOUT_SECONDS": "60",
    "BFF_QUEUE_TIMEOUT_SECONDS": "30",
    "BFF_REQUEST_INGRESS_QUEUE_TIMEOUT_SECONDS": "30",
}
MAX_PAGE_SIZE = 100
CATALOG_SIZE = 10_000


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


def csrf_token(client: httpx.AsyncClient) -> str | None:
    """The CSRF token this deployment issued, under whichever cookie name."""
    return next(
        (value for name in CSRF_COOKIE_NAMES if (value := client.cookies.get(name))),
        None,
    )


async def prepare_client(base_url: str) -> tuple[httpx.AsyncClient, float, float]:
    client = httpx.AsyncClient(
        base_url=base_url,
        follow_redirects=False,
        timeout=httpx.Timeout(30),
    )
    try:
        login_started = time.perf_counter()
        # rc5 binds each login post to a single-use token the login page issues
        # into the session, so the form must be fetched before it is submitted.
        # An unauthenticated GET of the application 307s here; request the login
        # page directly rather than following redirects on a no-redirect client.
        form = await client.get(f"/{APPLICATION}/login")
        form.raise_for_status()
        match = LOGIN_CSRF_FIELD.search(form.text)
        if match is None:
            raise RuntimeError("login page did not carry a login_csrf_token field")
        login = await client.post(
            f"/{APPLICATION}/auth/user",
            data={
                "email": EMAIL,
                "password": PASSWORD,
                "login_csrf_token": match.group(1),
            },
        )
        login_ms = (time.perf_counter() - login_started) * 1000
        if (
            login.status_code != 303
            or login.headers.get("location") != f"/{APPLICATION}"
        ):
            raise RuntimeError(
                f"login returned HTTP {login.status_code}: {login.text[:200]}"
            )

        app_started = time.perf_counter()
        app = await client.get(f"/{APPLICATION}")
        app_ms = (time.perf_counter() - app_started) * 1000
        app.raise_for_status()
        if "pytincture.js" not in app.text:
            raise RuntimeError(
                "authenticated Pytincture application HTML was not returned"
            )

        csrf = csrf_token(client)
        if not csrf:
            raise RuntimeError(
                "login did not issue a CSRF cookie under any of "
                f"{CSRF_COOKIE_NAMES}; jar held {sorted(client.cookies.keys())}"
            )
        client.headers["X-CSRF-Token"] = csrf
        return client, login_ms, app_ms
    except Exception:
        await client.aclose()
        raise


async def run_worker(
    client: httpx.AsyncClient,
    worker_id: int,
    request_count: int,
    records_per_page: int,
    start: asyncio.Event,
    latencies: list[float],
    errors: list[str],
) -> None:
    await start.wait()
    for sequence in range(request_count):
        page = (worker_id * request_count + sequence) % (
            CATALOG_SIZE // records_per_page
        ) + 1
        began = time.perf_counter()
        try:
            response = await client.post(
                PAGINATED_BFF_PATH,
                json={"args": [], "kwargs": {"page": page, "page_size": records_per_page}},
            )
            response.raise_for_status()
            payload = response.json()
            items = payload.get("items", [])
            expected_first_id = (page - 1) * records_per_page + 1
            if (
                payload.get("page") != page
                or payload.get("page_size") != records_per_page
                or payload.get("total") != CATALOG_SIZE
                or len(items) != records_per_page
                or items[0].get("id") != expected_first_id
            ):
                raise RuntimeError(f"unexpected BFF response: {response.text[:200]}")
        except Exception as exc:
            if len(errors) < 20:
                errors.append(
                    f"worker {worker_id}, request {sequence}: "
                    f"{type(exc).__name__}: {exc!r}"
                )
        finally:
            latencies.append((time.perf_counter() - began) * 1000)


async def prepare_clients(
    base_url: str,
    users: int,
    authentication_concurrency: int,
) -> tuple[list[httpx.AsyncClient], list[float], list[float]]:
    semaphore = asyncio.Semaphore(authentication_concurrency)

    async def prepare_limited():
        async with semaphore:
            return await prepare_client(base_url)

    prepared = await asyncio.gather(*(prepare_limited() for _ in range(users)))
    prepared_clients = [entry[0] for entry in prepared]
    load_clients = [
        httpx.AsyncClient(
            base_url=base_url,
            follow_redirects=False,
            timeout=httpx.Timeout(30),
            cookies=client.cookies,
            headers={"X-CSRF-Token": csrf_token(client)},
        )
        for client in prepared_clients
    ]
    # Session creation is intentionally separate from the measured stages.
    # Fresh transports avoid racing the server's idle keep-alive expiry after
    # preparing hundreds of password-authenticated sessions in bounded batches.
    await asyncio.gather(*(client.aclose() for client in prepared_clients))
    return (
        load_clients,
        [entry[1] for entry in prepared],
        [entry[2] for entry in prepared],
    )


async def run_stage(
    clients: list[httpx.AsyncClient],
    users: int,
    requests_per_user: int,
    records_per_page: int,
) -> dict:
    latencies: list[float] = []
    errors: list[str] = []
    start = asyncio.Event()
    tasks = [
        asyncio.create_task(
            run_worker(
                client,
                worker_id,
                requests_per_user,
                records_per_page,
                start,
                latencies,
                errors,
            )
        )
        for worker_id, client in enumerate(clients[:users])
    ]
    began = time.perf_counter()
    start.set()
    await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - began
    request_count = users * requests_per_user
    return {
        "users": users,
        "request_count": request_count,
        "records_per_response": records_per_page,
        **summarize(latencies),
        "elapsed_seconds": round(elapsed, 3),
        "requests_per_second": round(request_count / elapsed, 3),
        "error_count": len(errors),
        "error_rate": round(len(errors) / request_count, 6),
        "errors": errors,
    }


async def exercise(
    base_url: str,
    stages: list[int],
    requests_per_user: int,
    records_per_page: int,
    authentication_concurrency: int,
) -> dict:
    async with httpx.AsyncClient(base_url=base_url, timeout=10) as anonymous:
        rejected = await anonymous.post(
            PAGINATED_BFF_PATH,
            json={"args": [], "kwargs": {"page": 1, "page_size": records_per_page}},
        )
    if rejected.status_code != 401:
        raise RuntimeError(
            f"unauthenticated BFF call returned HTTP {rejected.status_code}, not 401"
        )

    clients, login_latencies, app_latencies = await prepare_clients(
        base_url,
        max(stages),
        authentication_concurrency,
    )
    try:
        cap_response = await clients[0].post(
            PAGINATED_BFF_PATH,
            json={"args": [], "kwargs": {"page": 1, "page_size": MAX_PAGE_SIZE + 1}},
        )
        cap_response.raise_for_status()
        cap_payload = cap_response.json()
        if (
            cap_payload.get("page_size") != MAX_PAGE_SIZE
            or len(cap_payload.get("items", [])) != MAX_PAGE_SIZE
        ):
            raise RuntimeError("BFF pagination did not enforce the 100-record cap")

        stage_results = []
        for users in stages:
            stage_results.append(
                await run_stage(
                    clients,
                    users,
                    requests_per_user,
                    records_per_page,
                )
            )
    finally:
        await asyncio.gather(*(client.aclose() for client in clients))
    return {
        "unauthenticated_bff_status": rejected.status_code,
        "pagination_cap": {
            "requested_records": MAX_PAGE_SIZE + 1,
            "returned_records": len(cap_payload["items"]),
            "enforced": True,
        },
        "session_login": summarize(login_latencies),
        "authenticated_app_html": summarize(app_latencies),
        "authenticated_paginated_bff_stages": stage_results,
    }


def parse_stages(value: str) -> list[int]:
    try:
        stages = [int(item.strip()) for item in value.split(",") if item.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "stages must be comma-separated integers"
        ) from exc
    if not stages or any(stage < 1 for stage in stages):
        raise argparse.ArgumentTypeError("stages must contain positive integers")
    if stages != sorted(set(stages)):
        raise argparse.ArgumentTypeError("stages must be unique and increasing")
    return stages


def service_environment(peak_sessions: int) -> dict[str, str]:
    """Environment for the service under test.

    Four rc5 defaults collide with the shape of this profile:

      * logins are throttled to AUTH_LOGIN_RATE_LIMIT_ATTEMPTS per window
        (20/60s), and the profile signs in one session per simulated user;
      * argon2 verification admits AUTH_PASSWORD_HASH_MAX_CONCURRENCY at a
        time (2), with a one-second queue timeout;
      * BFF request-body ingress is capped per peer at
        BFF_REQUEST_INGRESS_MAX_CONCURRENCY_PER_PEER (16), and every session
        here comes from one host;
      * BFF execution admits BFF_MAX_CONCURRENCY calls (32) with a queue of 64.

    Widen all four for the benchmark, scaled to the peak session count, and
    record the values in the results so the evidence states plainly which
    limits the numbers were measured under. These are real protections and a
    real deployment sees many peers: never carry them into one.
    """
    headroom = max(peak_sessions * 2, 100)
    environment = dict(os.environ)
    environment.update(LOAD_PROFILE_LIMITS)
    environment.update(
        {
            "AUTH_LOGIN_RATE_LIMIT_ATTEMPTS": str(headroom),
            "BFF_MAX_CONCURRENCY": str(headroom),
            "BFF_MAX_QUEUE": str(headroom * 2),
            "BFF_REQUEST_INGRESS_MAX_CONCURRENCY": str(headroom),
            "BFF_REQUEST_INGRESS_MAX_CONCURRENCY_PER_PEER": str(headroom),
            "BFF_REQUEST_INGRESS_MAX_QUEUE": str(headroom * 2),
        }
    )
    return environment


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument(
        "--stages",
        type=parse_stages,
        default=parse_stages("50,100,250"),
    )
    parser.add_argument("--requests-per-user", type=int, default=4)
    parser.add_argument("--records-per-page", type=int, default=MAX_PAGE_SIZE)
    parser.add_argument("--authentication-concurrency", type=int, default=8)
    parser.add_argument("--p95-budget-ms", type=float, default=1000)
    parser.add_argument("--minimum-rps", type=float, default=20)
    parser.add_argument("--output", type=Path, default=Path("load-results.json"))
    parser.add_argument("--external-service", action="store_true")
    args = parser.parse_args()
    if args.requests_per_user < 1:
        parser.error("requests-per-user must be positive")
    if not 1 <= args.records_per_page <= MAX_PAGE_SIZE:
        parser.error(f"records-per-page must be between 1 and {MAX_PAGE_SIZE}")
    if args.authentication_concurrency < 1:
        parser.error("authentication-concurrency must be positive")

    service = None
    service_log = None
    service_env = service_environment(max(args.stages))
    if not args.external_service:
        service_log = tempfile.TemporaryFile(mode="w+t")
        service = subprocess.Popen(
            [sys.executable, "run.py"],
            cwd=EXAMPLE,
            stdout=service_log,
            stderr=subprocess.STDOUT,
            text=True,
            env=service_env,
        )

    try:
        health = wait_for_service(args.base_url)
        results = asyncio.run(
            exercise(
                args.base_url,
                args.stages,
                args.requests_per_user,
                args.records_per_page,
                args.authentication_concurrency,
            )
        )
        failures = []
        for stage in results["authenticated_paginated_bff_stages"]:
            label = f"{stage['users']}-user stage"
            if stage["error_count"]:
                failures.append(f"{label}: {stage['error_count']} BFF requests failed")
            if stage["p95_ms"] > args.p95_budget_ms:
                failures.append(
                    f"{label}: p95 {stage['p95_ms']} ms exceeded "
                    f"{args.p95_budget_ms} ms"
                )
            if stage["requests_per_second"] < args.minimum_rps:
                failures.append(
                    f"{label}: throughput {stage['requests_per_second']} rps was "
                    f"below {args.minimum_rps} rps"
                )
        evidence = {
            "schema_version": 2,
            "generated_at": (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            ),
            "target": args.base_url,
            "health": health,
            "configuration": {
                "stages": args.stages,
                "requests_per_user": args.requests_per_user,
                "records_per_page": args.records_per_page,
                "authentication_concurrency": args.authentication_concurrency,
                "p95_budget_ms": args.p95_budget_ms,
                "minimum_requests_per_second": args.minimum_rps,
                # Relaxed for the benchmark only; see service_environment().
                "relaxed_limits": (
                    {}
                    if args.external_service
                    else {
                        key: service_env[key]
                        for key in sorted(
                            set(LOAD_PROFILE_LIMITS)
                            | {
                                "AUTH_LOGIN_RATE_LIMIT_ATTEMPTS",
                                "BFF_MAX_CONCURRENCY",
                                "BFF_MAX_QUEUE",
                                "BFF_REQUEST_INGRESS_MAX_CONCURRENCY",
                                "BFF_REQUEST_INGRESS_MAX_CONCURRENCY_PER_PEER",
                                "BFF_REQUEST_INGRESS_MAX_QUEUE",
                            }
                        )
                    }
                ),
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
