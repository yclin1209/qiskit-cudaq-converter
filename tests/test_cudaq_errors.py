"""不執行不支援的 CUDA-Q 語法。"""

import pytest

from qcconvert import UnsupportedFeatureError, cudaq_to_qiskit


@pytest.mark.parametrize(
    "expression,expected",
    [
        ("if mz(q[0]):\n        x(q[0])", "If"),
        ("while True:\n        x(q[0])", "While"),
        ("other(q[0])", "other"),
        ("exp_pauli(0.5, q[0], 'X')", "exp_pauli"),
        ("cudaq.control(other, q[0], q[0])", "cudaq.control"),
        ("x(q[4])", "qubit 索引"),
        ("q = cudaq.qvector(0)", "暫存器"),
    ],
)
def test_rejected(expression: str, expected: str) -> None:
    source = (
        f"import cudaq\n@cudaq.kernel\ndef kernel():\n    q = cudaq.qvector(1)\n    {expression}\n"
    )
    with pytest.raises(UnsupportedFeatureError, match=expected) as exc:
        cudaq_to_qiskit(source)
    assert "第 5 行" in str(exc.value)


@pytest.mark.parametrize("annotation", ["int", "str", ""])
def test_invalid_parameter_type(annotation: str) -> None:
    declaration = f"theta: {annotation}" if annotation else "theta"
    source = f"import cudaq\n@cudaq.kernel\ndef kernel({declaration}):\n    q = cudaq.qubit()\n"
    with pytest.raises(UnsupportedFeatureError, match="參數 theta") as exc:
        cudaq_to_qiskit(source)
    assert "第 3 行" in str(exc.value)


@pytest.mark.parametrize(
    "expression,label",
    [
        ("x(q[theta])", "常數索引"),
        ("for i in range(theta):\n        x(q[i])", "常數索引"),
    ],
)
def test_nonconstant_index_or_range(expression: str, label: str) -> None:
    source = f"import cudaq\n@cudaq.kernel\ndef kernel(theta: float):\n    q = cudaq.qvector(2)\n    {expression}\n"
    with pytest.raises(UnsupportedFeatureError, match=label) as exc:
        cudaq_to_qiskit(source)
    assert "第 5 行" in str(exc.value)
