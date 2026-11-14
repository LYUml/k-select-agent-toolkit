import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


def command(*args, cwd=None, input=None):
    executable = Path(sys.executable).parent / ("k-select.exe" if os.name == "nt" else "k-select")
    assert executable.is_file(), "Tests require pip install -e .[dev] first"
    return subprocess.run([str(executable), *args], cwd=cwd, input=input, text=True, encoding="utf-8", capture_output=True, timeout=15)


def test_installed_help_foreign_directory(tmp_path):
    result = command("--help", cwd=tmp_path)
    assert result.returncode == 0
    assert "performance" in result.stdout


def test_capabilities_foreign_directory(tmp_path):
    result = command("--json", "capabilities", cwd=tmp_path)
    data = json.loads(result.stdout)
    assert data["ok"]
    assert data["supported"]["model"] == ["1400"]
    assert "ADPI automation" in data["unsupported"]


def test_json_default_does_not_enter_repl():
    result = command("--json")
    assert json.loads(result.stdout)["ok"]


@pytest.mark.parametrize("args", [("performance", "--airflow", "nan"), ("performance", "--airflow", "-2"), ("performance", "--airflow", "300", "--model", "wrong"), ("unknown-command",)])
def test_invalid_arguments_are_json(args):
    result = command(*args)
    assert result.returncode != 0
    assert not json.loads(result.stdout)["ok"]


def test_repl_exit():
    result = command(input="exit\n")
    assert result.returncode == 0


def test_cli_reads_real_fixture_from_foreign_directory(tmp_path):
    fixture = Path(__file__).parent / "fixtures/1400-8in-300cfm.pdf"
    result = command("report-verify", str(fixture.resolve()), "--airflow", "300", cwd=tmp_path)
    assert result.returncode == 0
    assert json.loads(result.stdout)["checks"]["airflow"]
