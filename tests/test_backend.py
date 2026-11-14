import json
import subprocess
from types import SimpleNamespace

import pytest

from cli_anything.kselect.core import KSelectError
from cli_anything.kselect.utils import kselect_backend


def test_native_timeout_has_recovery_context(monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])
    monkeypatch.setattr(kselect_backend.subprocess, "run", timeout)
    with pytest.raises(KSelectError) as exc:
        kselect_backend.call_backend("calculate", output_directory="C:/runs/one")
    assert exc.value.code == "backend_timeout"
    assert exc.value.details["output_directory"] == "C:/runs/one"
    assert exc.value.details["timeout_seconds"] <= 50


def test_broken_worker_json_is_not_success(monkeypatch):
    monkeypatch.setattr(kselect_backend.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout="broken", stderr="diagnostic", returncode=1))
    with pytest.raises(KSelectError) as exc:
        kselect_backend.call_backend("status")
    assert exc.value.code == "worker_failed"


def test_structured_worker_error_is_preserved(monkeypatch):
    data = {"ok": False, "error": {"code": "blocked", "message": "dialog open", "dialogs": ["Export"]}}
    monkeypatch.setattr(kselect_backend.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout=json.dumps(data), returncode=0))
    with pytest.raises(KSelectError) as exc:
        kselect_backend.call_backend("status")
    assert exc.value.code == "blocked"
    assert exc.value.details["dialogs"] == ["Export"]


def test_missing_installation_returns_actionable_error(monkeypatch, tmp_path):
    monkeypatch.setenv("KSELECT_GRD_EXE", str(tmp_path / "grd.exe"))
    with pytest.raises(KSelectError) as exc:
        kselect_backend.call_backend("status")
    assert exc.value.code == "not_installed"


def test_competing_process_cannot_use_desktop():
    from cli_anything.kselect.worker import desktop_lock
    with desktop_lock():
        with pytest.raises(KSelectError) as exc:
            kselect_backend.call_backend("status")
    assert exc.value.code == "busy"
