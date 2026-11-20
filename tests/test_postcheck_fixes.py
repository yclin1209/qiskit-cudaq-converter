"""postcheck（runs/20261120-193502）發現 1–5 的回歸測試。"""

import json
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

from qcconvert import compare, cudaq_to_qiskit, load_kernel
from qcconvert.errors import ConversionError, UnsupportedFeatureError

ROOT = Path(__file__).resolve().parents[1]


# 發現 1：中途測量 + 多個 ClassicalRegister 的 counts 鍵格式


def _mid_two_cregs() -> QuantumCircuit:
    a, b = ClassicalRegister(1, "a"), ClassicalRegister(1, "b")
    qc = QuantumCircuit(QuantumRegister(2, "q"), a, b)
    qc.h(0)
    qc.measure(0, a[0])
    qc.cx(0, 1)
    qc.measure(1, b[0])
    return qc


def test_mid_measurement_multiple_cregs_distribution() -> None:
    report = compare(_mid_two_cregs(), shots=4000, seed=1234)
    assert report.distribution_only and report.statevector_equal is None
    assert all(" " not in key for key in report.qiskit_counts)
    assert set(report.qiskit_counts) == set(report.cudaq_counts) == {"00", "11"}
    assert report.tvd <= 0.05


def test_mid_measurement_uneven_cregs_bit_order() -> None:
    a, b = ClassicalRegister(2, "a"), ClassicalRegister(1, "b")
    qc = QuantumCircuit(QuantumRegister(2, "q"), a, b)
    qc.x(0)
    qc.measure(0, a[1])
    qc.x(0)
    qc.measure(0, b[0])
    qc.measure(1, a[0])
    report = compare(qc, shots=64, seed=7)
    # clbit 全域索引：a[0]=0、a[1]=1、b[0]=2；Qiskit 順序（最高位在左）。
    assert report.qiskit_counts == report.cudaq_counts == {"010": 64}
    assert report.tvd == 0.0


def test_normalize_qiskit_counts_helper() -> None:
    from qcconvert.runner import _normalize_qiskit_counts

    a, b = ClassicalRegister(2, "a"), ClassicalRegister(1, "b")
    qc = QuantumCircuit(QuantumRegister(1), a, b)
    assert _normalize_qiskit_counts({"1 01": 3, "0 10": 2}, qc) == {"101": 3, "010": 2}
    assert _normalize_qiskit_counts({"10": 4}, QuantumCircuit(1, 2)) == {"10": 4}


# 發現 2：qiskit-aer 依賴與缺少時的錯誤訊息


def test_mid_measurement_without_aer_gives_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "qiskit_aer", None)
    with pytest.raises(ConversionError, match="qiskit-aer"):
        compare(_mid_two_cregs(), shots=64)
    plain = QuantumCircuit(1, 1)
    plain.h(0)
    plain.measure(0, 0)
    assert compare(plain, shots=256).tvd <= 0.1


def test_install_instructions_list_qiskit_aer() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert any(dep.startswith("qiskit-aer") for dep in project["dependencies"])
    assert any(dep.startswith("ipywidgets") for dep in project["optional-dependencies"]["colab"])
    notebook = json.loads((ROOT / "colab/qcconvert_demo.ipynb").read_text())
    install = next(
        "".join(cell["source"]) for cell in notebook["cells"] if "pip" in "".join(cell["source"])
    )
    for package in ("'cudaq'", "'qiskit'", "'qiskit-aer'", "'ipywidgets'"):
        assert package in install
    for readme in ("README.md", "colab/README_colab.md"):
        assert "qiskit-aer" in (ROOT / readme).read_text()


# 發現 3：import qcconvert 不應強制需要 ipywidgets


def test_import_without_ipywidgets() -> None:
    code = (
        "import sys\n"
        "sys.modules['ipywidgets'] = None\n"
        "import qcconvert\n"
        "from qiskit import QuantumCircuit\n"
        "qc = QuantumCircuit(2)\nqc.h(0)\nqc.cx(0, 1)\n"
        "assert '@cudaq.kernel' in qcconvert.qiskit_to_cudaq(qc).code\n"
        "assert 'qcconvert.widgets' not in sys.modules\n"
        "try:\n    qcconvert.show()\nexcept ImportError as exc:\n"
        "    assert 'ipywidgets' in str(exc)\n    print('OK')\n"
    )
    done = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT, check=False
    )
    assert done.returncode == 0, done.stderr
    assert "OK" in done.stdout


def test_lazy_show_and_extension_still_work() -> None:
    import qcconvert

    assert callable(qcconvert.show) and callable(qcconvert.load_ipython_extension)
    assert {"show", "load_ipython_extension"} <= set(qcconvert.__all__)
    app = qcconvert.show()
    app.convert()
    assert "@cudaq.kernel" in app.output.value


# 發現 4：_mid_counts 測量擷取


def _mid_kernel(tmp_path: Path, body: str, name: str = "kernel") -> object:
    source = f"import cudaq\n@cudaq.kernel\ndef {name}():\n    q = cudaq.qvector(2)\n{body}"
    return load_kernel(source, name)


def _bell_mid() -> QuantumCircuit:
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.measure(0, 0)
    qc.cx(0, 1)
    qc.measure(1, 1)
    return qc


def test_mid_capture_assigned_measurement(tmp_path: Path) -> None:
    kernel = _mid_kernel(
        tmp_path,
        "    h(q[0])\n    r = mz(q[0])\n    x.ctrl(q[0], q[1])\n    s = mz(q[1])\n",
        "assigned",
    )
    report = compare(_bell_mid(), kernel, shots=4000, seed=1234)
    assert set(report.cudaq_counts) == {"00", "11"}
    assert report.tvd <= 0.05


@pytest.mark.parametrize("basis", ["mx", "my"])
def test_mid_capture_mx_my(basis: str) -> None:
    source = (
        "import cudaq\n@cudaq.kernel\ndef kernel():\n    q = cudaq.qvector(2)\n"
        f"    h(q[0])\n    s(q[0])\n    {basis}(q[0])\n    x.ctrl(q[0], q[1])\n    mz(q[1])\n"
    )
    qc = cudaq_to_qiskit(source).to_qiskit()
    report = compare(qc, load_kernel(source, "kernel"), shots=4000, seed=1234)
    assert report.distribution_only
    assert report.tvd <= 0.05


@pytest.mark.parametrize(
    "body,match",
    [
        ("    h(q[0])\n    cudaq.mz(q[0])\n    x.ctrl(q[0], q[1])\n    mz(q[1])\n", "第 6 行"),
        ("    h(q[0])\n    mz(q[0])\n    x.ctrl(q[0], q[1])\n    mz(q)\n", "第 8 行"),
        (
            (
                "    h(q[0])\n    mz(q[0])\n    x.ctrl(q[0], q[1])\n    for i in range(1):\n"
                "        mz(q[1])\n"
            ),
            "第 9 行",
        ),
        ("    h(q[0])\n    a, b = mz(q[0]), mz(q[1])\n    x.ctrl(q[0], q[1])\n", "第 6 行"),
    ],
)
def test_mid_capture_unsupported_forms(body: str, match: str) -> None:
    from qcconvert.runner import _capture_measurements

    source = f"import cudaq\n@cudaq.kernel\ndef kernel():\n    q = cudaq.qvector(2)\n{body}"
    with pytest.raises(UnsupportedFeatureError, match=match):
        _capture_measurements(source)


# 發現 5：h/x/y/z/swap 的 .adj


@pytest.mark.parametrize(
    "gate,operands",
    [("h", "q[0]"), ("x", "q[0]"), ("y", "q[0]"), ("z", "q[0]"), ("swap", "q[0], q[1]")],
)
def test_self_inverse_adj(gate: str, operands: str) -> None:
    """CUDA-Q 0.17 本身無法編譯 h/x/y/z/swap 的 .adj，故不能做等價測試；轉換器須明確拒絕並提示。"""
    import cudaq

    source = (
        "import cudaq\n@cudaq.kernel\ndef kernel():\n    q = cudaq.qvector(2)\n"
        f"    h(q[0])\n    {gate}.adj({operands})\n"
    )
    with pytest.raises(Exception):  # noqa: B017 - CUDA-Q 編譯錯誤型別不穩定
        cudaq.get_state(load_kernel(source, "kernel"))
    with pytest.raises(UnsupportedFeatureError, match=rf"第 6 行.*{gate}\.adj.*自反"):
        cudaq_to_qiskit(source)
