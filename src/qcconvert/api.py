"""公開轉換介面（public API）。"""

from collections.abc import Sequence
from dataclasses import dataclass

from qiskit import QuantumCircuit

from .cudaq_ast import from_source
from .cudaq_io import load_kernel, object_to_ir, to_source
from .errors import ConversionError
from .ir import Circuit
from .qiskit_io import from_ir, source_to_qiskit, to_ir
from .qiskit_io import to_source as qiskit_source


@dataclass
class ConversionResult:
    code: str
    circuit: Circuit
    warnings: list[str]
    kernel_name: str = "kernel"
    direction: str = "cudaq"

    def to_kernel(self) -> object:
        return load_kernel(self.code, self.kernel_name)

    def to_qiskit(self) -> QuantumCircuit:
        if self.direction != "qiskit":
            raise ConversionError("Qiskit → CUDA-Q 的結果無法以反向介面取回")
        return from_ir(self.circuit)


def qiskit_to_cudaq(
    src: QuantumCircuit | str, *, kernel_name: str = "kernel", decompose_unknown: bool = True
) -> ConversionResult:
    qc = source_to_qiskit(src) if isinstance(src, str) else src
    ir, warnings = to_ir(qc, decompose_unknown=decompose_unknown)
    return ConversionResult(to_source(ir, kernel_name), ir, warnings, kernel_name)


def cudaq_to_qiskit(
    src: str | object, *, args: Sequence[float] = (), circuit_name: str = "qc"
) -> ConversionResult:
    if not circuit_name.isidentifier():
        raise ConversionError(f"無效電路名稱：{circuit_name}")
    if isinstance(src, str):
        ir, warnings = from_source(src), []  # type: Circuit, list[str]
    else:
        ir, warnings = object_to_ir(src, args)
    return ConversionResult(qiskit_source(ir, circuit_name), ir, warnings, direction="qiskit")
