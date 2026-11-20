"""IPython cell magic 驗收。"""

from IPython.core.interactiveshell import InteractiveShell
from qiskit import QuantumCircuit

import qcconvert
from qcconvert.widgets import BELL


def test_cell_magics(monkeypatch: object, capsys: object) -> None:
    from _pytest.capture import CaptureFixture
    from _pytest.monkeypatch import MonkeyPatch

    assert isinstance(monkeypatch, MonkeyPatch)
    assert isinstance(capsys, CaptureFixture)
    monkeypatch.setenv("QCCONVERT_TARGET", "qpp-cpu")
    shell = InteractiveShell.instance()
    qcconvert.load_ipython_extension(shell)
    rendered = shell.run_cell_magic("qiskit2cudaq", "--run --name test_magic_kernel", BELL)
    assert rendered is None  # 不觸發 CUDA-Q 的 latex SVG 呈現。
    kernel = shell.user_ns["test_magic_kernel"]
    assert "@cudaq.kernel" in capsys.readouterr().out
    result = qcconvert.cudaq_to_qiskit(kernel)
    assert isinstance(result.to_qiskit(), QuantumCircuit)
    assert qcconvert.compare(result.to_qiskit(), kernel, shots=128).statevector_equal is True
    source = "import cudaq\n@cudaq.kernel\ndef kernel():\n    q = cudaq.qvector(2)\n    h(q[0])\n    x.ctrl(q[0], q[1])"
    shell.run_cell_magic("cudaq2qiskit", "--name test_magic_qc", source)
    qc = shell.user_ns["test_magic_qc"]
    assert isinstance(qc, QuantumCircuit)
    assert qcconvert.compare(qc).statevector_equal
