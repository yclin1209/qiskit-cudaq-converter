"""CLI、套件進入點、kernel 載入、Qiskit IR 與 widget 的邊界路徑。"""

import hashlib
import runpy
import sys
import threading
import time
from pathlib import Path

import pytest
from IPython.core.interactiveshell import InteractiveShell
from qiskit import QuantumCircuit
from qiskit.circuit import Gate, Parameter
from qiskit.circuit.library import GlobalPhaseGate

import qcconvert
from qcconvert import (
    ConversionError,
    UnsupportedFeatureError,
    compare,
    cudaq_to_qiskit,
    load_kernel,
    qiskit_to_cudaq,
)
from qcconvert.__main__ import main
from qcconvert.ir import Circuit, Op
from qcconvert.qiskit_io import from_ir
from qcconvert.qiskit_io import to_source as qiskit_source
from qcconvert.widgets import BELL, ConverterApp


@pytest.fixture(autouse=True)
def _cpu(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QCCONVERT_TARGET", "qpp-cpu")


# 套件與 CLI


def test_show_without_ipywidgets_in_process(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "ipywidgets", None)
    monkeypatch.delitem(sys.modules, "qcconvert.widgets", raising=False)
    with pytest.raises(ImportError, match="pip install ipywidgets"):
        qcconvert.show()


def test_cli_prints_to_stdout(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "bell.py"
    source.write_text(BELL)
    assert main([str(source), "--to", "cudaq"]) == 0
    assert "@cudaq.kernel" in capsys.readouterr().out


def test_python_dash_m_entry_point(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "bell.py"
    source.write_text(BELL)
    monkeypatch.setattr(sys, "argv", ["qcconvert", str(source), "--to", "cudaq"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("qcconvert", run_name="__main__", alter_sys=False)
    assert exc.value.code == 0
    assert "@cudaq.kernel" in capsys.readouterr().out


def test_invalid_circuit_name() -> None:
    with pytest.raises(ConversionError, match="無效電路名稱：1qc"):
        cudaq_to_qiskit("", circuit_name="1qc")


def test_magic_without_run_only_converts(capsys: pytest.CaptureFixture[str]) -> None:
    shell = InteractiveShell.instance()
    qcconvert.load_ipython_extension(shell)
    shell.run_cell_magic("qiskit2cudaq", "--name norun_kernel", BELL)
    printed = capsys.readouterr().out
    assert "@cudaq.kernel" in printed and "target:" not in printed
    assert qcconvert.compare(
        QuantumCircuit.from_qasm_str(
            'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nh q[0];\ncx q[0],q[1];\n'
        ),
        shell.user_ns["norun_kernel"],
    ).statevector_equal


# CUDA-Q 原始碼產生與載入


def test_parameter_names_colliding_after_cleanup() -> None:
    qc = QuantumCircuit(1)
    qc.rx(Parameter("a b"), 0)
    qc.ry(Parameter("a_b"), 0)
    with pytest.raises(ConversionError, match="清理後重複"):
        qiskit_to_cudaq(qc)


@pytest.mark.parametrize(
    "method", ["sin", "cos", "tan", "arcsin", "arccos", "arctan", "exp", "log"]
)
def test_parameter_expression_functions_compile_and_match(method: str) -> None:
    # 回歸：Qiskit 運算式字串是 `sin(theta)`，原本原樣輸出，CUDA-Q 編譯失敗（unhandled function call）。
    theta = Parameter("theta")
    qc = QuantumCircuit(1)
    qc.rx(getattr(theta, method)() * 2 + 0.1, 0)
    qc.rz(theta, 0)
    assert "np." in qiskit_to_cudaq(qc).code
    for value in (0.2, 0.45, 0.8):
        assert compare(qc, args=(value,)).statevector_equal is True


@pytest.mark.parametrize("method,name", [("abs", "abs"), ("sign", "sign"), ("conjugate", "conj")])
def test_parameter_expression_functions_unsupported(method: str, name: str) -> None:
    theta = Parameter("theta")
    qc = QuantumCircuit(1)
    qc.rx(getattr(theta, method)(), 0)
    with pytest.raises(UnsupportedFeatureError, match=f"參數運算式函式：{name}"):
        qiskit_to_cudaq(qc)


def test_r_gate_with_parameter_phase() -> None:
    theta, phi = Parameter("theta"), Parameter("phi")
    qc = QuantumCircuit(1)
    qc.r(theta, phi.sin(), 0)
    assert compare(qc, args=(0.3, 0.7)).statevector_equal is True


def test_load_kernel_failure_is_not_cached() -> None:
    code = "raise RuntimeError('kernel module failed')\n"
    for _ in range(2):  # 第二次仍要重新執行，而非回傳半初始化的模組。
        with pytest.raises(RuntimeError, match="kernel module failed"):
            load_kernel(code, "kernel")
    assert f"_qcconvert_{hashlib.sha256(code.encode()).hexdigest()}" not in sys.modules


def test_object_translation_failure() -> None:
    with pytest.raises(ConversionError, match="OpenQASM 2 翻譯失敗"):
        cudaq_to_qiskit(object())


# Qiskit → IR


def test_global_phase_instruction_is_skipped_with_warning() -> None:
    qc = QuantumCircuit(1)
    qc.append(GlobalPhaseGate(0.3), [])
    qc.h(0)
    result = qiskit_to_cudaq(qc)
    assert "global_phase 已略過" in result.warnings
    assert [op.name for op in result.circuit.ops] == ["h"]


def test_opaque_gate_is_rejected() -> None:
    qc = QuantumCircuit(1)
    qc.append(Gate("mystery", 1, []), [0])
    with pytest.raises(UnsupportedFeatureError, match="不支援 mystery:"):
        qiskit_to_cudaq(qc)
    with pytest.raises(UnsupportedFeatureError, match="不支援 mystery$"):
        qiskit_to_cudaq(qc, decompose_unknown=False)


def test_reused_parameter_is_declared_once() -> None:
    theta = Parameter("theta")
    qc = QuantumCircuit(1)
    qc.rx(theta, 0)
    qc.ry(2 * theta, 0)
    result = qiskit_to_cudaq(qc)
    assert result.circuit.params == ["theta"]
    assert compare(qc, args=(0.6,)).statevector_equal is True


def test_ir_with_unsupported_expressions() -> None:
    # IR 是兩個方向的共通邊界：非整數索引與非 pi 屬性都要明確拒絕，不可產生壞掉的程式碼。
    bad_index = Circuit(1, params=["th"], ops=[Op("rx", (0,), (), ("th[0.5]",))])
    with pytest.raises(ConversionError, match=r"不支援參數運算式：th\[0.5\]"):
        from_ir(bad_index)
    attribute = Circuit(1, ops=[Op("rx", (0,), (), ("np.e",))])
    with pytest.raises(ConversionError, match="不支援參數運算式：np.e"):
        qiskit_source(attribute)


# widget 延遲（debounce）


def test_negative_debounce() -> None:
    with pytest.raises(ValueError, match="debounce"):
        ConverterApp(debounce=-1)


def test_debounce_restarts_on_each_edit() -> None:
    app = ConverterApp(debounce=60)
    app.input.value = "qc = garbage"
    first = app._timer
    app.input.value = BELL
    assert isinstance(first, threading.Timer) and first.finished.is_set()
    assert app._timer is not first and app.output.value == ""
    assert app._timer is not None
    app._timer.cancel()


def test_direction_switch_flushes_pending_edit() -> None:
    # 回歸：延遲中切換方向，原本會把尚未轉換的輸入丟掉並換成空白。
    app = ConverterApp(debounce=60)
    app.input.value = BELL
    assert app.output.value == ""
    app.direction.value = "qiskit"
    assert "@cudaq.kernel" in app.input.value
    assert "QuantumCircuit" in app.output.value and "成功" in app.status.value
    if app._timer is not None:
        app._timer.cancel()


def test_direction_switch_after_debounce_fired() -> None:
    app = ConverterApp(debounce=0.01)
    app.input.value = BELL
    timer = app._timer
    assert timer is not None
    timer.join(5)
    deadline = time.monotonic() + 5
    while "@cudaq.kernel" not in app.output.value and time.monotonic() < deadline:
        time.sleep(0.01)
    app.direction.value = "qiskit"
    assert "@cudaq.kernel" in app.input.value and "QuantumCircuit" in app.output.value
