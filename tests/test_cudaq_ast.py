"""CUDA-Q 原始碼白名單與反向閘矩陣測試。"""

import numpy as np
import pytest
from qiskit.quantum_info import Statevector

from qcconvert import cudaq_to_qiskit, load_kernel
from qcconvert.equivalence import fidelity


@pytest.mark.parametrize(
    "gate,args",
    [
        ("h", ""),
        ("x", ""),
        ("y", ""),
        ("z", ""),
        ("s", ""),
        ("sdg", ""),
        ("t", ""),
        ("tdg", ""),
        ("rx", "0.37, "),
        ("ry", "0.37, "),
        ("rz", "0.37, "),
        ("r1", "0.37, "),
        ("u3", "0.2, 0.3, 0.4, "),
        ("swap", ""),
    ],
)
def test_gate_matrix(gate: str, args: str) -> None:
    operands = "q[0], q[1]" if gate == "swap" else "q[1]"
    source = f"import cudaq\n@cudaq.kernel\ndef kernel():\n    q = cudaq.qvector(2)\n    h(q[0])\n    {gate}({args}{operands})\n"
    result = cudaq_to_qiskit(source)
    actual = np.asarray(Statevector(result.to_qiskit()).data)
    expected = np.asarray(__import__("cudaq").get_state(load_kernel(source, "kernel")))
    assert fidelity(actual, expected) > 1 - 1e-6, gate


@pytest.mark.parametrize(
    "gate,args",
    [
        ("h", ""),
        ("x", ""),
        ("y", ""),
        ("z", ""),
        ("s", ""),
        ("t", ""),
        ("rx", "0.4, "),
        ("ry", "0.4, "),
        ("rz", "0.4, "),
        ("r1", "0.4, "),
        ("u3", "0.2, 0.3, 0.4, "),
        ("swap", ""),
    ],
)
def test_control(gate: str, args: str) -> None:
    operands = "q[0], q[1], q[2]" if gate == "swap" else "q[0], q[1]"
    source = f"import cudaq\n@cudaq.kernel\ndef kernel():\n    q = cudaq.qvector({3 if gate == 'swap' else 2})\n    h(q[0])\n    {gate}.ctrl({args}{operands})\n"
    result = cudaq_to_qiskit(source)
    assert (
        fidelity(
            np.asarray(Statevector(result.to_qiskit()).data),
            np.asarray(__import__("cudaq").get_state(load_kernel(source, "kernel"))),
        )
        > 1 - 1e-6
    )


def test_loop_registers_and_parameters() -> None:
    source = """import cudaq
import numpy as np
@cudaq.kernel
def kernel(theta: list[float], phi: float):
    left = cudaq.qvector(2)
    right = cudaq.qubit()
    for i in range(2):
        rx(2 * theta[i] + np.pi / 2, left[i])
    x.ctrl(left, right)
    rz(phi, right)
"""
    result = cudaq_to_qiskit(source)
    assert result.circuit.qreg_names == [("left", 2), ("right", 1)]
    assert len(result.circuit.ops) == 4
    assert "theta[0]" in str(result.circuit.ops[0].params)
    bound = result.to_qiskit().assign_parameters({"theta[0]": 0.1, "theta[1]": 0.2, "phi": 0.3})
    assert (
        fidelity(
            np.asarray(Statevector(bound).data),
            np.asarray(
                __import__("cudaq").get_state(load_kernel(source, "kernel"), [0.1, 0.2], 0.3)
            ),
        )
        > 1 - 1e-6
    )


@pytest.mark.parametrize("controls", ["q[0], q[1]", "[q[0], q[1]]"])
def test_multiple_controls(controls: str) -> None:
    source = f"import cudaq\n@cudaq.kernel\ndef kernel():\n    q = cudaq.qvector(3)\n    h(q[0])\n    h(q[1])\n    x.ctrl({controls}, q[2])\n"
    result = cudaq_to_qiskit(source)
    assert result.circuit.ops[-1].controls == (0, 1)
    assert (
        fidelity(
            np.asarray(Statevector(result.to_qiskit()).data),
            np.asarray(__import__("cudaq").get_state(load_kernel(source, "kernel"))),
        )
        > 1 - 1e-6
    )


@pytest.mark.parametrize("gate", ["mz", "mx", "my"])
def test_measurement(gate: str) -> None:
    source = f"import cudaq\n@cudaq.kernel\ndef kernel():\n    q = cudaq.qvector(2)\n    h(q[0])\n    {gate}(q)\n"
    result = cudaq_to_qiskit(source)
    assert result.to_qiskit().num_clbits == 2
    assert len(result.to_qiskit().data) >= 2
    import cudaq
    from qiskit.quantum_info import Statevector

    reference = result.to_qiskit().remove_final_measurements(inplace=False)
    probabilities = Statevector(reference).probabilities_dict()
    sampled = dict(cudaq.sample(load_kernel(source, "kernel"), shots_count=4000).items())
    # CUDA-Q 的 bitstring 左端是 qubit 0；Qiskit 的右端才是 qubit 0。
    observed = {key[::-1]: count / 4000 for key, count in sampled.items()}
    assert set(observed) <= set(probabilities)
    assert sum(abs(observed.get(key, 0) - value) for key, value in probabilities.items()) / 2 < 0.05


def test_reset_distribution() -> None:
    source = "import cudaq\n@cudaq.kernel\ndef kernel():\n    q = cudaq.qvector(1)\n    x(q[0])\n    reset(q[0])\n    mz(q[0])\n"
    result = cudaq_to_qiskit(source)
    import cudaq

    assert result.to_qiskit().count_ops()["reset"] == 1
    assert dict(cudaq.sample(load_kernel(source, "kernel"), shots_count=128).items()) == {"0": 128}


@pytest.mark.parametrize("gate", ["s", "t", "rx", "ry", "rz", "r1", "u3"])
def test_adj(gate: str) -> None:
    args = (
        "0.2, 0.3, 0.4, " if gate == "u3" else "0.2, " if gate in {"rx", "ry", "rz", "r1"} else ""
    )
    source = f"import cudaq\n@cudaq.kernel\ndef kernel():\n    q = cudaq.qvector(1)\n    h(q[0])\n    {gate}.adj({args}q[0])\n"
    result = cudaq_to_qiskit(source)
    assert (
        fidelity(
            np.asarray(Statevector(result.to_qiskit()).data),
            np.asarray(__import__("cudaq").get_state(load_kernel(source, "kernel"))),
        )
        > 1 - 1e-6
    )


@pytest.mark.parametrize("gate", ["sdg", "tdg"])
@pytest.mark.parametrize("suffix,operands", [("ctrl", "q[0], q[1]"), ("adj", "q[1]")])
def test_inverse_modifier_rejected(gate: str, suffix: str, operands: str) -> None:
    from qcconvert.errors import UnsupportedFeatureError

    source = f"import cudaq\n@cudaq.kernel\ndef kernel():\n    q = cudaq.qvector(2)\n    {gate}.{suffix}({operands})\n"
    with pytest.raises(UnsupportedFeatureError, match=gate + r"\." + suffix):
        cudaq_to_qiskit(source)


@pytest.mark.parametrize(
    "gate,args",
    [(gate, "") for gate in ("cx", "cy", "cz", "ch", "cs", "ct")]
    + [(gate, "0.3, ") for gate in ("crx", "cry", "crz", "cr1")],
)
def test_kernel_control_alias(gate: str, args: str) -> None:
    source = f"import cudaq\n@cudaq.kernel\ndef kernel():\n    q = cudaq.qvector(2)\n    h(q[0])\n    {gate}({args}q[0], q[1])\n"
    result = cudaq_to_qiskit(source)
    assert result.circuit.ops[-1].controls == (0,)
    assert (
        fidelity(
            np.asarray(Statevector(result.to_qiskit()).data),
            np.asarray(__import__("cudaq").get_state(load_kernel(source, "kernel"))),
        )
        > 1 - 1e-6
    )
