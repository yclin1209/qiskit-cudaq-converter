"""compare()／中途測量的錯誤路徑與邊界情況（以真實電路與 kernel 驗證可觀察結果）。"""

from types import SimpleNamespace

import cudaq
import pytest
from qiskit import QuantumCircuit
from qiskit.circuit import Clbit, Parameter, ParameterVector, Qubit

from qcconvert import compare, load_kernel, qiskit_to_cudaq
from qcconvert.errors import ConversionError
from qcconvert.runner import _capture_measurements


@pytest.fixture(autouse=True)
def _cpu(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QCCONVERT_TARGET", "qpp-cpu")


def _bell() -> QuantumCircuit:
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure([0, 1], [0, 1])
    return qc


def _mid() -> QuantumCircuit:
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.measure(0, 0)
    qc.cx(0, 1)
    qc.measure(1, 1)
    return qc


def test_kernel_without_signature_is_rejected() -> None:
    with pytest.raises(ConversionError, match="無法取得 kernel 參數簽章"):
        compare(_bell(), object())


def test_parameter_argument_errors() -> None:
    theta = Parameter("theta")
    qc = QuantumCircuit(1)
    qc.rx(theta, 0)
    with pytest.raises(ConversionError, match="參數數量不符"):
        compare(qc)
    # 綁定成另一個符號參數，電路仍未完全綁定。
    with pytest.raises(ConversionError, match="缺少參數 args"):
        compare(qc, args=(Parameter("phi"),))


def test_parameter_vector_argument_errors() -> None:
    angles = ParameterVector("angles", 2)
    qc = QuantumCircuit(1)
    qc.rx(angles[0], 0)
    qc.ry(angles[1], 0)
    with pytest.raises(ConversionError, match="angles 需要數值列表"):
        compare(qc, args=(0.5,))
    with pytest.raises(ConversionError, match="angles 長度不足"):
        compare(qc, args=([0.5],))
    assert compare(qc, args=([0.5, 0.25],)).statevector_equal is True


def test_unseeded_sampling_still_matches() -> None:
    report = compare(_bell(), seed=None)
    assert report.statevector_equal is True
    assert set(report.qiskit_counts) == set(report.cudaq_counts) == {"00", "11"}
    assert report.tvd <= 0.05


def test_kernel_measuring_fewer_qubits_than_circuit() -> None:
    source = (
        "import cudaq\n@cudaq.kernel\ndef fewer():\n    q = cudaq.qvector(2)\n"
        "    h(q[0])\n    x.ctrl(q[0], q[1])\n    mz(q[0])\n"
    )
    with pytest.raises(ConversionError, match="clbit 對應不符"):
        compare(_bell(), load_kernel(source, "fewer"))


def test_statically_unparsable_kernel_falls_back_to_distribution() -> None:
    # h(q) 廣播可由 CUDA-Q 編譯，但 AST 白名單不支援 → 無法重建測量前狀態，只比較分佈。
    source = (
        "import cudaq\n@cudaq.kernel\ndef broadcast():\n    q = cudaq.qvector(2)\n"
        "    h(q)\n    mz(q)\n"
    )
    qc = QuantumCircuit(2, 2)
    qc.h([0, 1])
    qc.measure([0, 1], [0, 1])
    report = compare(qc, load_kernel(source, "broadcast"))
    assert report.statevector_equal is None and report.distribution_only
    assert set(report.cudaq_counts) == {"00", "01", "10", "11"}
    assert report.tvd <= 0.05


def test_mid_measurement_needs_kernel_source() -> None:
    fake = SimpleNamespace(kernelFunction=lambda: None)
    with pytest.raises(ConversionError, match="funcSrc"):
        compare(_mid(), fake)


def test_mid_measurement_with_loose_clbits() -> None:
    # 沒有 ClassicalRegister 的 clbit：Aer 鍵不帶空白分隔，仍須對齊全域 clbit 索引。
    qc = QuantumCircuit([Qubit(), Qubit()], [Clbit(), Clbit()])
    qc.h(0)
    qc.measure(0, 0)
    qc.cx(0, 1)
    qc.measure(1, 1)
    report = compare(qc)
    assert report.distribution_only
    assert set(report.qiskit_counts) == set(report.cudaq_counts) == {"00", "11"}
    assert report.tvd <= 0.05


def _fake_run(result: object) -> object:
    def run(*_: object, **__: object) -> object:
        if isinstance(result, Exception):
            raise result
        return result

    return run


@pytest.mark.parametrize(
    "result,message",
    [
        ([[True, True]], "shot 數量不符"),
        ([[True]] * 8, "位元數量不符"),
        (RuntimeError("simulator crashed"), "中途測量無法比較：simulator crashed"),
    ],
)
def test_mid_measurement_rejects_malformed_simulator_output(
    monkeypatch: pytest.MonkeyPatch, result: object, message: str
) -> None:
    # 邊界：CUDA-Q 模擬器（cudaq.run）的回傳不符預期時，要轉成 ConversionError。
    monkeypatch.setattr(cudaq, "run", _fake_run(result))
    with pytest.raises(ConversionError, match=message):
        compare(_mid(), shots=8)


def test_capture_requires_single_function() -> None:
    source = qiskit_to_cudaq(_mid()).code + "\ndef extra():\n    pass\n"
    with pytest.raises(ConversionError, match="函式數量不符"):
        _capture_measurements(source)
