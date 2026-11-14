# Test plan

Written before test implementation.

- test_core.py: input validation, unit conversion, report extraction and stale/mismatched report rejection (about 20 cases).
- test_cli.py: installed commands, JSON errors, REPL exit and help from a foreign working directory (about 6 cases).
- test_mcp.py: real stdio initialization, tool listing, status and validation errors (about 3 cases).
- live_acceptance.py: explicit native acceptance, never silently skipped or mocked. Launch/status, select 1400, set neck and border, maximum/minimum/repeated airflow, export fresh PDFs, parse and verify each requested condition. Reopen a report to independently verify the saved evidence. Test failure paths and recovery.

Offline CI tests do not claim desktop acceptance. Live acceptance is a separate command requiring installed GRD 10.0.2 and an interactive unlocked Windows desktop. Artifacts are private in local/; a sanitized acceptance summary is published in docs/.
