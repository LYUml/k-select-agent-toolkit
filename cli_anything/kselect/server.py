"""stdio-only MCP; SDK owns stdout, and GUI work runs in bounded subprocesses."""
from mcp.server.mcpserver import MCPServer

from . import __version__
from .core import KSelectError, PerformanceRequest, parse_report, verify_report
from .service import calculate_performance as calculate, capabilities
from .utils.kselect_backend import call_backend

server = MCPServer("K-Select Agent Toolkit", version=__version__, instructions="Call get_capabilities first. Only the listed GRD 10.0.2/1400 profile is validated. launch returns immediately; poll get_status. calculate_performance always exports and verifies a fresh native PDF. Do not claim ADPI or project compliance. Avoid concurrent desktop interaction.")


def guarded(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except KSelectError as exc:
        return exc.as_dict()


@server.tool()
def get_capabilities() -> dict:
    """Return validated model, units, operations, requirements and limitations."""
    return capabilities()


@server.tool()
def get_status() -> dict:
    """Inspect installed GRD and its current screen/blocking dialogs."""
    return guarded(call_backend, "status")


@server.tool()
def launch() -> dict:
    """Start native GRD; return immediately, then poll get_status."""
    return guarded(call_backend, "launch")


@server.tool()
def calculate_performance(airflow: float, airflow_unit: str = "cfm", model: str = "1400", neck_in: int = 8,
                          module: str = "24x24", border: str = "F23 T-Bar", output_directory: str | None = None) -> dict:
    """Calculate using GRD, export fresh PDF, verify identity/units/airflow and save a journal. Existing output directories are rejected. 50 fpm terminal velocity, Horizontal pattern only."""
    return guarded(calculate, airflow, airflow_unit, model, neck_in, module, border, output_directory)


@server.tool()
def read_report(pdf: str) -> dict:
    """Read native PDF values, table, hash and SI conversions without desktop access."""
    def read():
        return {"ok": True, "report": parse_report(pdf)}
    return guarded(read)


@server.tool()
def verify_result(pdf: str, airflow: float, airflow_unit: str = "cfm", model: str = "1400", neck_in: int = 8,
                  module: str = "24x24", border: str = "F23 T-Bar") -> dict:
    """Independently compare a native PDF with an explicit performance request."""
    def verify():
        return verify_report(pdf, PerformanceRequest(airflow, airflow_unit, model, neck_in, module, border))
    return guarded(verify)


def main():
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
