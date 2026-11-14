# Upstream reuse

CLI-Anything: https://github.com/HKUDS/CLI-Anything

Reviewed commit: 34f519533bc175d2fe287ab8316b0dd99bb9cc43 (Apache-2.0).
Read cli-anything-plugin/HARNESS.md. Reuse its actual repl_skin.py unchanged,
namespace/entry-point layout, Click subcommands, JSON output, shared backend,
and native artifact verification workflow. This is a proprietary Windows GUI
adapter, not a headless harness or a claim of full upstream conformance.
No manufacturer algorithms are reimplemented. Undo is not provided for external
desktop calculations; every run writes a new evidence directory.

pywinauto 0.6.9 (BSD-3-Clause) supplies Win32 and UIA control access.
MCP Python SDK 2.3.0 supplies stdio transport. pypdf reads native reports.

Manufacturer: https://www.krueger-hvac.com/public/software/k-select
Observed K-Select 13.3.54 launches independent GRD 10.0.2 (VB6/Crystal Reports).
No supported public command-line calculation endpoint was found in this review.
K-Select binaries/data are prerequisites and are not redistributed.

Prior chat research reviewed: building-services-agent (continue develop general workflow),
and DIALux-agent (查找 DIALux AI 插件). Applied lessons: nonblocking launch,
bounded worker calls, native engine execution, fresh reports, explicit limitations.
