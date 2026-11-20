"""電路中間表示（intermediate representation）。"""

from dataclasses import dataclass, field


@dataclass
class Op:
    name: str
    targets: tuple[int, ...]
    controls: tuple[int, ...] = ()
    params: tuple[float | str, ...] = ()
    clbits: tuple[int, ...] = ()


@dataclass
class Circuit:
    num_qubits: int
    num_clbits: int = 0
    ops: list[Op] = field(default_factory=list)
    params: list[str] = field(default_factory=list)
    qreg_names: list[tuple[str, int]] = field(default_factory=list)
    creg_names: list[tuple[str, int]] = field(default_factory=list)
