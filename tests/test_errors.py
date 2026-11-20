"""Qiskit 動態建構與脈衝（pulse）不支援的回歸測試。"""

import pytest
from qiskit import QuantumCircuit
from qiskit.circuit import Gate
from qiskit.circuit.library import StatePreparation

from qcconvert import UnsupportedFeatureError, qiskit_to_cudaq


def _circuit(kind: str) -> QuantumCircuit:
    qc = QuantumCircuit(1, 1)
    if kind == "if_test":
        with qc.if_test((qc.clbits[0], 1)):
            qc.x(0)
    elif kind == "if_else":
        branch = QuantumCircuit(1, 1)
        branch.x(0)
        qc.if_else((qc.clbits[0], 1), branch, None, [0], [0])
    elif kind == "c_if":
        # Qiskit 2.x 的 InstructionSet.c_if 已移除；模擬舊式條件 Instruction。
        gate = Gate("legacy", 1, [])
        gate.condition = (qc.clbits[0], 1)
        qc.append(gate, [0])
    elif kind == "while_loop":
        with qc.while_loop((qc.clbits[0], 1)):
            qc.x(0)
    elif kind == "for_loop":
        with qc.for_loop(range(2)):
            qc.x(0)
    elif kind == "switch":
        with qc.switch(qc.clbits[0]) as case, case(0):
            qc.x(0)
    elif kind == "initialize":
        qc.initialize([1, 0], 0)
    elif kind == "StatePreparation":
        qc.append(StatePreparation([1, 0]), [0])
    elif kind == "delay":
        qc.delay(10, 0)
    elif kind == "pulse":
        # Qiskit 2.x 沒有 pulse／add_calibration API：以命名閘代表脈衝輸入。
        qc.append(Gate("calibrated_gate", 1, []), [0])
    return qc


@pytest.mark.parametrize(
    "kind,expected",
    [
        ("if_test", "if_test"),
        ("if_else", "if_test"),
        ("c_if", "c_if"),
        ("while_loop", "while_loop"),
        ("for_loop", "for_loop"),
        ("switch", "switch_case"),
        ("initialize", "initialize"),
        ("StatePreparation", "state_preparation"),
        ("delay", "delay"),
        ("pulse", "pulse"),
    ],
)
def test_unsupported_qiskit_construct(kind: str, expected: str) -> None:
    qc = _circuit(kind)
    with pytest.raises(UnsupportedFeatureError, match=expected):
        qiskit_to_cudaq(qc, decompose_unknown=False)


@pytest.mark.parametrize(
    "kind", ["if_test", "c_if", "while_loop", "for_loop", "switch", "delay", "pulse"]
)
def test_forbidden_even_with_decomposition(kind: str) -> None:
    with pytest.raises(UnsupportedFeatureError):
        qiskit_to_cudaq(_circuit(kind), decompose_unknown=True)
