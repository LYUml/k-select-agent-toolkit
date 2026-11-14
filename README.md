# K-Select Agent Toolkit

MCP and CLI for Krueger K-Select GRD.

Requires Windows, Python 3.12, installed GRD 10.0.2 and an unlocked desktop.
Supports model 1400 performance calculations, native PDF export and result verification.
Horizontal throw, 50 fpm only. ADPI and project schedules are not supported.

## Install

```powershell
git clone https://github.com/LYUml/k-select-agent-toolkit.git
cd k-select-agent-toolkit
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
```

## Use

```powershell
.\.venv\Scripts\k-select.exe launch
.\.venv\Scripts\k-select.exe status
.\.venv\Scripts\k-select.exe performance --airflow 300
```

For MCP, merge `local/mcp.json` into your client configuration and reconnect.
Run `k-select --help` or `k-select --json capabilities` for options and supported specifications.
Set `KSELECT_GRD_EXE` for a custom installation path.

Apache-2.0. Includes the CLI-Anything REPL; see [NOTICE](NOTICE).
