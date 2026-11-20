"""CLI 結果碼與檔案輸出。"""

from pathlib import Path

from qcconvert.__main__ import main
from qcconvert.widgets import BELL


def test_cli_check_and_errors(tmp_path: Path, monkeypatch: object) -> None:
    from _pytest.monkeypatch import MonkeyPatch

    assert isinstance(monkeypatch, MonkeyPatch)
    monkeypatch.setenv("QCCONVERT_TARGET", "qpp-cpu")
    source, output = tmp_path / "bell.py", tmp_path / "generated.py"
    source.write_text(BELL)
    assert main([str(source), "--to", "cudaq", "-o", str(output), "--check"]) == 0
    assert "@cudaq.kernel" in output.read_text()
    assert main([str(output), "--to", "qiskit", "--check"]) == 2
    source.write_text("qc = garbage")
    assert main([str(source), "--to", "cudaq"]) == 2
