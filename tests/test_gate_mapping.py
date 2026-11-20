"""每個支援閘及其受控矩陣（controlled matrix）的前向等價測試。"""

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.circuit.library import MCXGate, get_standard_gate_name_mapping
from qiskit.quantum_info import Statevector

from qcconvert import compare, qiskit_to_cudaq
from qcconvert.equivalence import fidelity

GATES: list[tuple[str, tuple[float, ...], int]] = (
    [(name, (), 1) for name in ("id", "h", "x", "y", "z", "s", "sdg", "t", "tdg", "sx", "sxdg")]
    + [(name, (0.47,), 1) for name in ("rx", "ry", "rz", "p", "u1")]
    + [
        ("u", (0.47, 0.31, -0.28), 1),
        ("u3", (0.47, 0.31, -0.28), 1),
        ("u2", (0.31, -0.28), 1),
        ("r", (0.47, 0.31), 1),
        *[(name, (), 2) for name in ("cx", "cy", "cz", "ch", "swap")],
        *[(name, (0.47,), 2) for name in ("crx", "cry", "crz", "cp", "cu1")],
        ("ccx", (), 3),
        ("cswap", (), 3),
        ("mcx", (), 4),
        *[(name, (0.47,), 2) for name in ("rzz", "rxx", "ryy")],
    ]
)


@pytest.mark.parametrize("name,params,arity", GATES, ids=[item[0] for item in GATES])
@pytest.mark.parametrize("controlled", [False, True], ids=["普通", "受控"])
def test_gate_matrix(name: str, params: tuple[float, ...], arity: int, controlled: bool) -> None:
    mapping = get_standard_gate_name_mapping()
    base = MCXGate(3) if name == "mcx" else mapping[name]
    if params:
        base = base.__class__(*params)
    qc = QuantumCircuit(arity + int(controlled))
    if controlled:
        qc.h(0)
        qc.h(arity)
        if arity > 1:
            qc.h(1)
        qc.append(base.control(1), list(range(arity + 1)))
    else:
        if arity > 1:
            qc.h(0)
            qc.h(arity - 1)
        qc.append(base, list(range(arity)))
    import cudaq

    kernel = qiskit_to_cudaq(qc).to_kernel()
    score = fidelity(np.asarray(Statevector(qc).data), np.asarray(cudaq.get_state(kernel)))
    assert score >= 1 - 1e-6, (name, controlled, score)


def test_barrier_and_global_phase() -> None:
    qc = QuantumCircuit(1)
    qc.h(0)
    qc.barrier(0)
    qc.global_phase = 0.29
    result = qiskit_to_cudaq(qc)
    assert any("barrier" in warning for warning in result.warnings)
    assert any("global_phase" in warning for warning in result.warnings)
    assert compare(qc, shots=80).statevector_equal is True


def test_reset_and_measure() -> None:
    qc = QuantumCircuit(2, 2)
    qc.x(0)
    qc.reset(0)
    qc.x(1)
    qc.measure(0, 0)
    qc.measure(1, 1)
    report = compare(qc, shots=80)
    assert report.cudaq_counts == report.qiskit_counts == {"10": 80}
    assert report.statevector_equal is True
