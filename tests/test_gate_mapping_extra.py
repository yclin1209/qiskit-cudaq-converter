"""批次 A 的閘、取樣、錯誤與原始碼回歸測試。"""

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter, ParameterVector

from qcconvert import ConversionError, UnsupportedFeatureError, compare, qiskit_to_cudaq
from qcconvert.equivalence import fidelity


@pytest.mark.parametrize(
    "gate,params",
    [
        ("h", ()),
        ("x", ()),
        ("y", ()),
        ("z", ()),
        ("s", ()),
        ("sdg", ()),
        ("t", ()),
        ("tdg", ()),
        ("sx", ()),
        ("sxdg", ()),
        ("rx", (0.7,)),
        ("ry", (0.7,)),
        ("rz", (0.7,)),
        ("p", (0.7,)),
        ("u", (0.4, 0.5, 0.6)),
        ("u1", (0.4,)),
        ("u2", (0.4, 0.5)),
        ("r", (0.4, 0.5)),
    ],
)
@pytest.mark.parametrize("controlled", [False, True])
def test_single_gates(gate: str, params: tuple[float, ...], controlled: bool) -> None:
    qc = QuantumCircuit(2 if controlled else 1)
    target = int(controlled)
    if controlled:
        qc.h(0)
        from qiskit.circuit.library import get_standard_gate_name_mapping

        operation = get_standard_gate_name_mapping()[gate]
        if params:
            operation = operation.__class__(*params)
        qc.append(operation.control(), [0, 1])
    else:
        if gate in {"u1", "u2"}:
            from qiskit.circuit.library import U1Gate, U2Gate

            qc.append((U1Gate if gate == "u1" else U2Gate)(*params), [target])
        else:
            getattr(qc, gate)(*params, target)
    report = compare(qc, shots=100, seed=1234)
    assert report.statevector_equal, (gate, controlled, report.fidelity)


@pytest.mark.parametrize(
    "gate,params",
    [
        ("cx", ()),
        ("cy", ()),
        ("cz", ()),
        ("ch", ()),
        ("swap", ()),
        ("crx", (0.4,)),
        ("cry", (0.4,)),
        ("crz", (0.4,)),
        ("cp", (0.4,)),
        ("ccx", ()),
        ("cswap", ()),
        ("rzz", (0.4,)),
        ("rxx", (0.4,)),
        ("ryy", (0.4,)),
    ],
)
def test_multi_gates(gate: str, params: tuple[float, ...]) -> None:
    count = 3 if gate in {"ccx", "cswap"} else 2
    qc = QuantumCircuit(count)
    qc.h(0)
    getattr(qc, gate)(*params, *range(count))
    assert compare(qc, shots=100).statevector_equal, gate


def test_source_selection() -> None:
    src = "from qiskit import QuantumCircuit\na = QuantumCircuit(1)\nqc = QuantumCircuit(2)\nb = QuantumCircuit(3)"
    assert qiskit_to_cudaq(src).circuit.num_qubits == 2
    assert qiskit_to_cudaq(src.replace("qc =", "other =")).circuit.num_qubits == 3
    with pytest.raises(ConversionError, match="找不到 QuantumCircuit"):
        qiskit_to_cudaq("x = 1")
    with pytest.raises(ConversionError, match="第 1 行"):
        qiskit_to_cudaq("if :")


def test_unsupported() -> None:
    qc = QuantumCircuit(1)
    qc.delay(10, 0)
    with pytest.raises(UnsupportedFeatureError, match="delay"):
        qiskit_to_cudaq(qc)


def test_parameters() -> None:
    theta = Parameter("theta")
    vector = ParameterVector("v", 2)
    qc = QuantumCircuit(1)
    qc.rx(theta + vector[0], 0)
    qc.ry(vector[1], 0)
    result = qiskit_to_cudaq(qc)
    assert "list[float]" in result.code
    for a in (0.1, 0.4, 0.8):
        import cudaq
        from qiskit.quantum_info import Statevector

        bound = qc.assign_parameters({theta: a, vector[0]: 0.2, vector[1]: 0.3})
        assert (
            fidelity(
                np.asarray(Statevector(bound).data),
                np.asarray(cudaq.get_state(result.to_kernel(), a, [0.2, 0.3])),
            )
            > 1 - 1e-6
        )


def test_bit_order() -> None:
    qc = QuantumCircuit(3)
    qc.x(0)
    report = compare(qc, shots=100)
    assert report.cudaq_counts == report.qiskit_counts == {"001": 100}


def test_random_corpus() -> None:
    import cudaq
    from qiskit.quantum_info import Statevector

    rng = np.random.default_rng(4831)
    from qcconvert import cudaq_to_qiskit

    for index in range(200):
        count = int(rng.integers(1, 6))
        qc = QuantumCircuit(count)
        theta = Parameter(f"theta_{index}")
        depth = int(rng.integers(1, 21))
        qc.rx(theta, int(rng.integers(0, count)))
        for _ in range(depth - 1):
            gate = rng.choice(
                ["h", "x", "sx", "rz", "ry", "p", "cx", "rzz"]
                if count > 1
                else ["h", "x", "sx", "rz", "ry", "p"]
            )
            qubits = rng.choice(count, size=2 if gate in {"cx", "rzz"} else 1, replace=False)
            if gate in {"rz", "ry", "p", "rzz"}:
                getattr(qc, gate)(float(rng.uniform(-2, 2)), *map(int, qubits))
            else:
                getattr(qc, gate)(*map(int, qubits))
        angle = float(rng.uniform(-2, 2))
        bound = qc.assign_parameters({theta: angle})
        generated = qiskit_to_cudaq(qc)
        kernel = generated.to_kernel()
        assert (
            fidelity(
                np.asarray(Statevector(bound).data), np.asarray(cudaq.get_state(kernel, angle))
            )
            > 1 - 1e-6
        )
        if index < 50:
            back = (
                cudaq_to_qiskit(generated.code).to_qiskit().assign_parameters({theta.name: angle})
            )
            assert (
                fidelity(np.asarray(Statevector(bound).data), np.asarray(Statevector(back).data))
                > 1 - 1e-6
            )


def test_measurements_and_warnings() -> None:
    from qiskit.circuit import ClassicalRegister, QuantumRegister

    a, b = QuantumRegister(2, "alpha"), QuantumRegister(1, "beta")
    c, d = ClassicalRegister(1, "first"), ClassicalRegister(2, "second")
    qc = QuantumCircuit(a, b, c, d)
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.barrier()
    qc.measure(0, 2)
    qc.measure(2, 0)
    result = qiskit_to_cudaq(qc)
    assert result.circuit.qreg_names == [("alpha", 2), ("beta", 1)]
    assert "alpha: q[0:2]" in result.code
    assert "barrier" in result.warnings[0]
    report = compare(qc, shots=4000)
    assert report.statevector_equal and report.tvd <= 0.05
    assert set(report.cudaq_counts) == {"000", "101"}


def test_mid_measurement() -> None:
    qc = QuantumCircuit(1, 1)
    qc.h(0)
    qc.measure(0, 0)
    qc.x(0)
    report = compare(qc, shots=4000)
    assert report.distribution_only and report.statevector_equal is None
    assert report.tvd <= 0.05


def test_errors_and_decomposition() -> None:
    from qiskit.circuit.library import XGate

    qc = QuantumCircuit(2)
    qc.append(XGate().control(ctrl_state=0), [0, 1])
    with pytest.raises(UnsupportedFeatureError, match="ctrl_state"):
        qiskit_to_cudaq(qc)
    qc = QuantumCircuit(1)
    qc.initialize([1, 0], 0)
    with pytest.raises(UnsupportedFeatureError, match="initialize"):
        qiskit_to_cudaq(qc, decompose_unknown=False)
    with pytest.raises(ConversionError, match="第 2 行"):
        qiskit_to_cudaq("x = 1\nraise ValueError('broken')")


def test_misc() -> None:
    from qcconvert.cudaq_io import load_kernel
    from qcconvert.qiskit_io import from_ir, to_source

    qc = QuantumCircuit(1)
    qc.h(0)
    result = qiskit_to_cudaq(qc)
    assert load_kernel(result.code, "kernel") is result.to_kernel()
    assert from_ir(result.circuit) == qc
    assert "qc.h(0)" in to_source(result.circuit)
    with pytest.raises(ConversionError, match="無效 kernel"):
        qiskit_to_cudaq(qc, kernel_name="not valid")
    with pytest.raises(ConversionError, match="反向"):
        result.to_qiskit()
