"""狀態與機率分佈的等價指標（equivalence metrics）。"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass
class CompareReport:
    fidelity: float | None
    statevector_equal: bool | None
    qiskit_counts: dict[str, int]
    cudaq_counts: dict[str, int]
    tvd: float
    target: str
    elapsed: float
    distribution_only: bool = False


def fidelity(a: NDArray[np.complex128], b: NDArray[np.complex128]) -> float:
    return float(abs(np.vdot(a, b)) ** 2)


def tvd(a: dict[str, int], b: dict[str, int]) -> float:
    na, nb = sum(a.values()), sum(b.values())
    return 0.5 * sum(abs(a.get(key, 0) / na - b.get(key, 0) / nb) for key in a.keys() | b.keys())


def reorder_counts(
    raw: dict[str, int], mapping: list[tuple[int, int]], width: int
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for key, value in raw.items():
        bits = ["0"] * width
        for qubit, clbit in mapping:
            bits[width - 1 - clbit] = key[qubit]
        label = "".join(bits)
        counts[label] = counts.get(label, 0) + value
    return dict(sorted(counts.items()))
