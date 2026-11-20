"""測量映射、參數名稱與反向轉換的邊界回歸。"""

import subprocess
import sys
from pathlib import Path

import pytest
from qiskit import QuantumCircuit
from qiskit.circuit import ClassicalRegister, Parameter, ParameterVector, QuantumRegister
from qiskit.quantum_info import Statevector

from qcconvert import compare, cudaq_to_qiskit, load_kernel, qiskit_to_cudaq


def test_measurement_out_of_order() -> None:
    qc = QuantumCircuit(3, 2)
    qc.x(2)
    qc.measure(2, 0)
    qc.measure(0, 1)
    report = compare(qc, shots=128, seed=1234)
    assert report.qiskit_counts == report.cudaq_counts == {"01": 128}
    assert report.tvd == 0


def test_compare_parameter_vector_args() -> None:
    vector = ParameterVector("v", 2)
    qc = QuantumCircuit(1)
    qc.rx(vector[0], 0)
    qc.ry(vector[1], 0)
    report = compare(qc, args=([0.3, 0.7],), shots=128, seed=1234)
    assert report.statevector_equal is True
    assert report.tvd <= 0.05


def test_compare_mixed_scalar_vector_signature() -> None:
    vector = ParameterVector("a", 2)
    scalar = Parameter("z")
    qc = QuantumCircuit(1)
    qc.rx(vector[0], 0)
    qc.ry(scalar + vector[1], 0)
    generated = qiskit_to_cudaq(qc)
    assert "z: float, a: list[float]" in generated.code
    report = compare(qc, generated.to_kernel(), args=(0.2, [0.3, 0.4]), shots=4000)
    assert report.statevector_equal is True
    assert report.tvd <= 0.05


@pytest.mark.parametrize(
    "name",
    [
        "rx",
        "q",
        "cudaq",
    ],
)
def test_parameter_identifier_conflict(name: str) -> None:
    qc = QuantumCircuit(1)
    qc.rx(Parameter(name), 0)
    generated = qiskit_to_cudaq(qc)
    assert f"param_{name}: float" in generated.code
    import cudaq
    import numpy as np
    from qiskit.quantum_info import Statevector

    actual = np.asarray(cudaq.get_state(generated.to_kernel(), 0.37))
    expected = np.asarray(Statevector(qc.assign_parameters({name: 0.37})).data)
    assert abs(np.vdot(actual, expected)) ** 2 >= 1 - 1e-6


@pytest.mark.parametrize(
    "name", ["x", "h", "mz", "r1", "u3", "reset", "math", "np", "open", "len", "for"]
)
def test_reserved_parameter_names(name: str) -> None:
    qc = QuantumCircuit(1)
    qc.rx(Parameter(name), 0)
    generated = qiskit_to_cudaq(qc)
    assert f"param_{name}: float" in generated.code
    assert compare(qc, generated.to_kernel(), args=(0.3,), shots=128).statevector_equal is True


def test_ghz_distribution() -> None:
    qc = QuantumCircuit(3, 3)
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.measure(range(3), range(3))
    report = compare(qc, shots=4000, seed=1234)
    assert report.statevector_equal is True
    assert set(report.qiskit_counts) == set(report.cudaq_counts) == {"000", "111"}
    assert report.tvd <= 0.05


def test_reverse_reset_and_adjoints() -> None:
    source = """import cudaq
@cudaq.kernel
def kernel():
    q = cudaq.qvector(1)
    x(q[0])
    reset(q[0])
    s.adj(q[0])
    t.adj(q[0])
"""
    result = cudaq_to_qiskit(source)
    assert [instruction.operation.name for instruction in result.to_qiskit().data] == [
        "x",
        "reset",
        "sdg",
        "tdg",
    ]


def test_reverse_register_names() -> None:
    source = """import cudaq
@cudaq.kernel
def kernel():
    left = cudaq.qvector(2)
    right = cudaq.qubit()
    h(left[0])
    x.ctrl(left[0], right)
"""
    result = cudaq_to_qiskit(source)
    qc = result.to_qiskit()
    assert [(reg.name, reg.size) for reg in qc.qregs] == [("left", 2), ("right", 1)]
    assert result.circuit.ops[-1].controls == (0,)
    assert result.circuit.ops[-1].targets == (2,)


def test_partial_multiple_cregs_distribution() -> None:
    first = ClassicalRegister(2, "first")
    second = ClassicalRegister(1, "second")
    qc = QuantumCircuit(QuantumRegister(3), first, second)
    qc.x(2)
    qc.measure(2, second[0])
    qc.measure(0, first[1])
    report = compare(qc, shots=128, seed=1234)
    assert report.qiskit_counts == report.cudaq_counts == {"100": 128}


def test_no_measurement_one_qubit() -> None:
    qc = QuantumCircuit(1)
    qc.x(0)
    report = compare(qc, shots=128, seed=1234)
    assert report.qiskit_counts == report.cudaq_counts == {"1": 128}


def test_zero_qubit_source() -> None:
    qc = QuantumCircuit(0)
    generated = qiskit_to_cudaq(qc)
    assert "cudaq.qvector(0)" in generated.code


def test_load_kernel_repeated_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from qcconvert import cudaq_io

    monkeypatch.setattr(cudaq_io.tempfile, "gettempdir", lambda: str(tmp_path))
    code = "import cudaq\n@cudaq.kernel\ndef kernel():\n    q = cudaq.qvector(1)\n    x(q[0])\n"
    first = load_kernel(code, "kernel")
    assert all(load_kernel(code, "kernel") is first for _ in range(3))
    assert len(list((tmp_path / "qcconvert_kernels").glob("*.py"))) == 1


def test_real_cli_and_build(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    source = tmp_path / "bell.py"
    source.write_text(
        "from qiskit import QuantumCircuit\nqc = QuantumCircuit(2)\nqc.h(0)\nqc.cx(0, 1)\n"
    )
    command = [sys.executable, "-m", "qcconvert", str(source), "--to", "cudaq", "--check"]
    checked = subprocess.run(command, capture_output=True, text=True, cwd=tmp_path, check=False)
    assert checked.returncode == 0, checked.stderr
    assert "@cudaq.kernel" in checked.stdout and "TVD:" in checked.stderr
    source.write_text("qc = missing\n")
    invalid = subprocess.run(command, capture_output=True, text=True, cwd=tmp_path, check=False)
    assert invalid.returncode == 2 and "第 1 行" in invalid.stderr
    archive = subprocess.run(
        [sys.executable, str(root / "scripts/build_dist.py"), str(tmp_path / "dist")],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )
    assert archive.returncode == 0, archive.stderr
    assert (tmp_path / "dist" / "qcconvert_colab.zip").is_file()


def _execute_generated(code: str, name: str = "qc") -> QuantumCircuit:
    namespace: dict[str, object] = {}
    exec(compile(code, "<generated qiskit>", "exec"), namespace)  # noqa: S102
    circuit = namespace[name]
    assert isinstance(circuit, QuantumCircuit)
    return circuit


def test_reverse_source_controlled_exec() -> None:
    source = "import cudaq\n@cudaq.kernel\ndef kernel():\n    q = cudaq.qvector(2)\n    h(q[0])\n    x.ctrl(q[0], q[1])\n"
    result = cudaq_to_qiskit(source)
    recreated = _execute_generated(result.code)
    assert Statevector(recreated).equiv(Statevector(result.to_qiskit()))


@pytest.mark.parametrize("gate", ["u3", "mx"])
def test_reverse_source_special_gate_exec(gate: str) -> None:
    invocation = "u3(0.2, 0.3, 0.4, q[0])" if gate == "u3" else "mx(q[0])"
    source = (
        f"import cudaq\n@cudaq.kernel\ndef kernel():\n    q = cudaq.qvector(1)\n    {invocation}\n"
    )
    result = cudaq_to_qiskit(source)
    recreated = _execute_generated(result.code)
    assert recreated == result.to_qiskit()


def test_reverse_source_expression_exec() -> None:
    source = "import cudaq\n@cudaq.kernel\ndef kernel(theta: float):\n    q = cudaq.qvector(1)\n    rx(2 * theta, q[0])\n"
    result = cudaq_to_qiskit(source)
    recreated = _execute_generated(result.code)
    expected = result.to_qiskit()
    for angle in (0.1, 0.4, 0.8):
        assert Statevector(recreated.assign_parameters({"theta": angle})).equiv(
            Statevector(expected.assign_parameters({"theta": angle}))
        )


def test_reverse_source_vector_and_pi_exec() -> None:
    source = """import cudaq
import numpy as np
@cudaq.kernel
def kernel(theta: list[float]):
    q = cudaq.qvector(2)
    h(q[0])
    rx(theta[0] + np.pi / 2, q[1])
    ry.ctrl(theta[1] * 2, q[0], q[1])
"""
    result = cudaq_to_qiskit(source)
    recreated = _execute_generated(result.code)
    assert {str(param) for param in recreated.parameters} == {"theta[0]", "theta[1]"}
    for values in ((0.1, 0.2), (0.3, -0.4), (1.0, 0.8)):
        binding = dict(zip(("theta[0]", "theta[1]"), values, strict=True))
        assert Statevector(recreated.assign_parameters(binding)).equiv(
            Statevector(result.to_qiskit().assign_parameters(binding))
        )
    assert qiskit_to_cudaq(result.code).circuit.num_qubits == 2


def test_reverse_source_controlled_adjoint_exec() -> None:
    source = """import cudaq
@cudaq.kernel
def kernel():
    q = cudaq.qvector(2)
    h(q[0])
    u3.adj(0.2, 0.3, 0.4, q[1])
    s.adj(q[1])
    x.ctrl(q[0], q[1])
"""
    result = cudaq_to_qiskit(source)
    assert Statevector(_execute_generated(result.code)).equiv(Statevector(result.to_qiskit()))
    assert qiskit_to_cudaq(result.code).circuit.num_qubits == 2


def test_reverse_source_register_names_exec() -> None:
    source = "import cudaq\n@cudaq.kernel\ndef kernel():\n    left = cudaq.qvector(2)\n    right = cudaq.qubit()\n    h(left[0])\n    mz(right)\n"
    result = cudaq_to_qiskit(source)
    recreated = _execute_generated(result.code)
    assert [(r.name, r.size) for r in recreated.qregs] == [
        (r.name, r.size) for r in result.to_qiskit().qregs
    ]
    assert recreated == result.to_qiskit()


@pytest.mark.parametrize("gate", ["sdg", "tdg"])
def test_reverse_explicit_inverse_gates(gate: str) -> None:
    source = f"import cudaq\n@cudaq.kernel\ndef kernel():\n    q = cudaq.qvector(1)\n    h(q[0])\n    {gate}(q[0])\n"
    result = cudaq_to_qiskit(source)
    expected = QuantumCircuit(1)
    expected.h(0)
    getattr(expected, gate)(0)
    assert Statevector(result.to_qiskit()).equiv(Statevector(expected))


def test_widget_round_trip_status() -> None:
    from qcconvert.widgets import BELL, ConverterApp

    app = ConverterApp(debounce=0)
    app.input.value = BELL
    assert "成功" in app.status.value
    app.direction.value = "qiskit"
    assert "成功" in app.status.value
    app.direction.value = "cudaq"
    assert "成功" in app.status.value and "@cudaq.kernel" in app.output.value


def test_cli_reverse_output_executable(tmp_path: Path) -> None:
    source = tmp_path / "input.py"
    source.write_text(
        "import cudaq\n@cudaq.kernel\ndef kernel():\n    q = cudaq.qvector(2)\n    h(q[0])\n    x.ctrl(q[0], q[1])\n"
    )
    result = subprocess.run(
        [sys.executable, "-m", "qcconvert", str(source), "--to", "qiskit"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert Statevector(_execute_generated(result.stdout)).equiv(
        Statevector(cudaq_to_qiskit(source.read_text()).to_qiskit())
    )


def test_magic_reverse_printed_code_executable(capsys: pytest.CaptureFixture[str]) -> None:
    from IPython.core.interactiveshell import InteractiveShell

    from qcconvert.magics import load_ipython_extension

    shell = InteractiveShell.instance()
    load_ipython_extension(shell)
    source = "import cudaq\n@cudaq.kernel\ndef kernel():\n    q = cudaq.qvector(2)\n    h(q[0])\n    x.ctrl(q[0], q[1])\n"
    shell.run_cell_magic("cudaq2qiskit", "--name magic_recreated", source)
    printed = capsys.readouterr().out
    assert Statevector(_execute_generated(printed, "magic_recreated")).equiv(
        Statevector(shell.user_ns["magic_recreated"])
    )


def test_deep_seeded_random_circuit() -> None:
    import cudaq
    import numpy as np

    rng = np.random.default_rng(20261120)
    qc = QuantumCircuit(5)
    for _ in range(80):
        choice = int(rng.integers(0, 6))
        target = int(rng.integers(0, 5))
        if choice == 0:
            qc.h(target)
        elif choice == 1:
            qc.sx(target)
        elif choice < 5:
            getattr(qc, ("rx", "ry", "rz")[choice - 2])(float(rng.uniform(-2, 2)), target)
        else:
            control = int(rng.choice([index for index in range(5) if index != target]))
            qc.cx(control, target)
    kernel = qiskit_to_cudaq(qc).to_kernel()
    reference = Statevector(qc).data
    actual = np.asarray(cudaq.get_state(kernel))
    assert abs(np.vdot(reference, actual)) ** 2 >= 1 - 1e-6


def test_zero_qubit_ir_dimensions() -> None:
    qc = QuantumCircuit(0)
    result = qiskit_to_cudaq(qc)
    assert result.circuit.num_qubits == 0 and result.circuit.ops == []
    assert "cudaq.qvector(0)" in result.code


@pytest.mark.parametrize(
    "parameter_name",
    [
        "qc",
        "_base",
        "_qr0",
        "np",
        "math",
        "Parameter",
        "QuantumCircuit",
        "custom",
        "_qcconvert_base",
        "_qcconvert_qr0",
        "_qcconvert_param_0",
    ],
)
def test_reverse_source_parameter_shadows_circuit(parameter_name: str) -> None:
    source = (
        "import cudaq\n@cudaq.kernel\n"
        f"def kernel({parameter_name}: float):\n"
        "    q = cudaq.qvector(2)\n"
        "    h(q[0])\n"
        f"    rx.ctrl({parameter_name}, q[0], q[1])\n"
    )
    circuit_name = "custom" if parameter_name == "custom" else "qc"
    result = cudaq_to_qiskit(source, circuit_name=circuit_name)
    recreated = _execute_generated(result.code, circuit_name)
    assert {str(parameter) for parameter in recreated.parameters} == {parameter_name}
    assert Statevector(recreated.assign_parameters({parameter_name: 0.37})).equiv(
        Statevector(result.to_qiskit().assign_parameters({parameter_name: 0.37}))
    )


def test_widget_reverse_run_button(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from qcconvert.widgets import ConverterApp

    monkeypatch.setenv("QCCONVERT_TARGET", "qpp-cpu")
    app = ConverterApp(debounce=0)
    app.direction.value = "qiskit"
    app.input.value = (
        "import cudaq\n@cudaq.kernel\ndef kernel():\n"
        "    q = cudaq.qvector(2)\n    h(q[0])\n    x.ctrl(q[0], q[1])\n"
    )
    assert "成功" in app.status.value
    app.run_button.click()
    printed = capsys.readouterr().out
    assert "target: qpp-cpu" in printed
    assert "counts" in printed and "fidelity" in printed and "TVD" in printed
    assert "錯誤" not in printed


def test_reverse_source_parameter_shadows_register() -> None:
    source = (
        "import cudaq\n@cudaq.kernel\ndef kernel(_qr0: float):\n"
        "    q = cudaq.qvector(1)\n    rx(_qr0, q[0])\n"
    )
    result = cudaq_to_qiskit(source)
    recreated = _execute_generated(result.code)
    assert Statevector(recreated.assign_parameters({"_qr0": 0.37})).equiv(
        Statevector(result.to_qiskit().assign_parameters({"_qr0": 0.37}))
    )


def test_widget_reverse_parameter_output_executable() -> None:
    from qcconvert.widgets import ConverterApp

    app = ConverterApp(debounce=0)
    app.direction.value = "qiskit"
    app.input.value = (
        "import cudaq\n@cudaq.kernel\ndef kernel(qc: float):\n"
        "    q = cudaq.qvector(1)\n    rx(qc, q[0])\n"
    )
    assert "成功" in app.status.value
    recreated = _execute_generated(app.output.value)
    assert {str(parameter) for parameter in recreated.parameters} == {"qc"}


def test_reverse_source_multiple_colliding_parameters_and_expression() -> None:
    source = (
        "import cudaq\n@cudaq.kernel\ndef kernel(np: float, math: float, _base: float):\n"
        "    q = cudaq.qvector(2)\n    h(q[0])\n"
        "    rx.ctrl(np + math * _base, q[0], q[1])\n"
    )
    result = cudaq_to_qiskit(source, circuit_name="Parameter")
    recreated = _execute_generated(result.code, "Parameter")
    assert {str(parameter) for parameter in recreated.parameters} == {"np", "math", "_base"}
    values = {"np": 0.3, "math": 0.4, "_base": 0.5}
    assert Statevector(recreated.assign_parameters(values)).equiv(
        Statevector(result.to_qiskit().assign_parameters(values))
    )


@pytest.mark.parametrize("gate", ["sdg", "tdg", "crx", "cr1"])
def test_reverse_inverse_and_control_alias_independent(gate: str) -> None:
    import cudaq
    import numpy as np

    args = "0.38, " if gate.startswith("cr") else ""
    operands = "q[0], q[1]" if gate.startswith("cr") else "q[1]"
    source = (
        "import cudaq\n@cudaq.kernel\ndef kernel():\n"
        f"    q = cudaq.qvector(2)\n    h(q[0])\n    {gate}({args}{operands})\n"
    )
    result = cudaq_to_qiskit(source)
    score = (
        abs(
            np.vdot(
                Statevector(result.to_qiskit()).data,
                np.asarray(cudaq.get_state(load_kernel(source, "kernel"))),
            )
        )
        ** 2
    )
    assert score >= 1 - 1e-6, (gate, score)


@pytest.mark.parametrize("gate", ["sx", "u"])
def test_independent_controlled_phase(gate: str) -> None:
    import cudaq
    import numpy as np
    from qiskit.circuit.library import SXGate, UGate

    qc = QuantumCircuit(2)
    qc.h(0)
    qc.append(SXGate().control() if gate == "sx" else UGate(0.3, 0.4, -0.7).control(), [0, 1])
    generated = qiskit_to_cudaq(qc)
    score = (
        abs(np.vdot(Statevector(qc).data, np.asarray(cudaq.get_state(generated.to_kernel())))) ** 2
    )
    assert score >= 1 - 1e-6, (gate, score)


def test_compare_reverse_kernel_signature_order() -> None:
    source = (
        "import cudaq\n@cudaq.kernel\ndef kernel(theta: float, alpha: float):\n"
        "    q = cudaq.qvector(1)\n    rx(theta, q[0])\n    ry(alpha, q[0])\n"
    )
    kernel = load_kernel(source, "kernel")
    qc = cudaq_to_qiskit(source).to_qiskit()
    report = compare(qc, kernel, args=(0.3, 1.9), shots=128, seed=1234)
    assert report.fidelity is not None and report.fidelity >= 1 - 1e-6, report.fidelity


def test_compare_measured_kernel_state_must_use_supplied_kernel() -> None:
    qc = QuantumCircuit(1, 1)
    qc.h(0)
    qc.measure(0, 0)
    source = (
        "import cudaq\n@cudaq.kernel\ndef kernel():\n"
        "    q = cudaq.qvector(1)\n    h(q[0])\n    z(q[0])\n    mz(q[0])\n"
    )
    report = compare(qc, load_kernel(source, "kernel"), shots=128, seed=1234)
    assert report.statevector_equal is False, report.fidelity


def test_compare_vector_and_scalar_signature_order() -> None:
    source = (
        "import cudaq\n@cudaq.kernel\ndef kernel(theta: list[float], alpha: float):\n"
        "    q = cudaq.qvector(1)\n    rx(theta[0], q[0])\n"
        "    ry(alpha, q[0])\n    rz(theta[1], q[0])\n"
    )
    kernel = load_kernel(source, "kernel")
    qc = cudaq_to_qiskit(source).to_qiskit()
    report = compare(qc, kernel, args=([0.3, 0.8], 1.9), shots=128, seed=1234)
    assert report.statevector_equal is True, report.fidelity


def test_compare_measured_vector_and_scalar_signature_order() -> None:
    source = (
        "import cudaq\n@cudaq.kernel\ndef kernel(theta: list[float], alpha: float):\n"
        "    q = cudaq.qvector(1)\n    rx(theta[0], q[0])\n"
        "    ry(alpha, q[0])\n    mz(q[0])\n"
    )
    qc = cudaq_to_qiskit(source).to_qiskit()
    report = compare(qc, load_kernel(source, "kernel"), args=([0.3], 1.9), shots=128)
    assert report.statevector_equal is True, report.fidelity


def test_compare_measure_before_unrelated_gate() -> None:
    qc = QuantumCircuit(2, 1)
    qc.measure(0, 0)
    qc.x(1)
    report = compare(qc, shots=128, seed=1234)
    assert report.qiskit_counts == report.cudaq_counts == {"0": 128}
    assert report.statevector_equal is True


def _cross_qubit_mid_measurement() -> QuantumCircuit:
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.measure(0, 0)
    qc.cx(0, 1)
    qc.measure(1, 1)
    return qc


def test_mid_measurement_cross_qubit_counts() -> None:
    qc = _cross_qubit_mid_measurement()
    report = compare(qc, shots=4000, seed=1234)
    assert report.distribution_only and report.statevector_equal is None
    assert report.tvd <= 0.05
    assert set(report.cudaq_counts) == {"00", "11"}


def test_mid_measurement_cli_check(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    source = tmp_path / "mid.py"
    source.write_text(
        "from qiskit import QuantumCircuit\nqc = QuantumCircuit(2, 2)\n"
        "qc.h(0)\nqc.measure(0, 0)\nqc.cx(0, 1)\nqc.measure(1, 1)\n"
    )
    checked = subprocess.run(
        [
            str(root / ".venv/bin/python"),
            "-m",
            "qcconvert",
            str(source),
            "--to",
            "cudaq",
            "--check",
        ],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )
    assert checked.returncode == 0, checked.stderr
    assert "Traceback" not in checked.stderr
    assert "TVD:" in checked.stderr


def test_mid_measurement_widget(
    caplog: pytest.LogCaptureFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    from qcconvert.widgets import ConverterApp

    app = ConverterApp(debounce=0)
    app.input.value = (
        "from qiskit import QuantumCircuit\nqc = QuantumCircuit(2, 2)\n"
        "qc.h(0)\nqc.measure(0, 0)\nqc.cx(0, 1)\nqc.measure(1, 1)\n"
    )
    assert "成功" in app.status.value
    app.run_button.click()
    assert "Traceback" not in caplog.text
    assert "僅比較分佈" in capsys.readouterr().out


def test_mid_measurement_repeated_qubit() -> None:
    qc = QuantumCircuit(1, 2)
    qc.h(0)
    qc.measure(0, 0)
    qc.x(0)
    qc.measure(0, 1)
    report = compare(qc, shots=4000, seed=1234)
    assert report.distribution_only and report.statevector_equal is None
    assert report.tvd <= 0.05
    assert set(report.qiskit_counts) == set(report.cudaq_counts) == {"01", "10"}


def test_mid_measurement_reset_then_measure() -> None:
    qc = QuantumCircuit(1, 2)
    qc.x(0)
    qc.measure(0, 0)
    qc.reset(0)
    qc.measure(0, 1)
    report = compare(qc, shots=128, seed=1234)
    assert report.distribution_only and report.statevector_equal is None
    assert report.qiskit_counts == report.cudaq_counts == {"01": 128}


def test_mid_measurement_overwrites_same_clbit() -> None:
    qc = QuantumCircuit(1, 1)
    qc.x(0)
    qc.measure(0, 0)
    qc.reset(0)
    qc.measure(0, 0)
    report = compare(qc, shots=128)
    assert report.distribution_only and report.statevector_equal is None
    assert report.qiskit_counts == report.cudaq_counts == {"0": 128}


def test_mid_measurement_incompatible_kernel_error(tmp_path: Path) -> None:
    from qcconvert.errors import ConversionError

    qc = _cross_qubit_mid_measurement()
    incompatible = load_kernel(
        "import cudaq\n@cudaq.kernel\ndef kernel():\n"
        "    q = cudaq.qvector(2)\n    h(q[0])\n    mz(q[0])\n",
        "kernel",
    )
    with pytest.raises(ConversionError, match="測量數"):
        compare(qc, incompatible, shots=128)
    from qcconvert.__main__ import main
    from qcconvert.widgets import ConverterApp

    source = tmp_path / "mid.py"
    source.write_text(
        "from qiskit import QuantumCircuit\nqc = QuantumCircuit(2, 2)\n"
        "qc.h(0)\nqc.measure(0, 0)\nqc.cx(0, 1)\nqc.measure(1, 1)\n"
    )
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("qcconvert.__main__.compare", lambda *a, **k: compare(qc, incompatible))
        assert main([str(source), "--to", "cudaq", "--check"]) == 2
        patch.setattr("qcconvert.widgets.compare", lambda *a, **k: compare(qc, incompatible))
        app = ConverterApp(debounce=0)
        app.input.value = source.read_text()
        app.run_button.click()
        assert "錯誤" in app.status.value and "Traceback" not in app.status.value
