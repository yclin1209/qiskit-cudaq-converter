"""產生 CUDA-Q kernel 原始碼並從真實 Python 檔載入。"""

import builtins
import hashlib
import importlib.util
import keyword
import re
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

import cudaq
from qiskit import qasm2

from .errors import ConversionError
from .ir import Circuit, Op
from .qiskit_io import to_ir

RESERVED = {
    "q",
    "cudaq",
    "np",
    "math",
    "h",
    "x",
    "y",
    "z",
    "s",
    "t",
    "sdg",
    "tdg",
    "sx",
    "sxdg",
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
    "id",
    "p",
    "u",
    "u1",
    "u2",
    "r",
    "cx",
    "cy",
    "cz",
    "ch",
    "crx",
    "cry",
    "crz",
    "cp",
    "cu1",
    "ccx",
    "cswap",
    "mcx",
    "rxx",
    "ryy",
    "rzz",
    "measure",
    "barrier",
} | set(dir(builtins))


def _identifier(name: str) -> str:
    clean = re.sub(r"\W", "_", name)
    if not clean or clean[0].isdigit() or keyword.iskeyword(clean) or clean in RESERVED:
        clean = "param_" + clean
    return clean


def to_source(ir: Circuit, name: str = "kernel") -> str:
    if not name.isidentifier() or keyword.iskeyword(name):
        raise ConversionError(f"無效 kernel 名稱：{name}")
    names = {p: _identifier(p) for p in ir.params}
    if len(set(names.values())) != len(names):
        raise ConversionError("參數名稱清理後重複")
    vector_names = {
        p
        for p in names
        if any(re.search(r"\b" + re.escape(p) + r"\[", str(v)) for op in ir.ops for v in op.params)
    }
    ordered = sorted(names, key=lambda p: (p in vector_names, p))
    signature = ", ".join(
        f"{names[p]}: {'list[float]' if p in vector_names else 'float'}" for p in ordered
    )
    lines = [
        "import cudaq",
        "import numpy as np",
        "",
        "@cudaq.kernel",
        f"def {name}({signature}):",
        f"    q = cudaq.qvector({ir.num_qubits})",
    ]
    start = 0
    for reg, size in ir.qreg_names:
        lines.append(f"    # {reg}: q[{start}:{start + size}]")
        start += size

    def param(value: float | str) -> str:
        text = repr(value) if isinstance(value, float) else value
        for original, clean in names.items():
            text = re.sub(r"\b" + re.escape(original) + r"\b", clean, text)
        return text

    def emit(
        gate: str,
        targets: tuple[int, ...],
        controls: tuple[int, ...] = (),
        params: tuple[float | str, ...] = (),
    ) -> None:
        args = [param(p) for p in params] + [f"q[{i}]" for i in (*controls, *targets)]
        lines.append(f"    {gate}{'.ctrl' if controls else ''}({', '.join(args)})")

    def generate(op: Op) -> None:
        gate, target, ctrl, values = op.name, op.targets, op.controls, op.params
        if gate == "measure":
            emit("mz", target)
        elif gate == "reset":
            emit("reset", target)
        elif gate in {"sx", "sxdg"}:
            emit("h", target, ctrl)
            emit(
                "s" if gate == "sx" else "r1",
                target,
                ctrl,
                () if gate == "sx" else (-1.5707963267948966,),
            )
            emit("h", target, ctrl)
        elif gate in {"rzz", "rxx", "ryy"}:
            a, b = target
            if gate == "rxx":
                emit("h", (a,), ctrl)
                emit("h", (b,), ctrl)
            if gate == "ryy":
                emit("rx", (a,), ctrl, (1.5707963267948966,))
                emit("rx", (b,), ctrl, (1.5707963267948966,))
            emit("x", (b,), (*ctrl, a))
            emit("rz", (b,), ctrl, values)
            emit("x", (b,), (*ctrl, a))
            if gate == "rxx":
                emit("h", (a,), ctrl)
                emit("h", (b,), ctrl)
            if gate == "ryy":
                emit("rx", (a,), ctrl, (-1.5707963267948966,))
                emit("rx", (b,), ctrl, (-1.5707963267948966,))
        elif gate == "r":
            emit("rz", target, ctrl, (f"-({param(values[1])})",))
            emit("rx", target, ctrl, (values[0],))
            emit("rz", target, ctrl, (values[1],))
        elif gate in {"u", "u3", "u2"}:
            angles = values if gate != "u2" else (1.5707963267948966, *values)
            if len(angles) == 4:
                emit("r1", (ctrl[-1],), ctrl[:-1], (angles[3],))
            emit("u3", target, ctrl, angles[:3])
        elif gate in {"p", "u1"}:
            emit("r1", target, ctrl, values)
        elif gate in {"sdg", "tdg"}:
            emit(
                "r1", target, ctrl, (-1.5707963267948966 if gate == "sdg" else -0.7853981633974483,)
            )
        else:
            emit(gate, target, ctrl, values)

    for op in ir.ops:
        generate(op)
    return "\n".join(lines) + "\n"


def load_kernel(code: str, name: str) -> object:
    digest = hashlib.sha256(code.encode()).hexdigest()
    module_name = f"_qcconvert_{digest}"
    directory = Path(tempfile.gettempdir()) / "qcconvert_kernels"
    directory.mkdir(exist_ok=True)
    path = directory / f"{digest}.py"
    if not path.exists() or path.read_text(encoding="utf-8") != code:
        path.write_text(code, encoding="utf-8")
    if module_name not in sys.modules:
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ConversionError("無法載入 kernel 原始碼")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            del sys.modules[module_name]
            raise
    return getattr(sys.modules[module_name], name)


def object_to_ir(kernel: object, args: Sequence[float]) -> tuple[Circuit, list[str]]:
    """透過 CUDA-Q 的 OpenQASM 2 翻譯實體 kernel。"""
    try:
        compiled = cudaq.synthesize(kernel, *args) if args else kernel
        qasm = cudaq.translate(compiled, format="openqasm2")
        ir, warnings = to_ir(qasm2.loads(qasm))
    except Exception as exc:
        raise ConversionError(f"kernel OpenQASM 2 翻譯失敗：{exc}") from exc
    if re.search(r"\bcrz\s*\(|\bcrz\s+", qasm, re.IGNORECASE):
        warnings.append("OpenQASM 2 的 rz 可能來自 r1；受控相位不可保證")
    return ir, warnings
