"""Explicit native acceptance. Failure is a failure; no mocked/skipped desktop."""
import argparse
import json
from pathlib import Path
import time

from cli_anything.kselect.core import NECKS, PerformanceRequest, verify_report
from cli_anything.kselect.service import calculate_performance
from cli_anything.kselect.utils.kselect_backend import call_backend


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-directory", required=True, type=Path)
    args = parser.parse_args()
    directory = args.output_directory.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    results = []
    state = call_backend("launch")
    for _ in range(60):
        status = call_backend("status")
        if status["state"] == "ready":
            break
        if status["state"] == "blocked":
            raise RuntimeError(status)
        time.sleep(.5)
    else:
        raise RuntimeError("GRD did not become ready")
    cases = [{"airflow": 300}, {"airflow": 112}, {"airflow": 300},
             {"airflow": 141.58423296, "airflow_unit": "l/s"}]
    cases += [{"airflow": 300, "module": module, "neck_in": neck} for module, necks in NECKS.items() for neck in necks]
    cases += [{"airflow": 300, "border": border} for border in ("F22 Surface", "F27 Spline", "F98 Narrow T")]
    for index, case in enumerate(cases):
        result = calculate_performance(**case, output_directory=str(directory / f"case-{index:02}"))
        request = PerformanceRequest(**case)
        # Reopen the file independently of the desktop call's returned result.
        replay = verify_report(result["report"]["path"], request)
        assert replay["report"]["selected"] == result["report"]["selected"]
        assert replay["report"]["sha256"] == result["report"]["sha256"]
        item = {"request": result["request"], "selected": result["report"]["selected"], "sha256": result["report"]["sha256"], "checks": result["checks"]}
        results.append(item)
        print(json.dumps(item), flush=True)
    summary = {"ok": True, "backend": "Installed GRD 10.0.2", "initial_launch": state["state"], "cases": results, "elapsed_seconds": round(time.monotonic() - start, 2)}
    (directory / "acceptance.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Native artifacts: {directory}")


if __name__ == "__main__":
    main()
