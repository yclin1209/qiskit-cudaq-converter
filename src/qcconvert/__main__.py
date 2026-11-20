"""命令列轉換器（CLI）。"""

import argparse
import sys
from pathlib import Path

from .api import cudaq_to_qiskit, qiskit_to_cudaq
from .errors import ConversionError
from .qiskit_io import source_to_qiskit
from .runner import compare


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Qiskit ⇄ CUDA-Q 電路轉換")
    parser.add_argument("input", type=Path)
    parser.add_argument("--to", choices=("cudaq", "qiskit"), required=True)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        source = args.input.read_text(encoding="utf-8")
        result = qiskit_to_cudaq(source) if args.to == "cudaq" else cudaq_to_qiskit(source)
        if args.output:
            args.output.write_text(result.code, encoding="utf-8")
        else:
            print(result.code)
        if args.check:
            if args.to != "cudaq":
                raise ConversionError(
                    "CUDA-Q 原始碼只作 AST 靜態解析，無法安全執行原始參考以 --check"
                )
            report = compare(source_to_qiskit(source), result.to_kernel())
            print(f"fidelity: {report.fidelity}; TVD: {report.tvd:.6f}", file=sys.stderr)
            return 0 if report.statevector_equal is not False and report.tvd <= 0.05 else 1
        return 0
    except Exception as exc:  # noqa: BLE001
        # CLI 的比較失敗亦屬轉換／檢查錯誤，不向使用者洩漏 traceback。
        print(f"轉換錯誤：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
