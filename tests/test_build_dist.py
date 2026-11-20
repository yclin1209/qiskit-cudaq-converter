"""Zip 打包與隔離匯入驗收。"""

import subprocess
from pathlib import Path
from zipfile import ZipFile


def test_archive(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    archive_dir = tmp_path / "dist"
    subprocess.run(
        [str(root / ".venv/bin/python"), str(root / "scripts/build_dist.py"), str(archive_dir)],
        check=True,
        capture_output=True,
    )
    archive = archive_dir / "qcconvert_colab.zip"
    with ZipFile(archive) as zf:
        names = zf.namelist()
        assert {"qcconvert/__init__.py", "qcconvert_demo.ipynb", "README_colab.md"} <= set(names)
        assert all(
            ".venv" not in name and "__pycache__" not in name and "tests/" not in name
            for name in names
        )
        zf.extractall(tmp_path / "extracted")
    result = subprocess.run(
        [
            str(root / ".venv/bin/python"),
            "-c",
            "from qiskit import QuantumCircuit; import qcconvert; qc=QuantumCircuit(2); qc.h(0); qc.cx(0,1); print(qcconvert.qiskit_to_cudaq(qc).code)",
        ],
        cwd=tmp_path / "extracted",
        env={"PYTHONPATH": str(tmp_path / "extracted"), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=True,
    )
    assert "@cudaq.kernel" in result.stdout and "x.ctrl" in result.stdout
