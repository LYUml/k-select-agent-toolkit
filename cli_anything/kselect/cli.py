"""CLI-Anything commands and interactive REPL."""
import json
from pathlib import Path
import shlex
import sys

import click

from . import __version__
from .core import KSelectError, PerformanceRequest, parse_report, verify_report
from .service import calculate_performance, capabilities
from .utils.kselect_backend import call_backend


def emit(result):
    # The same stable envelope is used in interactive and machine-readable mode.
    click.echo(json.dumps(result, ensure_ascii=True, indent=2))


@click.group(invoke_without_command=True)
@click.option("--json", "json_output", is_flag=True, help="Machine-readable JSON results (also the default).")
@click.version_option(__version__)
@click.pass_context
def cli(ctx, json_output):
    """K-Select Agent Toolkit: native manufacturer performance, PDF and verification."""
    if ctx.invoked_subcommand is None:
        if json_output:
            emit(capabilities())
        else:
            ctx.invoke(repl)


@cli.command("capabilities")
def show_capabilities():
    """List validated capabilities and explicit limitations."""
    emit(capabilities())


@cli.command()
def status():
    """Read executable, GRD screen and blocking dialogs."""
    emit(call_backend("status"))


@cli.command()
def launch():
    """Start GRD without waiting; poll status until ready."""
    emit(call_backend("launch"))


def performance_options(function):
    for option in reversed([
        click.option("--airflow", required=True, type=float),
        click.option("--airflow-unit", default="cfm", type=click.Choice(["cfm", "l/s"]), show_default=True),
        click.option("--model", default="1400", show_default=True),
        click.option("--neck-in", default=8, type=int, show_default=True),
        click.option("--module", default="24x24", type=click.Choice(["12x12", "24x24"]), show_default=True),
        click.option("--border", default="F23 T-Bar", show_default=True),
    ]):
        function = option(function)
    return function


@cli.command("performance")
@performance_options
@click.option("--output-directory", type=click.Path(path_type=Path), help="Fresh evidence directory; existing directories are rejected.")
def performance(**kwargs):
    """Calculate in native GRD, export PDF, verify and retain evidence."""
    if kwargs["output_directory"] is not None:
        kwargs["output_directory"] = str(kwargs["output_directory"])
    emit(calculate_performance(**kwargs))


@cli.command("report-read")
@click.argument("pdf", type=click.Path(exists=True, dir_okay=False, path_type=Path))
def report_read(pdf):
    """Read a native specified-airflow report without controlling the desktop."""
    emit({"ok": True, "report": parse_report(pdf)})


@cli.command("report-verify")
@click.argument("pdf", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@performance_options
def report_verify(pdf, **kwargs):
    """Independently compare a saved report against an explicit request."""
    emit(verify_report(pdf, PerformanceRequest(**kwargs)))


@cli.command()
def repl():
    """Interactive CLI-Anything REPL; type help or exit."""
    from .utils.repl_skin import ReplSkin
    skin = ReplSkin("kselect", version=__version__)
    skin.print_banner()
    session = skin.create_prompt_session() if sys.stdin.isatty() else None
    while True:
        try:
            line = skin.get_input(session) if session is not None else input("kselect> ")
            if line.strip() in ("exit", "quit"):
                break
            if not line.strip():
                continue
            if line.strip() == "help":
                line = "--help"
            # POSIX parsing supports quoted Windows paths with forward slashes.
            cli.main(args=shlex.split(line), standalone_mode=False)
        except (EOFError, KeyboardInterrupt):
            break
        except (click.ClickException, KSelectError, ValueError) as exc:
            skin.error(str(exc))
    skin.print_goodbye()


def main():
    # Windows redirected stdout may otherwise use a code page that cannot print
    # the upstream REPL skin. JSON remains ASCII-safe for existing integrations.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    try:
        cli.main(standalone_mode=False)
    except KSelectError as exc:
        emit(exc.as_dict())
        raise SystemExit(1)
    except click.ClickException as exc:
        emit({"ok": False, "error": {"code": "invalid_arguments", "message": exc.format_message()}})
        raise SystemExit(2)


if __name__ == "__main__":
    main()
