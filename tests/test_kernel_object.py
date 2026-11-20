"""實體 kernel 經 synthesize 與 OpenQASM 2 的回歸測試。"""

import cudaq
import numpy as np
import pytest
from qiskit.quantum_info import Statevector

from qcconvert import cudaq_to_qiskit, load_kernel
from qcconvert.equivalence import fidelity


@pytest.mark.parametrize(
    "gate,arguments",
    [("h", ""), ("x", ""), ("swap", "q[0], q[1]"), ("r1", "0.3, q[0]"), ("rx", "theta, q[0]")],
)
def test_object(gate: str, arguments: str) -> None:
    source = f"import cudaq\n@cudaq.kernel\ndef kernel({'theta: float' if gate == 'rx' else ''}):\n    q = cudaq.qvector(2)\n    {gate}({arguments or 'q[0]'})\n"
    kernel = load_kernel(source, "kernel")
    args = (0.4,) if gate == "rx" else ()
    result = cudaq_to_qiskit(kernel, args=args)
    assert (
        fidelity(
            np.asarray(Statevector(result.to_qiskit()).data),
            np.asarray(cudaq.get_state(kernel, *args)),
        )
        > 1 - 1e-6
    )
    assert "OPENQASM" not in result.code
    if gate == "r1":
        assert not any("r1" in warning for warning in result.warnings)


def test_controlled_rz_translation_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    source = "import cudaq\n@cudaq.kernel\ndef kernel():\n    q = cudaq.qvector(2)\n    h(q[0])\n    r1.ctrl(0.3, q[0], q[1])\n"
    kernel = load_kernel(source, "kernel")
    original = cudaq.translate(kernel, format="openqasm2")
    # 受控 rz 的 OpenQASM 2 名稱出現時才警告；一般 rz 不應誤報。
    monkeypatch.setattr(
        cudaq,
        "translate",
        lambda _kernel, format: (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncrz(0.3) q[0],q[1];\n'
        ),
    )
    assert any("r1" in warning for warning in cudaq_to_qiskit(kernel).warnings)
    monkeypatch.setattr(cudaq, "translate", lambda _kernel, format: original)
    assert not any("r1" in warning for warning in cudaq_to_qiskit(kernel).warnings)
