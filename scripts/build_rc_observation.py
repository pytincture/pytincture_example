#!/usr/bin/env python3
"""Combine example acceptance results into one portable RC observation."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping


SCHEMA_ID = (
    "https://github.com/pytincture/pytincture_example/contracts/"
    "rc-observation-v1.schema.json"
)
SHA256 = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _timestamp(value: str | None = None) -> str:
    if value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("observed_at must be an ISO-8601 timestamp") from exc
        if parsed.tzinfo is None:
            raise ValueError("observed_at must include a timezone")
        parsed = parsed.astimezone(timezone.utc)
    else:
        parsed = datetime.now(timezone.utc)
    return parsed.isoformat(timespec="seconds").replace("+00:00", "Z")


def _load_result(path: Path, label: str) -> tuple[dict, str]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"{label} result must be a JSON object")
    return payload, _sha256(path)


def _run_url(environment: Mapping[str, str]) -> str:
    required = ("GITHUB_SERVER_URL", "GITHUB_REPOSITORY", "GITHUB_RUN_ID")
    if not all(environment.get(name) for name in required):
        return ""
    return (
        f"{environment['GITHUB_SERVER_URL'].rstrip('/')}"
        f"/{environment['GITHUB_REPOSITORY']}/actions/runs/"
        f"{environment['GITHUB_RUN_ID']}"
    )


def _version(distribution: str) -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError as exc:
        raise ValueError(
            f"required distribution is not installed: {distribution}"
        ) from exc


def build_observation(
    args: argparse.Namespace, environment: Mapping[str, str]
) -> dict:
    acceptance, acceptance_hash = _load_result(
        args.acceptance_result, "browser acceptance"
    )
    load, load_hash = _load_result(args.load_result, "authenticated load")
    findings = []
    if acceptance.get("status") != "passed":
        findings.append("browser acceptance did not pass")
    if acceptance.get("console_errors"):
        findings.append("browser console errors were observed")
    if acceptance.get("failed_requests"):
        findings.append("browser request failures were observed")
    if load.get("status") != "passed":
        findings.append("authenticated load profile did not pass")
    for failure in load.get("failures", []):
        findings.append(f"load profile: {failure}")

    commit_sha = args.commit_sha or environment.get("GITHUB_SHA", "")
    evidence_url = args.evidence_url or _run_url(environment)
    observation = {
        "$schema": SCHEMA_ID,
        "schema_version": 1,
        "application": "pytincture_example",
        "application_version": _version("pytincture_example"),
        "candidate": _version("pytincture"),
        "widgetset": f"dhxpyt=={_version('dhxpyt')}",
        "status": "failed" if findings else "passed",
        "observed_at": _timestamp(args.observed_at),
        "commit_sha": commit_sha,
        "evidence_url": evidence_url,
        "run": {
            "id": args.run_id or environment.get("GITHUB_RUN_ID", ""),
            "attempt": int(
                args.run_attempt or environment.get("GITHUB_RUN_ATTEMPT", "1")
            ),
            "event": args.event or environment.get("GITHUB_EVENT_NAME", ""),
            "ref": args.ref or environment.get("GITHUB_REF", ""),
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "result_sha256": {
            "browser_acceptance": acceptance_hash,
            "authenticated_load": load_hash,
        },
        "results": {
            "browser_acceptance": acceptance,
            "authenticated_load": load,
        },
        "findings": findings,
    }
    failures = validate_observation(observation)
    if failures:
        raise ValueError("; ".join(failures))
    return observation


def validate_observation(observation: dict) -> list[str]:
    failures = []
    if (
        observation.get("$schema") != SCHEMA_ID
        or observation.get("schema_version") != 1
    ):
        failures.append("unsupported observation schema")
    for field in (
        "application",
        "application_version",
        "candidate",
        "widgetset",
        "status",
        "observed_at",
        "commit_sha",
        "evidence_url",
    ):
        if not isinstance(observation.get(field), str) or not observation[field]:
            failures.append(f"{field} is required")
    if observation.get("status") not in {"passed", "failed"}:
        failures.append("status is not supported")
    if not COMMIT.fullmatch(str(observation.get("commit_sha", ""))):
        failures.append("commit_sha must be a full lowercase Git SHA")
    try:
        _timestamp(observation.get("observed_at"))
    except ValueError as exc:
        failures.append(str(exc))
    if not str(observation.get("evidence_url", "")).startswith(
        ("https://", "http://")
    ):
        failures.append("evidence_url must be an absolute HTTP(S) URL")
    run = observation.get("run", {})
    if not isinstance(run, dict):
        failures.append("run must be an object")
        run = {}
    for field in ("id", "event", "ref"):
        if not isinstance(run.get(field), str) or not run[field]:
            failures.append(f"run.{field} is required")
    if not isinstance(run.get("attempt"), int) or run.get("attempt", 0) < 1:
        failures.append("run.attempt must be a positive integer")
    hashes = observation.get("result_sha256", {})
    if not isinstance(hashes, dict):
        failures.append("result_sha256 must be an object")
        hashes = {}
    if set(hashes) != {"browser_acceptance", "authenticated_load"}:
        failures.append("result_sha256 must contain both observation results")
    for label, digest in hashes.items():
        if not SHA256.fullmatch(str(digest)):
            failures.append(f"result_sha256.{label} must be a SHA-256 digest")
    results = observation.get("results", {})
    if not isinstance(results, dict) or set(results) != set(hashes):
        failures.append("results must match result_sha256")
    findings = observation.get("findings")
    if not isinstance(findings, list):
        failures.append("findings must be an array")
    elif observation.get("status") == "passed" and findings:
        failures.append("passed observation cannot contain findings")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--acceptance-result", type=Path, required=True)
    parser.add_argument("--load-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--observed-at")
    parser.add_argument("--commit-sha")
    parser.add_argument("--evidence-url")
    parser.add_argument("--run-id")
    parser.add_argument("--run-attempt")
    parser.add_argument("--event")
    parser.add_argument("--ref")
    args = parser.parse_args()
    try:
        observation = build_observation(args, os.environ)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"RC observation generation failed: {exc}") from exc
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(observation, indent=2, sort_keys=True) + "\n")
    print(args.output)


if __name__ == "__main__":
    main()
