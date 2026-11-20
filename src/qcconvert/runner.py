"""以 Qiskit 與 CUDA-Q 執行電路並比較。"""

import ast
import os
import time
from collections.abc import Sequence
from dataclasses import replace
from inspect import signature

import cudaq
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import ParameterVectorElement
from qiskit.quantum_info import Statevector

from .equivalence import CompareReport, fidelity, reorder_counts, tvd
from .errors import ConversionError


def _mid_counts(
    kernel: object, args: Sequence[float], mapping: list[tuple[int, int]], width: int, shots: int
) -> dict[str, int]:
    """以 run 的逐次回傳值取得真正的中途測量軌跡（sample 不保留此語意）。"""
    from .cudaq_io import load_kernel

    source = getattr(kernel, "funcSrc", None)
    if not isinstance(source, str):
        raise ConversionError("中途測量需要可讀取原始碼的 kernel")
    try:
        tree = ast.parse(source)
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
        if len(functions) != 1:
            raise ConversionError("中途測量 kernel 函式數量不符")
        function = functions[0]
        names: list[str] = []

        class Capture(ast.NodeTransformer):
            def visit_Expr(self, node: ast.Expr) -> ast.stmt:
                if (
                    isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id == "mz"
                ):
                    name = f"_qcconvert_measure_{len(names)}"
                    names.append(name)
                    return ast.copy_location(
                        ast.Assign(targets=[ast.Name(id=name, ctx=ast.Store())], value=node.value),
                        node,
                    )
                return node

        Capture().visit(function)
        if len(names) != len(mapping):
            raise ConversionError("中途測量 kernel 測量數與 Qiskit 電路不一致")
        function.returns = ast.parse("list[bool]", mode="eval").body
        function.body.append(
            ast.Return(
                value=ast.List(
                    elts=[ast.Name(id=name, ctx=ast.Load()) for name in names], ctx=ast.Load()
                )
            )
        )
        ast.fix_missing_locations(tree)
        captured = load_kernel("import cudaq\n" + ast.unparse(tree), function.name)
        samples = cudaq.run(captured, *args, shots_count=shots)
        counts: dict[str, int] = {}
        if len(samples) != shots:
            raise ConversionError("中途測量回傳的 shot 數量不符")
        for sample in samples:
            if len(sample) != len(mapping):
                raise ConversionError("中途測量回傳的位元數量不符")
            bits = ["0"] * width
            for (_, clbit), bit in zip(mapping, sample):
                bits[width - 1 - clbit] = str(int(bit))
            key = "".join(bits)
            counts[key] = counts.get(key, 0) + 1
        return dict(sorted(counts.items()))
    except ConversionError:
        raise
    except Exception as exc:
        raise ConversionError(f"中途測量無法比較：{exc}") from exc


def _kernel_parameters(kernel: object) -> list[str]:
    """依 CUDA-Q 函式簽章取名稱；不可依 Qiskit 的字母排序推測。"""
    function = getattr(kernel, "kernelFunction", None)
    if function is None:
        raise ConversionError("無法取得 kernel 參數簽章")
    return list(signature(function).parameters)


def pick_target() -> str:
    target = os.getenv("QCCONVERT_TARGET") or (
        "nvidia" if cudaq.num_available_gpus() > 0 else "qpp-cpu"
    )
    cudaq.set_target(target)
    return str(cudaq.get_target().name)


def compare(
    qc: QuantumCircuit,
    kernel: object | None = None,
    *,
    args: Sequence[float] = (),
    shots: int = 4000,
    seed: int | None = 1234,
) -> CompareReport:
    """比較兩電路；args 依 kernel 函式簽章順序，向量各佔一個列表。"""
    from .api import qiskit_to_cudaq
    from .cudaq_io import _identifier

    start = time.monotonic()
    target = pick_target()
    if kernel is None:
        kernel = qiskit_to_cudaq(qc).to_kernel()
    parameters = list(qc.parameters)
    names = {p.vector.name if isinstance(p, ParameterVectorElement) else p.name for p in parameters}
    ordered = _kernel_parameters(kernel)
    if len(args) != len(ordered) or set(ordered) != {_identifier(n) for n in names}:
        raise ConversionError("缺少參數 args 或參數數量不符")
    supplied = dict(zip(ordered, args))
    bindings = {}
    for p in parameters:
        if isinstance(p, ParameterVectorElement):
            values = supplied[_identifier(p.vector.name)]
            if not isinstance(values, (list, tuple)):
                raise ConversionError(f"參數向量 {p.vector.name} 需要數值列表")
            if p.index >= len(values):
                raise ConversionError(f"參數向量 {p.vector.name} 長度不足")
            bindings[p] = values[p.index]
        else:
            bindings[p] = supplied[_identifier(p.name)]
    bound = qc.assign_parameters(bindings) if parameters else qc
    if bound.parameters:
        raise ConversionError("缺少參數 args")
    measured = [
        (bound.find_bit(inst.qubits[0]).index, bound.find_bit(inst.clbits[0]).index)
        for inst in bound.data
        if inst.operation.name == "measure"
    ]
    mapping = measured or [(i, i) for i in range(bound.num_qubits)]
    width = bound.num_clbits if measured else bound.num_qubits
    operations = list(bound.data)
    mid = any(
        inst.operation.name == "measure"
        and any(
            later.operation.name not in {"measure", "barrier"} and inst.qubits[0] in later.qubits
            for later in operations[index + 1 :]
        )
        for index, inst in enumerate(operations)
    )
    clean = bound.remove_final_measurements(inplace=False)
    state: float | None = None
    equal: bool | None = None
    if not mid:
        reference = np.asarray(Statevector.from_instruction(clean).data)
        state_kernel = kernel
        if measured:
            # get_state 對 mz 不代表測量前的純態；只從使用者 kernel 重建演化。
            from .cudaq_ast import from_source
            from .cudaq_io import load_kernel, to_source

            source = getattr(kernel, "funcSrc", None)
            if isinstance(source, str):
                try:
                    ir = from_source(source)
                    bare = replace(ir, ops=[op for op in ir.ops if op.name != "measure"])
                    state_kernel = load_kernel(to_source(bare, "state_kernel"), "state_kernel")
                except ConversionError:
                    state_kernel = None
            else:
                state_kernel = None
        if state_kernel is not None:
            state_args = (
                tuple(supplied[name] for name in _kernel_parameters(state_kernel))
                if measured
                else args
            )
            actual = np.asarray(cudaq.get_state(state_kernel, *state_args))
            state = fidelity(reference, actual)
            equal = state >= (1 - 1e-4 if target == "nvidia" else 1 - 1e-6)
    if seed is not None:
        cudaq.set_random_seed(seed)
    if mid:
        cuda_counts = _mid_counts(kernel, args, mapping, width, shots)
    else:
        sampled = dict(cudaq.sample(kernel, *args, shots_count=shots).items())
        # CUDA-Q 僅輸出已測量 qubit，依 qubit 索引而非 mz 呼叫順序排列。
        sample_mapping = (
            [(sorted({q for q, _ in mapping}).index(q), c) for q, c in mapping]
            if measured
            else mapping
        )
        try:
            cuda_counts = reorder_counts(sampled, sample_mapping, width)
        except (IndexError, ValueError) as exc:
            raise ConversionError(f"CUDA-Q 測量結果與 Qiskit clbit 對應不符：{exc}") from exc
    if mid:
        from qiskit_aer import AerSimulator

        ref_circuit = bound.copy()
        if not measured:
            ref_circuit.measure_all()
        ref_counts = dict(
            AerSimulator().run(ref_circuit, shots=shots, seed_simulator=seed).result().get_counts()
        )
    else:
        rng = np.random.default_rng(seed)
        probabilities = Statevector.from_instruction(clean).probabilities()
        indices = rng.choice(len(probabilities), shots, p=probabilities)
        ref_counts = {}
        for index in indices:
            bits = ["0"] * width
            for q, c in mapping:
                bits[width - 1 - c] = str((int(index) >> q) & 1)
            key = "".join(bits)
            ref_counts[key] = ref_counts.get(key, 0) + 1
    return CompareReport(
        state,
        equal,
        dict(sorted(ref_counts.items())),
        cuda_counts,
        tvd(ref_counts, cuda_counts),
        target,
        time.monotonic() - start,
        mid or state is None,
    )
