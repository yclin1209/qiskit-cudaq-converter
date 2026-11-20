"""以白名單 AST 靜態解析 CUDA-Q kernel，不執行輸入。"""

import ast
import operator
import re

from .errors import ConversionError, UnsupportedFeatureError
from .ir import Circuit, Op

GATES = {
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
    "r1",
    "u3",
    "swap",
    "mz",
    "mx",
    "my",
    "reset",
    "cx",
    "cy",
    "cz",
    "ch",
    "cs",
    "ct",
    "crx",
    "cry",
    "crz",
    "cr1",
}
ARITY = {"swap": 2}
ANGLES = {"rx": 1, "ry": 1, "rz": 1, "r1": 1, "u3": 3}
ALIASES = {
    "cx": "x",
    "cy": "y",
    "cz": "z",
    "ch": "h",
    "cs": "s",
    "ct": "t",
    "crx": "rx",
    "cry": "ry",
    "crz": "rz",
    "cr1": "r1",
}
ARITH = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}


def reject(node: ast.AST, name: str | None = None) -> None:
    label = name or (ast.unparse(node.func) if isinstance(node, ast.Call) else type(node).__name__)
    raise UnsupportedFeatureError(f"第 {getattr(node, 'lineno', '?')} 行：不支援 {label}")


class Parser:
    def __init__(self, function: ast.FunctionDef) -> None:
        self.ir = Circuit(0)
        self.registers: dict[str, tuple[int, ...]] = {}
        self.loops: dict[str, int] = {}
        self.vectors: set[str] = set()
        for arg in function.args.args:
            annotation = ast.unparse(arg.annotation) if arg.annotation else ""
            if annotation not in {"float", "list[float]"}:
                reject(arg, f"參數 {arg.arg}: {annotation}")
            if annotation == "list[float]":
                self.vectors.add(arg.arg)
            self.ir.params.append(arg.arg)
        if (
            function.args.kwonlyargs
            or function.args.vararg
            or function.args.kwarg
            or function.args.defaults
        ):
            reject(function, "參數宣告")
        self.body(function.body)

    def integer(self, node: ast.AST) -> int:
        if isinstance(node, ast.Constant) and type(node.value) is int:
            return node.value
        if isinstance(node, ast.Name) and node.id in self.loops:
            return self.loops[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -self.integer(node.operand)
        if isinstance(node, ast.BinOp) and type(node.op) in ARITH:
            return int(ARITH[type(node.op)](self.integer(node.left), self.integer(node.right)))
        reject(node, "常數索引")
        raise AssertionError

    def qubits(self, node: ast.AST) -> tuple[int, ...]:
        if isinstance(node, ast.Name) and node.id in self.registers:
            return self.registers[node.id]
        if isinstance(node, ast.List):
            return tuple(q for item in node.elts for q in self.qubits(item))
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
            reg = self.registers.get(node.value.id)
            if reg is not None:
                index = self.integer(node.slice)
                if 0 <= index < len(reg):
                    return (reg[index],)
        reject(node, "qubit 索引")
        raise AssertionError

    def angle(self, node: ast.AST) -> float | str:
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                reject(child)
            if isinstance(child, ast.Name) and child.id not in self.ir.params + [
                "np",
                "math",
                *self.loops,
            ]:
                reject(child, child.id)
            if isinstance(child, ast.Subscript):
                if not isinstance(child.value, ast.Name) or child.value.id not in self.vectors:
                    reject(child, "參數索引")
                self.integer(child.slice)
            if (
                isinstance(child, ast.Name)
                and child.id in self.vectors
                and not any(
                    isinstance(parent, ast.Subscript) and parent.value is child
                    for parent in ast.walk(node)
                )
            ):
                reject(child, "參數索引")
            if isinstance(child, ast.Attribute) and not (
                isinstance(child.value, ast.Name)
                and child.value.id in {"np", "math"}
                and child.attr == "pi"
            ):
                reject(child, "參數運算式")
            if isinstance(child, (ast.Compare, ast.BoolOp, ast.IfExp, ast.Lambda)):
                reject(child, "參數運算式")
        text = ast.unparse(node)
        for key, value in self.loops.items():
            text = re.sub(r"\b" + key + r"\b", str(value), text)
        if isinstance(node, ast.Constant) and isinstance(node.value, (float, int)):
            return float(node.value)
        return text

    def call(self, call: ast.Call) -> None:
        func = call.func
        adj = isinstance(func, ast.Attribute) and func.attr == "adj"
        ctrl = isinstance(func, ast.Attribute) and func.attr == "ctrl"
        gate = (
            func.value.id
            if isinstance(func, ast.Attribute)
            and (adj or ctrl)
            and isinstance(func.value, ast.Name)
            else (func.id if isinstance(func, ast.Name) else "")
        )
        if gate not in GATES or call.keywords:
            reject(call)
        if gate in {"sdg", "tdg"} and (ctrl or adj):
            reject(call, gate + (".ctrl" if ctrl else ".adj"))
        alias = gate in ALIASES
        base_gate = ALIASES.get(gate, gate)
        if alias and (ctrl or adj):
            reject(call, gate)
        count = ANGLES.get(base_gate, 0)
        if len(call.args) < count + ARITY.get(base_gate, 1) + int(ctrl or alias):
            reject(call, gate)
        params = tuple(self.angle(arg) for arg in call.args[:count])
        operands = call.args[count:]
        target_args = operands[-ARITY.get(base_gate, 1) :] if ctrl or alias else operands
        controls = (
            tuple(q for arg in operands[: -ARITY.get(base_gate, 1)] for q in self.qubits(arg))
            if ctrl or alias
            else ()
        )
        targets = tuple(q for arg in target_args for q in self.qubits(arg))
        if set(controls) & set(targets) or len(set(controls)) != len(controls):
            reject(call, "控制位元")
        if gate not in {"mz", "mx", "my"} and len(targets) != ARITY.get(base_gate, 1):
            reject(call, gate)
        if gate in {"mz", "mx", "my"}:
            if ctrl or adj:
                reject(call, gate)
            for target in targets:
                self.ir.ops.append(
                    Op("measure" if gate == "mz" else gate, (target,), clbits=(self.ir.num_clbits,))
                )
                self.ir.num_clbits += 1
            return
        if adj and gate not in {"s", "t", "rx", "ry", "rz", "r1", "u3"}:
            reject(call, gate + ".adj")
        if adj:
            if gate == "s":
                gate = "sdg"
            elif gate == "t":
                gate = "tdg"
            elif gate == "u3":
                params = tuple(f"-({v})" for v in (params[0], params[2], params[1]))
            else:
                params = (f"-({params[0]})",)
        gate = ALIASES.get(gate, gate)
        self.ir.ops.append(Op({"r1": "p"}.get(gate, gate), targets, controls, params))

    def body(self, statements: list[ast.stmt]) -> None:
        for stmt in statements:
            if (
                isinstance(stmt, ast.Assign)
                and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)
            ):
                name = stmt.targets[0].id
                value = stmt.value
                if not isinstance(value, ast.Call) or ast.unparse(value.func) not in {
                    "cudaq.qvector",
                    "cudaq.qubit",
                }:
                    reject(stmt, "賦值")
                    continue
                is_vector = ast.unparse(value.func) == "cudaq.qvector"
                if len(value.args) != int(is_vector):
                    reject(stmt, "暫存器")
                size = self.integer(value.args[0]) if is_vector else 1
                if size < 1 or name in self.registers or value.keywords:
                    reject(stmt, "暫存器")
                self.registers[name] = tuple(range(self.ir.num_qubits, self.ir.num_qubits + size))
                self.ir.qreg_names.append((name, size))
                self.ir.num_qubits += size
            elif (
                isinstance(stmt, ast.For)
                and isinstance(stmt.target, ast.Name)
                and isinstance(stmt.iter, ast.Call)
                and isinstance(stmt.iter.func, ast.Name)
                and stmt.iter.func.id == "range"
                and len(stmt.iter.args) == 1
                and not stmt.orelse
            ):
                for index in range(self.integer(stmt.iter.args[0])):
                    self.loops[stmt.target.id] = index
                    self.body(stmt.body)
                self.loops.pop(stmt.target.id, None)
            elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                self.call(stmt.value)
            elif isinstance(stmt, ast.Pass):
                continue
            else:
                reject(stmt)


def from_source(source: str, name: str | None = None) -> Circuit:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ConversionError(f"第 {exc.lineno} 行：{exc.msg}") from exc
    kernels = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and any(ast.unparse(d) == "cudaq.kernel" for d in node.decorator_list)
    ]
    chosen = [node for node in kernels if name is None or node.name == name]
    if len(chosen) != 1:
        raise ConversionError(f"找不到唯一 @cudaq.kernel：{name or '未指定名稱'}")
    return Parser(chosen[0]).ir
