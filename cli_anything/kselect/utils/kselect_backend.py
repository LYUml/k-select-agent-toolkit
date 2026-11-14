"""Bounded process boundary: Windows/COM state never enters the MCP process."""
from __future__ import annotations

import json
import os
import subprocess
import sys

from ..core import KSelectError


def call_backend(operation: str, **arguments) -> dict:
    if sys.platform != "win32":
        raise KSelectError("windows_required", "Native K-Select operations require Windows and an unlocked desktop")
    command = [sys.executable, "-m", "cli_anything.kselect.worker"]
    timeout = 50 if operation == "calculate" else 15
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    try:
        p = subprocess.run(command, input=json.dumps({"operation": operation, **arguments}), capture_output=True,
                           text=True, encoding="utf-8", env=env, timeout=timeout,
                           creationflags=subprocess.CREATE_NO_WINDOW)
    except subprocess.TimeoutExpired as exc:
        raise KSelectError("backend_timeout", "Worker timed out; inspect status and any GRD dialogs before retrying. Existing run evidence is retained.", timeout_seconds=timeout, output_directory=arguments.get("output_directory")) from exc
    try:
        result = json.loads(p.stdout)
    except (ValueError, TypeError) as exc:
        raise KSelectError("worker_failed", "Worker did not return valid JSON", exit_code=p.returncode, diagnostic=p.stderr[-2000:]) from exc
    if not result.get("ok"):
        err = result.get("error", {})
        raise KSelectError(err.get("code", "worker_failed"), err.get("message", "Unknown worker failure"), **{k: v for k, v in err.items() if k not in ("code", "message")})
    return result
