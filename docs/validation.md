# Validation, 2026-11-14

Windows 11, Python 3.12, installed K-Select 13.3.54 / GRD 10.0.2.
These are synthetic toolkit acceptance conditions, not a building design.

## Final native regression

The final 15-case run completed without retries. Each case invoked the real GRD
engine, exported a new Crystal Reports PDF, compared its inputs/results, then
reopened the PDF independently. The sanitized [case records](native-acceptance.json)
retain requested inputs, selected values, checks and report SHA256 values.

- 300 / 112 / repeated 300 CFM, plus equivalent L/s input.
- All eight advertised neck/module combinations.
- All four advertised borders.
- Horizontal pattern and 50 fpm terminal velocity verified in every report.

For 1400, 8-inch neck, 24x24, F23 T-Bar:

| CFM | Throw, ft | Pressure, in.w.c. | NC |
|---:|---:|---:|---|
| 300 | 14.0 | 0.11 | 22 |
| 112 | 8.0 | 0.01 | Unknown; selected native field prints 10 and table prints '-' |

Five consecutive cold-start runs passed during development after the transient
window enumeration fix. Earlier trials failed on stale handles, modal timing,
filename initialization and competing focus; these failures prompted the final
changes. They are not counted as successful acceptance runs.

## Installation and MCP

The wheel was installed into an independent virtual environment. A real MCP
stdio client launched that installed server from a foreign working directory,
cold-started GRD with the default restricted MCP environment, navigated to 1400,
calculated 300 CFM, exported a native PDF, and independently verified it through
the MCP `verify_result` tool. The [MCP acceptance record](mcp-acceptance.json)
retains its checks and report hash.

The PowerShell setup script was executed successfully and generated an absolute
interpreter configuration. Dependency checks passed. Offline tests passed in
the clean environment: **41 passed**, including installed CLI subprocesses,
real MCP protocol exchange, real native PDF fixtures, invalid inputs, stale
request/report rejection, worker timeout/error propagation, missing software
and cross-process desktop locking. Full named results are in [TEST.md](../tests/TEST.md).

## Limits

Hosted CI verifies portable package/report/protocol behavior, not desktop engine
execution. The native results above were measured on this machine. They do not
prove compatibility with every Windows configuration, DPI, locale or future
GRD version. The program requires an unlocked desktop; competing input can
cause an explicit failure. ADPI, other product families and project schedules
are outside v0.1. Native PDF checks verify consistency with the request and its
own native table, not the manufacturer's calculation algorithm or compliance.

Raw run directories remain local. Two unmodified, synthetic native PDFs are
included as parser fixtures. No manufacturer executable/database, private
project, credential or customer document is distributed.

MCP cold-start regression identified missing CommonProgramFiles environment
variables (native error 335 / 8007007E). The launcher restores only these standard
COM component paths from Windows registry, preserving client overrides. Two
offline controls verify reconstruction and override preservation. The final cold
MCP acceptance used the default client environment, without extra client variables.
