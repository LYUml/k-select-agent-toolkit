# Test plan

Written before test implementation.

- test_core.py: input validation, unit conversion, report extraction and stale/mismatched report rejection (about 20 cases).
- test_cli.py: installed commands, JSON errors, REPL exit and help from a foreign working directory (about 6 cases).
- test_mcp.py: real stdio initialization, tool listing, status and validation errors (about 3 cases).
- live_acceptance.py: explicit native acceptance, never silently skipped or mocked. Launch/status, select 1400, set neck and border, maximum/minimum/repeated airflow, export fresh PDFs, parse and verify each requested condition. Reopen a report to independently verify the saved evidence. Test failure paths and recovery.

Offline CI tests do not claim desktop acceptance. Live acceptance is a separate command requiring installed GRD 10.0.2 and an interactive unlocked Windows desktop. Artifacts are private in local/; a sanitized acceptance summary is published in docs/.

## Final offline results

41 passed, zero skipped. Clean environment with the built wheel installed.

```text
tests/test_backend.py::test_native_timeout_has_recovery_context PASSED   [  2%]
tests/test_backend.py::test_broken_worker_json_is_not_success PASSED     [  4%]
tests/test_backend.py::test_structured_worker_error_is_preserved PASSED  [  7%]
tests/test_backend.py::test_missing_installation_returns_actionable_error PASSED [  9%]
tests/test_backend.py::test_competing_process_cannot_use_desktop PASSED  [ 12%]
tests/test_backend.py::test_restricted_mcp_environment_restores_windows_com_paths PASSED [ 14%]
tests/test_backend.py::test_explicit_windows_com_path_override_is_preserved PASSED [ 17%]
tests/test_cli.py::test_installed_help_foreign_directory PASSED          [ 19%]
tests/test_cli.py::test_capabilities_foreign_directory PASSED            [ 21%]
tests/test_cli.py::test_json_default_does_not_enter_repl PASSED          [ 24%]
tests/test_cli.py::test_invalid_arguments_are_json[args0] PASSED         [ 26%]
tests/test_cli.py::test_invalid_arguments_are_json[args1] PASSED         [ 29%]
tests/test_cli.py::test_invalid_arguments_are_json[args2] PASSED         [ 31%]
tests/test_cli.py::test_invalid_arguments_are_json[args3] PASSED         [ 34%]
tests/test_cli.py::test_repl_exit PASSED                                 [ 36%]
tests/test_cli.py::test_cli_reads_real_fixture_from_foreign_directory PASSED [ 39%]
tests/test_core.py::test_invalid_airflow[0] PASSED                       [ 41%]
tests/test_core.py::test_invalid_airflow[-1] PASSED                      [ 43%]
tests/test_core.py::test_invalid_airflow[nan] PASSED                     [ 46%]
tests/test_core.py::test_invalid_airflow[inf] PASSED                     [ 48%]
tests/test_core.py::test_invalid_airflow[-inf] PASSED                    [ 51%]
tests/test_core.py::test_invalid_airflow[True] PASSED                    [ 53%]
tests/test_core.py::test_invalid_airflow[300] PASSED                     [ 56%]
tests/test_core.py::test_invalid_airflow[None] PASSED                    [ 58%]
tests/test_core.py::test_invalid_airflow[5001] PASSED                    [ 60%]
tests/test_core.py::test_invalid_specification[options0] PASSED          [ 63%]
tests/test_core.py::test_invalid_specification[options1] PASSED          [ 65%]
tests/test_core.py::test_invalid_specification[options2] PASSED          [ 68%]
tests/test_core.py::test_invalid_specification[options3] PASSED          [ 70%]
tests/test_core.py::test_invalid_specification[options4] PASSED          [ 73%]
tests/test_core.py::test_rounding_and_conversion PASSED                  [ 75%]
tests/test_core.py::test_duplicate_neck_module_indices PASSED            [ 78%]
tests/test_core.py::test_real_native_report_units_and_table PASSED       [ 80%]
tests/test_core.py::test_low_nc_disagreement_is_preserved PASSED         [ 82%]
tests/test_core.py::test_stale_or_mismatched_report_rejected[options0] PASSED [ 85%]
tests/test_core.py::test_stale_or_mismatched_report_rejected[options1] PASSED [ 87%]
tests/test_core.py::test_stale_or_mismatched_report_rejected[options2] PASSED [ 90%]
tests/test_core.py::test_stale_or_mismatched_report_rejected[options3] PASSED [ 92%]
tests/test_core.py::test_invalid_pdf PASSED                              [ 95%]
tests/test_core.py::test_broken_pdf PASSED                               [ 97%]
tests/test_mcp.py::test_real_stdio_protocol PASSED                       [100%]
============================= 41 passed in 2.62s ==============================
```

Native acceptance is documented separately in docs/validation.md.
