"""IPython cell magics（儲存轉換結果於使用者命名空間）。"""

import argparse
import shlex
from typing import Any

from IPython.core.magic import Magics, cell_magic, magics_class

from .api import cudaq_to_qiskit, qiskit_to_cudaq
from .qiskit_io import source_to_qiskit
from .runner import compare


@magics_class
class ConverterMagics(Magics):
    def _options(self, line: str, *, run: bool = False) -> argparse.Namespace:
        parser = argparse.ArgumentParser(prog="qcconvert magic")
        parser.add_argument("--name", default="kernel" if run else "qc")
        if run:
            parser.add_argument("--run", action="store_true")
        return parser.parse_args(shlex.split(line))

    @cell_magic
    def qiskit2cudaq(self, line: str, cell: str) -> Any:
        assert self.shell is not None
        options = self._options(line, run=True)
        result = qiskit_to_cudaq(cell, kernel_name=options.name)
        kernel = result.to_kernel()
        self.shell.user_ns[options.name] = kernel
        print(result.code)
        if options.run:
            report = compare(source_to_qiskit(cell), kernel)
            print(f"target: {report.target}; fidelity: {report.fidelity}; TVD: {report.tvd:.6f}")
        return None  # 不讓 IPython 自動渲染 CUDA-Q SVG（無 latex 環境會失敗）。

    @cell_magic
    def cudaq2qiskit(self, line: str, cell: str) -> Any:
        assert self.shell is not None
        options = self._options(line)
        result = cudaq_to_qiskit(cell, circuit_name=options.name)
        qc = result.to_qiskit()
        self.shell.user_ns[options.name] = qc
        print(result.code)
        return None


def load_ipython_extension(ipython: Any) -> None:
    """讓 `%load_ext qcconvert` 註冊兩種 cell magic。"""
    ipython.register_magics(ConverterMagics)
