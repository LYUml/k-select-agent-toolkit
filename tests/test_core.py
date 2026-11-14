from pathlib import Path
import math

import pytest

from cli_anything.kselect.core import KSelectError, PerformanceRequest, parse_report, verify_report, CFM_PER_LPS

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize("airflow", [0, -1, math.nan, math.inf, -math.inf, True, "300", None, 5001])
def test_invalid_airflow(airflow):
    with pytest.raises(KSelectError, match="airflow|Airflow"):
        PerformanceRequest(airflow)


@pytest.mark.parametrize("options", [{"model": "51400"}, {"module": "12x12", "neck_in": 10}, {"neck_in": True}, {"airflow_unit": "m3/h"}, {"border": "invalid"}])
def test_invalid_specification(options):
    with pytest.raises(KSelectError):
        PerformanceRequest(300, **options)


def test_rounding_and_conversion():
    request = PerformanceRequest(300 / CFM_PER_LPS, airflow_unit="l/s")
    assert request.effective_cfm == 300
    assert PerformanceRequest(300.5).effective_cfm == 301
    assert PerformanceRequest(300.49).effective_cfm == 300


def test_duplicate_neck_module_indices():
    assert PerformanceRequest(300, module="12x12").neck_index == 1
    assert PerformanceRequest(300).neck_index == 3
    assert PerformanceRequest(300, neck_in=15).neck_index == 7


def test_real_native_report_units_and_table():
    result = verify_report(FIXTURES / "1400-8in-300cfm.pdf", PerformanceRequest(300))
    assert all(result["checks"].values())
    r = result["report"]
    assert r["selected"] == {"airflow_cfm": 300, "throw_ft": 14, "pressure_in_wc": .11, "nc": 22}
    assert r["si"]["throw_m"] == pytest.approx(4.2672)
    assert r["si"]["pressure_pa"] == pytest.approx(27.3997801)
    assert len(r["table"]["airflow_cfm"]) == 9


def test_low_nc_disagreement_is_preserved():
    r = verify_report(FIXTURES / "1400-8in-112cfm.pdf", PerformanceRequest(112))["report"]
    assert r["selected"]["nc"] is None
    assert r["nc_reported"] == 10
    assert any("selected NC field" in w for w in r["warnings"])


@pytest.mark.parametrize("options", [{"airflow": 112}, {"airflow": 300, "neck_in": 10}, {"airflow": 300, "module": "12x12"}, {"airflow": 300, "border": "F22 Surface"}])
def test_stale_or_mismatched_report_rejected(options):
    with pytest.raises(KSelectError) as exc:
        verify_report(FIXTURES / "1400-8in-300cfm.pdf", PerformanceRequest(**options))
    assert exc.value.code == "result_mismatch"
    assert not all(exc.value.details["checks"].values())


def test_invalid_pdf(tmp_path):
    path = tmp_path / "wrong.pdf"
    path.write_text("not a PDF")
    with pytest.raises(KSelectError) as exc:
        parse_report(path)
    assert exc.value.code == "invalid_report"


def test_broken_pdf(tmp_path):
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"%PDF-broken")
    with pytest.raises(KSelectError):
        parse_report(path)
