"""CUDA-Q 原始碼 AST 白名單：每種拒絕路徑都要指出建構名稱與行號，合法變體要正確轉換。"""

import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from qcconvert import UnsupportedFeatureError, cudaq_to_qiskit


def _kernel(body: str, signature: str = "") -> str:
    lines = "\n".join("    " + line for line in body.splitlines())
    return f"import cudaq\nimport numpy as np\n@cudaq.kernel\ndef kernel({signature}):\n{lines}\n"


@pytest.mark.parametrize(
    "signature",
    ["*, theta: float", "theta: float = 0.5", "*thetas: float", "**options: float"],
)
def test_rejects_non_positional_parameter_declarations(signature: str) -> None:
    with pytest.raises(UnsupportedFeatureError, match="不支援 參數宣告") as exc:
        cudaq_to_qiskit(_kernel("q = cudaq.qubit()", signature))
    assert "第 4 行" in str(exc.value)


@pytest.mark.parametrize(
    "statement,signature,label",
    [
        # qubit 索引：負數、超出範圍、未知暫存器、巢狀下標。
        ("x(q[-1])", "", "qubit 索引"),
        ("x(q[2 + 1])", "", "qubit 索引"),
        ("x(r[0])", "", "qubit 索引"),
        ("x(q[0][0])", "", "qubit 索引"),
        # 角度運算式只允許參數、常數與 np.pi／math.pi。
        ("rx(np.sin(0.1), q[0])", "", "np.sin"),
        ("rx(phi, q[0])", "theta: float", "phi"),
        ("rx(theta[0], q[0])", "theta: float", "參數索引"),
        ("rx(thetas, q[0])", "thetas: list[float]", "參數索引"),
        ("rx(np.e, q[0])", "", "參數運算式"),
        ("rx(0.1 if True else 0.2, q[0])", "", "參數運算式"),
        ("rx(theta > 0, q[0])", "theta: float", "參數運算式"),
        # 閘形式：別名不可再 .ctrl、引數不足、控制重疊、目標數錯誤（含 h(q) 廣播）。
        ("cx.ctrl(q[0], q[1], q[2])", "", "不支援 cx"),
        ("rx(q[0])", "", "不支援 rx"),
        ("x.ctrl(q[0], q[0])", "", "控制位元"),
        ("swap(q[0], q[1], q[2])", "", "不支援 swap"),
        ("h(q)", "", "不支援 h"),
        ("mz.ctrl(q[0], q[1])", "", "不支援 mz"),
        ("reset.adj(q[0])", "", "reset.adj"),
        # 賦值只接受 cudaq.qvector(N)／cudaq.qubit()。
        ("a = 1", "", "賦值"),
        ("r = cudaq.qvector()", "", "暫存器"),
        ("r = cudaq.qubit(2)", "", "暫存器"),
    ],
)
def test_rejects_with_construct_and_line(statement: str, signature: str, label: str) -> None:
    source = _kernel(f"q = cudaq.qvector(3)\n{statement}", signature)
    with pytest.raises(UnsupportedFeatureError, match=label) as exc:
        cudaq_to_qiskit(source)
    assert "第 6 行" in str(exc.value)


def test_constant_index_arithmetic_and_pass() -> None:
    # -1 + 2 → q[1]；2 - 1 → q[1]；pass 不產生任何閘。
    result = cudaq_to_qiskit(_kernel("q = cudaq.qvector(2)\npass\nx(q[-1 + 2])\nh(q[2 - 1])"))
    expected = QuantumCircuit(2)
    expected.x(1)
    expected.h(1)
    assert [op.name for op in result.circuit.ops] == ["x", "h"]
    assert all(op.targets == (1,) for op in result.circuit.ops)
    assert Operator(result.to_qiskit()).equiv(Operator(expected))
