"""Qiskit 電路輸入與中間表示（IR）轉換。"""

import ast
import math
import operator
import re
import traceback
from typing import Any, cast

from qiskit import QuantumCircuit, transpile
from qiskit.circuit import Parameter, ParameterExpression, ParameterVectorElement

from .errors import ConversionError, UnsupportedFeatureError
from .ir import Circuit, Op

SINGLE = {
    "h",
    "x",
    "y",
    "z",
    "s",
    "sdg",
    "t",
    "tdg",
    "sx",
    "sxdg",
    "rx",
    "ry",
    "rz",
    "p",
    "u",
    "u1",
    "u2",
    "u3",
    "r",
    "id",
}
MULTI = {
    "cx": ("x", 1),
    "cy": ("y", 1),
    "cz": ("z", 1),
    "ch": ("h", 1),
    "crx": ("rx", 1),
    "cry": ("ry", 1),
    "crz": ("rz", 1),
    "cp": ("p", 1),
    "cu1": ("u1", 1),
    "ccx": ("x", 2),
    "cswap": ("swap", 1),
    "swap": ("swap", 0),
    "rzz": ("rzz", 0),
    "rxx": ("rxx", 0),
    "ryy": ("ryy", 0),
}
FORBIDDEN = {
    "if_else",
    "while_loop",
    "for_loop",
    "switch_case",
    "delay",
    "break_loop",
    "continue_loop",
    "store",
}


def _unsupported(name: str, operation: object) -> str | None:
    if name == "if_else":
        return "if_test"
    if name in FORBIDDEN:
        return name
    if getattr(operation, "condition", None) is not None:
        return "c_if"
    if name == "calibrated_gate" or getattr(operation, "calibration", None) is not None:
        return "pulse"
    return None


def source_to_qiskit(source: str) -> QuantumCircuit:
    """執行使用者輸入程式碼（非安全沙箱），並選取最後指派電路。"""
    scope: dict[str, object] = {}
    try:
        exec(compile(source, "<qiskit input>", "exec"), scope)  # noqa: S102
    except Exception as exc:
        line = (
            exc.lineno
            if isinstance(exc, SyntaxError)
            else next(
                (
                    frame.lineno
                    for frame in reversed(traceback.extract_tb(exc.__traceback__))
                    if frame.filename == "<qiskit input>"
                ),
                None,
            )
        )
        raise ConversionError(f"第 {line} 行：{exc}") from exc
    if isinstance(scope.get("qc"), QuantumCircuit):
        return scope["qc"]
    circuits = [value for value in scope.values() if isinstance(value, QuantumCircuit)]
    if not circuits:
        raise ConversionError("找不到 QuantumCircuit 電路")
    return circuits[-1]


def to_ir(qc: QuantumCircuit, *, decompose_unknown: bool = True) -> tuple[Circuit, list[str]]:
    warnings: list[str] = []
    ir = Circuit(
        qc.num_qubits,
        qc.num_clbits,
        qreg_names=[(r.name, r.size) for r in qc.qregs],
        creg_names=[(r.name, r.size) for r in qc.cregs],
    )
    if qc.global_phase:
        warnings.append("global_phase 已略過")
    for inst in qc.data:
        op = inst.operation
        name = op.name
        forbidden = _unsupported(name, op)
        if forbidden is not None:
            raise UnsupportedFeatureError(f"不支援 {forbidden} 經典條件控制")
        if name in {"initialize", "state_preparation"} and not decompose_unknown:
            raise UnsupportedFeatureError(f"不支援 {name}")
        if name == "barrier":
            warnings.append("barrier 已略過")
            continue
        if name == "global_phase":
            warnings.append("global_phase 已略過")
            continue
        qubits = tuple(qc.find_bit(bit).index for bit in inst.qubits)
        clbits = tuple(qc.find_bit(bit).index for bit in inst.clbits)
        controls = 0
        base = name
        if name == "mcx":
            base, controls = "x", len(qubits) - 1
        elif name == "cu":
            base, controls = "u", 1
        elif name in MULTI:
            base, controls = MULTI[name]
        elif name not in SINGLE | {"measure", "reset"}:
            from qiskit.circuit import ControlledGate

            if isinstance(op, ControlledGate) and op.base_gate.name in SINGLE | {
                "swap",
                "rzz",
                "rxx",
                "ryy",
            }:
                base, controls = op.base_gate.name, op.num_ctrl_qubits
                if op.ctrl_state != (1 << controls) - 1:
                    raise UnsupportedFeatureError(f"不支援 {name} ctrl_state")
                if base == "id":
                    continue
            elif decompose_unknown:
                try:
                    expanded = transpile(
                        qc,
                        basis_gates=[
                            "h",
                            "x",
                            "y",
                            "z",
                            "s",
                            "sdg",
                            "t",
                            "tdg",
                            "rx",
                            "ry",
                            "rz",
                            "p",
                            "u",
                            "cx",
                            "cz",
                            "swap",
                            "rzz",
                            "rxx",
                            "ryy",
                            "reset",
                            "measure",
                        ],
                        optimization_level=0,
                    )
                except Exception as exc:
                    raise UnsupportedFeatureError(f"不支援 {name}: {exc}") from exc
                warnings.append(f"{name} 已分解")
                result, extra = to_ir(expanded, decompose_unknown=False)
                return result, warnings + extra
            else:
                raise UnsupportedFeatureError(f"不支援 {name}")
        if name == "id":
            continue
        params: list[float | str] = []
        for value in op.params:
            if isinstance(value, ParameterExpression):
                for symbol in value.parameters:
                    if isinstance(symbol, ParameterVectorElement):
                        label = symbol.vector.name
                        if label not in ir.params:
                            ir.params.append(label)
                    elif symbol.name not in ir.params:
                        ir.params.append(symbol.name)
                params.append(str(value))
            else:
                params.append(float(value))
        ir.ops.append(Op(base, qubits[controls:], qubits[:controls], tuple(params), clbits))
    return ir, warnings


def _parameter_value(text: str, symbols: dict[str, object]) -> object:
    """以白名單運算式重建符號參數，避免執行外來程式碼。"""
    binary = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
    }

    def visit(node: ast.AST) -> object:
        if isinstance(node, ast.Constant) and isinstance(node.value, (float, int)):
            return node.value
        if isinstance(node, ast.Name) and node.id in symbols:
            return symbols[node.id]
        if (
            isinstance(node, ast.Attribute)
            and node.attr == "pi"
            and isinstance(node.value, ast.Name)
            and node.value.id in {"np", "math"}
        ):
            return math.pi
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id in symbols
        ):
            index = visit(node.slice)
            if type(index) is int and isinstance(symbols[node.value.id], list):
                return cast(Any, symbols[node.value.id])[index]
            if type(index) is int and hasattr(symbols[node.value.id], "__getitem__"):
                return cast(Any, symbols[node.value.id])[index]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            value = visit(node.operand)
            return -cast(Any, value) if isinstance(node.op, ast.USub) else value
        if isinstance(node, ast.BinOp) and type(node.op) in binary:
            return binary[type(node.op)](visit(node.left), visit(node.right))
        raise ConversionError(f"不支援參數運算式：{text}")

    return visit(ast.parse(text, mode="eval").body)


def from_ir(ir: Circuit) -> QuantumCircuit:
    from qiskit.circuit import ClassicalRegister, ParameterVector, QuantumRegister

    qr = [QuantumRegister(size, name) for name, size in ir.qreg_names] or [
        QuantumRegister(ir.num_qubits, "q")
    ]
    cr = [ClassicalRegister(size, name) for name, size in ir.creg_names] or (
        [ClassicalRegister(ir.num_clbits, "c")] if ir.num_clbits else []
    )
    qc = QuantumCircuit(*qr, *cr)
    symbols = {name: Parameter(name) for name in ir.params}
    for name in ir.params:
        indices = [
            int(match.group(1))
            for op in ir.ops
            for value in op.params
            if isinstance(value, str)
            for match in re.finditer(r"\b" + re.escape(name) + r"\[(\d+)\]", value)
        ]
        if indices:
            symbols[name] = ParameterVector(name, max(indices) + 1)
    for op in ir.ops:
        if op.name == "measure":
            qc.measure(op.targets[0], op.clbits[0])
            continue
        if op.name in {"mx", "my"}:
            if op.name == "mx":
                qc.h(op.targets[0])
            else:
                qc.sdg(op.targets[0])
                qc.h(op.targets[0])
            qc.measure(op.targets[0], op.clbits[0])
            continue
        method = getattr(qc, "u" if op.name == "u3" else op.name)
        values = [
            (_parameter_value(value, symbols)) if isinstance(value, str) else value
            for value in op.params
        ]
        if op.controls:
            base = QuantumCircuit(len(op.targets))
            getattr(base, "u" if op.name == "u3" else op.name)(*values, *range(len(op.targets)))
            gate = base.to_gate().control(len(op.controls))
            qc.append(gate, (*op.controls, *op.targets))
        else:
            method(*values, *op.targets)
    return qc


def to_source(ir: Circuit, name: str = "qc") -> str:
    """產生可重建電路的 Qiskit 原始碼。"""
    expressions = [value for op in ir.ops for value in op.params if isinstance(value, str)]
    reserved = {name, *ir.params}
    for expression in expressions:
        reserved.update(
            node.id
            for node in ast.walk(ast.parse(expression, mode="eval"))
            if isinstance(node, ast.Name)
        )

    def fresh(label: str) -> str:
        candidate = f"_qcconvert_{label}"
        while candidate in reserved:
            candidate += "_"
        reserved.add(candidate)
        return candidate

    math_alias, numpy_alias = fresh("math"), fresh("numpy")
    circuit_type, quantum_type, classical_type = (
        fresh("QuantumCircuit"),
        fresh("QuantumRegister"),
        fresh("ClassicalRegister"),
    )
    param_type, vector_type = fresh("Parameter"), fresh("ParameterVector")
    symbols = {param: fresh(f"param_{index}") for index, param in enumerate(ir.params)}
    base = fresh("base")

    class RenameExpression(ast.NodeTransformer):
        def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
            # np.pi／math.pi 是常數，不受同名參數影響。
            if (
                isinstance(node.value, ast.Name)
                and node.value.id in {"np", "math"}
                and node.attr == "pi"
            ):
                return ast.copy_location(
                    ast.Attribute(
                        value=ast.Name(
                            id=numpy_alias if node.value.id == "np" else math_alias, ctx=ast.Load()
                        ),
                        attr="pi",
                        ctx=ast.Load(),
                    ),
                    node,
                )
            return self.generic_visit(node)

        def visit_Name(self, node: ast.Name) -> ast.AST:
            return (
                ast.copy_location(ast.Name(id=symbols[node.id], ctx=ast.Load()), node)
                if node.id in symbols
                else node
            )

    def argument(value: float | str) -> str:
        return (
            ast.unparse(RenameExpression().visit(ast.parse(value, mode="eval")))
            if isinstance(value, str)
            else repr(value)
        )

    lines = [
        f"import math as {math_alias}",
        f"import numpy as {numpy_alias}",
        f"from qiskit import QuantumCircuit as {circuit_type}",
        f"from qiskit.circuit import QuantumRegister as {quantum_type}, ClassicalRegister as {classical_type}",
        f"from qiskit.circuit import Parameter as {param_type}, ParameterVector as {vector_type}",
    ]
    for param in ir.params:
        indices = [
            int(match.group(1))
            for op in ir.ops
            for value in op.params
            if isinstance(value, str)
            for match in re.finditer(r"\b" + re.escape(param) + r"\[(\d+)\]", value)
        ]
        constructor = (
            f"{vector_type}({param!r}, {max(indices) + 1})"
            if indices
            else f"{param_type}({param!r})"
        )
        lines.append(f"{symbols[param]} = {constructor}")
    qregs = ir.qreg_names or [("q", ir.num_qubits)]
    cregs = ir.creg_names or ([("c", ir.num_clbits)] if ir.num_clbits else [])
    qreg_vars = [fresh(f"qr{index}") for index in range(len(qregs))]
    creg_vars = [fresh(f"cr{index}") for index in range(len(cregs))]
    for index, (reg_name, size) in enumerate(qregs):
        lines.append(f"{qreg_vars[index]} = {quantum_type}({size}, {reg_name!r})")
    for index, (reg_name, size) in enumerate(cregs):
        lines.append(f"{creg_vars[index]} = {classical_type}({size}, {reg_name!r})")
    lines.append(f"{name} = {circuit_type}({', '.join(qreg_vars + creg_vars)})")
    for op in ir.ops:
        target = op.targets[0] if op.targets else 0
        if op.name in {"mx", "my"}:
            if op.name == "my":
                lines.append(f"{name}.sdg({target})")
            lines.append(f"{name}.h({target})")
            lines.append(f"{name}.measure({target}, {op.clbits[0]})")
            continue
        method = "u" if op.name == "u3" else op.name
        arguments = [argument(value) for value in op.params]
        if op.controls:
            lines.append(f"{base} = {circuit_type}({len(op.targets)})")
            local_args = arguments + [str(i) for i in range(len(op.targets))]
            lines.append(f"{base}.{method}({', '.join(local_args)})")
            qubits = [*op.controls, *op.targets]
            lines.append(f"{name}.append({base}.to_gate().control({len(op.controls)}), {qubits!r})")
        else:
            arguments += [str(q) for q in (*op.targets, *op.clbits)]
            lines.append(f"{name}.{method}({', '.join(arguments)})")
    return "\n".join(lines) + "\n"
