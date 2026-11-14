"""Public API shared by the CLI and MCP server."""
from pathlib import Path
from uuid import uuid4
import time

from .core import PerformanceRequest, verify_report, parse_report
from .utils.kselect_backend import call_backend


def capabilities():
    return {"ok": True, "name": "K-Select Agent Toolkit", "version": "0.1.0", "backend": "Installed Krueger GRD 10.0.2 on Windows",
            "supported": {"model": ["1400"], "module_necks_in": {"12x12": [6, 8], "24x24": [6, 8, 10, 12, 14, 15]},
                          "input_airflow_units": ["cfm", "l/s"], "terminal_velocity_fpm": 50, "throw_pattern": "Horizontal",
                          "operations": ["launch", "status", "calculate performance with native PDF", "read/verify saved report"]},
            "unsupported": ["ADPI automation", "other product families", "project schedules", "headless operation", "autonomous engineering design"],
            "requirements": "Installed K-Select with GRD module; unlocked interactive Windows desktop. Avoid mouse/keyboard use during product navigation."}


def calculate_performance(airflow: float, airflow_unit: str = "cfm", model: str = "1400", neck_in: int = 8,
                          module: str = "24x24", border: str = "F23 T-Bar", output_directory: str | None = None):
    request = PerformanceRequest(airflow=airflow, airflow_unit=airflow_unit, model=model, neck_in=neck_in, module=module, border=border)
    output = Path(output_directory) if output_directory else Path.home() / "K-select-runs" / (time.strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8])
    return call_backend("calculate", request={k: v for k, v in request.as_dict().items() if k != "effective_cfm"}, output_directory=str(output.resolve()))
