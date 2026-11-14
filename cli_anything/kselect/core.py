"""Portable request validation and native report verification."""
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path

CFM_PER_LPS = 2.118880003289315
PA_PER_IN_WC = 249.08891
NECKS = {"12x12": [6, 8], "24x24": [6, 8, 10, 12, 14, 15]}


class KSelectError(RuntimeError):
    """An actionable, structured adapter error."""

    def __init__(self, code: str, message: str, **details):
        super().__init__(message)
        self.code, self.details = code, details

    def as_dict(self):
        return {"ok": False, "error": {"code": self.code, "message": str(self), **self.details}}


@dataclass(frozen=True)
class PerformanceRequest:
    airflow: float
    airflow_unit: str = "cfm"
    model: str = "1400"
    neck_in: int = 8
    module: str = "24x24"
    border: str = "F23 T-Bar"

    def __post_init__(self):
        if isinstance(self.airflow, bool) or not isinstance(self.airflow, (int, float)) or not math.isfinite(self.airflow) or self.airflow <= 0:
            raise KSelectError("invalid_request", "airflow must be a positive finite number")
        if self.airflow_unit not in ("cfm", "l/s"):
            raise KSelectError("invalid_request", "airflow_unit must be cfm or l/s")
        if self.model != "1400":
            raise KSelectError("unsupported_model", "v0.1 supports the validated 1400 profile only")
        if self.module not in NECKS or isinstance(self.neck_in, bool) or self.neck_in not in NECKS[self.module]:
            raise KSelectError("invalid_request", "Unsupported neck/module combination", supported=NECKS)
        if self.border not in ("F23 T-Bar", "F22 Surface", "F27 Spline", "F98 Narrow T"):
            raise KSelectError("invalid_request", "Unsupported border type")
        if not 1 <= self.effective_cfm <= 5000:
            raise KSelectError("invalid_request", "Effective airflow must be 1..5000 whole CFM")

    @property
    def effective_cfm(self) -> int:
        return math.floor(self.airflow * (CFM_PER_LPS if self.airflow_unit == "l/s" else 1) + 0.5)

    @property
    def neck_index(self) -> int:
        return (0 if self.module == "12x12" else 2) + NECKS[self.module].index(self.neck_in)

    def as_dict(self):
        return {**asdict(self), "effective_cfm": self.effective_cfm}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_report(path: str | Path) -> dict:
    """Read actual GRD 10.0.2 Crystal PDF; fail closed on unknown layouts."""
    from pypdf import PdfReader

    path = Path(path).resolve()
    if not path.is_file() or path.read_bytes()[:5] != b"%PDF-":
        raise KSelectError("invalid_report", "Expected an existing native PDF report")
    try:
        reader = PdfReader(path)
        if len(reader.pages) != 1:
            raise KSelectError("unsupported_report", "Expected a one-page GRD performance report")
        fragments = []
        plain = reader.pages[0].extract_text(visitor_text=lambda t, cm, tm, f, s: fragments.append(t.strip()))
        layout = reader.pages[0].extract_text(extraction_mode="layout")
        if "Krueger GRD Selection" not in plain or "Performance at Specified Airflow" not in plain:
            raise KSelectError("unsupported_report", "PDF lacks a specified-airflow manufacturer calculation")

        def match(pattern):
            m = re.search(pattern, layout, re.M)
            if not m:
                raise KSelectError("unsupported_report", f"Missing report field: {pattern}")
            return m

        model = match(r"Model:\s+(\S+)").group(1)
        neck = float(match(r"Neck Size:\s+(\d+(?:\.\d+)?)").group(1))
        module = match(r"Module Size:\s+(\S+)").group(1)
        terminal = float(match(r"Terminal Velocity\s*:\s*(\d+(?:\.\d+)?)\s+fpm").group(1))
        border = match(r"Border Type\s*:\s+(.+?)\s*$").group(1).strip()
        pattern = match(r"Throw Pattern:\s+(.+?)\s*$").group(1).strip()
        table = {}
        for name, label in [("velocity_fpm", r"Velocity FPM:"), ("airflow_cfm", r"Air Flow, CFM"), ("throw_ft", r"Throw Feet"), ("nc", r"NC"), ("pressure_in_wc", r"Pressure, w\.c\.")]:
            values = match(r"^\s*" + label + r"\s+([\d.\s\-]+)$").group(1).split()
            if len(values) != 9:
                raise KSelectError("unsupported_report", "Expected nine native performance columns", row=name)
            table[name] = [None if v == "-" else float(v) for v in values]
        # Crystal renders the four selected numbers together, separately from labels.
        rows = [re.fullmatch(r"(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(-|\d+(?:\.\d+)?)", t) for t in fragments]
        rows = [r for r in rows if r]
        if len(rows) != 1:
            raise KSelectError("unsupported_report", "Cannot uniquely read specified-airflow values")
        flow, throw, pressure, nc = rows[0].groups()
        selected = {"airflow_cfm": float(flow), "throw_ft": float(throw), "pressure_in_wc": float(pressure), "nc": None if nc == "-" else float(nc)}
        warnings = []
        reported_nc = selected["nc"]
        if table["nc"][7] is None and reported_nc == 10:
            # Observed GRD low-flow discrepancy: selected field prints 10 while
            # the performance table prints '-'. Preserve both, assert neither
            # an exact NC of 10 nor zero noise.
            selected["nc"] = None
            warnings.append("Native selected NC field reports 10 while the table reports '-'. nc is unknown; nc_reported preserves the printed number.")
        # The selected point is also column 8 in the native performance table.
        for key, val in selected.items():
            tab = table[key][7]
            tolerance = 0.51 if key == "throw_ft" else 0.011
            if (tab is None) != (val is None) or (tab is not None and abs(tab - val) > tolerance):
                raise KSelectError("report_inconsistent", "Selected result disagrees with native table", field=key, selected=val, table=tab)
        return {"path": str(path), "sha256": sha256(path), "model": model, "neck_in": neck, "module": module, "border": border, "throw_pattern": pattern, "terminal_velocity_fpm": terminal, "selected": selected,
                "si": {"airflow_lps": float(flow) / CFM_PER_LPS, "throw_m": float(throw) * 0.3048, "pressure_pa": float(pressure) * PA_PER_IN_WC},
                "nc_reported": reported_nc, "table": table, "warnings": warnings + ["GRD labels the selected throw as 'Throw m' even in this imperial report. Unit is established from the Throw Feet table and checked against its selected column.", "NC '-' is retained as unknown/below the displayed reporting range; it is not zero.", "Manufacturer results are a design aid, not project compliance approval."]}
    except KSelectError:
        raise
    except Exception as exc:
        raise KSelectError("invalid_report", f"Could not parse native report: {exc}") from exc


def verify_report(path: str | Path, request: PerformanceRequest) -> dict:
    report = parse_report(path)
    checks = {"model": report["model"] == request.model, "neck": report["neck_in"] == request.neck_in,
              "module": report["module"].lower() == request.module, "border": report["border"] == request.border,
              "airflow": report["selected"]["airflow_cfm"] == request.effective_cfm,
              "terminal_velocity": report["terminal_velocity_fpm"] == 50, "throw_pattern": report["throw_pattern"] == "Horizontal"}
    if not all(checks.values()):
        raise KSelectError("result_mismatch", "Native report does not match this request", checks=checks, report=report)
    return {"ok": True, "request": request.as_dict(), "checks": checks, "report": report}
