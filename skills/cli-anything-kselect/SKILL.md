---
name: cli-anything-kselect
description: Operate the installed Krueger K-Select GRD 10.0.2 model 1400 performance calculator through K-Select Agent Toolkit MCP or CLI, export native PDFs and verify saved results. Use for this adapter's supported diffuser performance work, not ADPI or other product families.
---

Use the installed `k-select` or `cli-anything-kselect` command. Both share the
same backend as `k-select-mcp`. In a source checkout, use
`<checkout>/.venv/Scripts/k-select.exe`; setup is `scripts/setup.ps1`.

1. Read `k-select --json capabilities` (MCP: `get_capabilities`).
2. Call `launch`, then poll `status` until `ready`. Launch is nonblocking.
3. Run `performance --airflow 300 --neck-in 8 --module 24x24
   --output-directory C:/work/new-run` (MCP: `calculate_performance`). The output
   directory must be new. Omit it to create a unique directory in `~/K-select-runs`.
4. Read the returned checks, native PDF path, hash, selected values and warnings.
   Reopen with `report-verify <pdf> --airflow 300` / `verify_result` when verifying
   independently of the desktop call.

All command results are JSON. Exit 0 means success; nonzero returns an error
envelope. An empty invocation enters the upstream CLI-Anything REPL.
For l/s input use `--airflow-unit "l/s"`; GRD receives nearest whole CFM and the
effective value is returned. 50 fpm terminal velocity, Horizontal throw only.

Product navigation needs an unlocked desktop and can move the pointer. Avoid
parallel desktop input. A named GRD project blocks automatic Quick Select.
If a performance screen is already open it must be model 1400; the exported PDF
is checked and any wrong model, module, units or airflow is rejected. For a
different model, return to Product Index before invoking this adapter.

For `blocked`, inspect returned dialogs and resolve them before retrying; do not
dismiss arbitrary dialogs or overwrite a project. For `backend_timeout` or a
failed journal, inspect status and saved evidence before using a fresh run
directory. No success result is issued for a stale or mismatched PDF.

The native report mislabels selected throw as `Throw m` in its imperial output;
the adapter checks it against the `Throw Feet` table before converting to SI.
At low flow, native selected NC may print 10 while its table prints `-`:
`nc_reported` preserves 10, and usable `nc` stays null with a warning.
Manufacturer performance is not proof of project compliance or an ADPI result.
