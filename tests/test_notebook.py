"""Colab notebook 無頭（headless）執行驗收。"""

from pathlib import Path

import nbformat
from nbclient import NotebookClient


def test_notebook(tmp_path: Path, monkeypatch: object) -> None:
    from _pytest.monkeypatch import MonkeyPatch

    assert isinstance(monkeypatch, MonkeyPatch)
    monkeypatch.setenv("QCCONVERT_SKIP_INSTALL", "1")
    monkeypatch.setenv("QCCONVERT_TARGET", "qpp-cpu")
    notebook = nbformat.read(
        Path(__file__).resolve().parents[1] / "colab/qcconvert_demo.ipynb", as_version=4
    )
    client = NotebookClient(notebook, timeout=600, resources={"metadata": {"path": str(tmp_path)}})
    result = client.execute()
    outputs = "\n".join(
        str(output.get("text", ""))
        for cell in result.cells
        if cell.cell_type == "code"
        for output in cell.outputs
    )
    assert "qpp-cpu" in outputs and "跳過安裝" in outputs
    assert "fidelity" in outputs and "雙欄編輯器" in outputs
