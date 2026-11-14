# K-Select Agent Toolkit

MCP tools, a CLI and verifiable automation workflows for AI assistants operating
Krueger K-Select. The installed **manufacturer's GRD engine performs the
calculation**; this toolkit supplies inputs, exports its native PDF and checks
the result. It follows [CLI-Anything](docs/upstream-review.md) conventions and
includes its REPL component.

## Supported in v0.1

- Windows; **GRD 10.0.2**, locally tested with K-Select 13.3.54.
- **Model 1400**, Horizontal throw, terminal velocity **50 fpm**.
- 12x12 module: 6/8-inch neck; 24x24 module: 6/8/10/12/14/15-inch neck.
- F23 T-Bar, F22 Surface, F27 Spline and F98 Narrow T borders.
- CFM or L/s input, converted to nearest whole CFM for the native app.
- Native performance PDF, JSON results, SHA256 and per-run journal.
- Independent reading/verification of saved reports and SI conversions.

ADPI automation, other product families, schedules and autonomous design are
outside this release. The manufacturer's product range is broader than this
adapter's validated range. An **unlocked interactive desktop** is required;
navigation may foreground GRD and move the pointer. This is not headless software.

## Install

Install [official K-Select](https://www.krueger-hvac.com/public/software/k-select)
with its GRD module, and Python **3.12**. Manufacturer software/data are not
redistributed. Clone this repository or extract a release source archive:

```powershell
git clone https://github.com/LYUml/k-select-agent-toolkit.git
cd k-select-agent-toolkit
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
```

For a custom Python location add `-Python C:/path/to/python.exe`.
Setup creates `.venv`, installs pinned dependencies and the toolkit, checks
dependencies and writes `local/mcp.json`. The Microsoft Store `python` alias is
not treated as a working interpreter. Rerun setup after moving the checkout.

Default backend: `C:/Program Files (x86)/Krueger/Selection/GRD/grd.exe`.
For a custom installation set `KSELECT_GRD_EXE` to its full `grd.exe` path,
including in your MCP client's environment when necessary. Release wheels
support normal `pip install`; they do not include the manufacturer application.

## CLI

```powershell
.\.venv\Scripts\k-select.exe --json capabilities
.\.venv\Scripts\k-select.exe launch
.\.venv\Scripts\k-select.exe status
.\.venv\Scripts\k-select.exe performance --airflow 300 --neck-in 8 --module 24x24 --output-directory C:/work/kselect-run-001
.\.venv\Scripts\k-select.exe report-verify C:/work/kselect-run-001/performance.pdf --airflow 300 --neck-in 8 --module 24x24
```

`launch` returns immediately; poll `status` until `ready`. `performance` performs
the native calculation **and PDF export** as one verified operation. Output
directories must be new; omit the option for a unique directory in
`~/K-select-runs`. Use `--airflow-unit "l/s"` for L/s; requested and effective
airflow are retained. Use `--border "F22 Surface"` for another supported border.

Results are JSON. Success exits 0, operational errors exit 1, invalid arguments
exit 2. `--json` is accepted for compatibility; JSON is already the default.
`cli-anything-kselect` is an alias. No arguments enters the CLI-Anything REPL
with `help` and `exit`. Installed commands work from any directory;
`python -m cli_anything.kselect` is another entry point.

## MCP

Merge generated `local/mcp.json` into your client's MCP configuration and
reconnect. Example, replacing the absolute path:

```json
{
  "mcpServers": {
    "kselect": {
      "command": "C:/path/to/k-select-agent-toolkit/.venv/Scripts/python.exe",
      "args": ["-m", "cli_anything.kselect.server"]
    }
  }
}
```

The installed `k-select-mcp` command also starts the stdio server.

| Tool | Purpose |
|---|---|
| `get_capabilities` | Validated scope and requirements |
| `get_status` | Executable, screen, lifecycle and dialogs |
| `launch` | Nonblocking start; poll status afterwards |
| `calculate_performance` | Native calculation, PDF export and verification |
| `read_report` | Native PDF, hash, values and conversions |
| `verify_result` | Compare saved PDF with explicit expected inputs |

CLI and MCP share a backend. Desktop calls use a disposable worker, bounded
timeout and cross-process lock. No listening network port is needed. The
[usage skill](skills/cli-anything-kselect/SKILL.md) ships in the source and wheel.

## Evidence and recovery

A successful run contains `performance.pdf`, `result.json` and `journal.json`.
Checks cover model, neck, module, border, airflow, terminal velocity and throw
direction, plus native table/selected-point consistency. Existing directories
are never overwritten. A mismatched PDF returns an error.

Keep the desktop free of competing input during navigation. From a fresh Project
Screen, the tool uses Quick Select; a named project blocks this transition.
An already open performance screen must be **1400**: a wrong model is rejected
by the final PDF check. Return to Product Index to select 1400 automatically.
Nondefault units/terminal velocity are rejected; restore imperial/50 fpm in GRD.

For `blocked`, inspect and resolve the reported dialog before retrying.
For `desktop_interference`, stop competing input and use a fresh run directory.
For `backend_timeout`, inspect status and journal first. The worker stops waiting
but leaves the manufacturer app and evidence intact; it never kills GRD or
dismisses unknown dialogs to manufacture success. A report from an interrupted
run may need to be closed manually.

Two native report quirks are explicit:

- Selected throw is mislabeled `Throw m` in imperial output. It is checked
  against **Throw Feet** before conversion to metres.
- Low-flow selected NC may print 10 while its table shows `-`. `nc_reported`
  retains 10; `selected.nc` is null with a warning. No exact NC or zero noise is asserted.

These checks establish report/request consistency, not an independent validation
of Krueger's algorithms or proof of project compliance.

## Validation

```powershell
.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\python.exe scripts/live_acceptance.py --output-directory C:/work/new-acceptance
```

Offline tests use real native PDF fixtures, installed CLI subprocesses and a real
stdio MCP session. Native acceptance is explicit, invokes installed GRD and
fails when unavailable. Hosted CI covers packaging/protocol/report behavior;
it cannot run proprietary GRD on an unlocked user desktop. See
[validation evidence](docs/validation.md) and [test plan/results](tests/TEST.md).

## License

Apache-2.0. See [NOTICE](NOTICE), [LICENSE](LICENSE) and
[upstream review](docs/upstream-review.md). This independent toolkit is not
affiliated with or endorsed by Krueger or Revalize.
