"""可在 notebook 使用的即時雙欄轉換介面（widget）。"""

import threading
from typing import Any

import ipywidgets as widgets
from IPython.display import display

from .api import cudaq_to_qiskit, qiskit_to_cudaq
from .errors import ConversionError
from .qiskit_io import source_to_qiskit
from .runner import compare

BELL = "from qiskit import QuantumCircuit\nqc = QuantumCircuit(2)\nqc.h(0)\nqc.cx(0, 1)\n"


class ConverterApp:
    """編輯輸入時轉換；零延遲模式供無瀏覽器測試。"""

    def __init__(self, debounce: float = 0.3) -> None:
        if debounce < 0:
            raise ValueError("debounce 不可為負數")
        self.input = widgets.Textarea(
            description="輸入", layout=widgets.Layout(width="50%", height="280px")
        )
        self.output = widgets.Textarea(
            description="輸出", disabled=True, layout=widgets.Layout(width="50%", height="280px")
        )
        self.direction = widgets.ToggleButtons(
            options=[("Qiskit → CUDA-Q", "cudaq"), ("CUDA-Q → Qiskit", "qiskit")],
            value="cudaq",
        )
        self.status = widgets.HTML(value="等待輸入")
        self.run_button = widgets.Button(description="在 CUDA-Q 執行並對照")
        self.results = widgets.Output()
        self._debounce = debounce
        self._timer: threading.Timer | None = None
        self.widget = widgets.VBox(
            [
                self.direction,
                widgets.HBox([self.input, self.output]),
                self.status,
                self.run_button,
                self.results,
            ]
        )
        self.input.observe(self._on_input, names="value")
        self.direction.observe(self._on_direction, names="value")
        self.run_button.on_click(self._run)

    def _on_input(self, change: dict[str, Any]) -> None:
        if self._timer is not None:
            self._timer.cancel()
        if self._debounce == 0:
            self.convert()
        else:
            self._timer = threading.Timer(self._debounce, self.convert)
            self._timer.daemon = True
            self._timer.start()

    def _on_direction(self, change: dict[str, Any]) -> None:
        pending, self._timer = self._timer, None
        if pending is not None and pending.is_alive():
            pending.cancel()
            # 延遲中的轉換先以原方向完成，否則切換方向會丟掉剛輸入、尚未轉換的程式碼。
            self.convert(change["old"])
        previous = self.output.value
        self.input.value = previous
        self.convert()

    def convert(self, direction: str | None = None) -> None:
        try:
            result = (
                qiskit_to_cudaq(self.input.value)
                if (direction or self.direction.value) == "cudaq"
                else cudaq_to_qiskit(self.input.value)
            )
            self.output.value = result.code
            self.status.value = "成功" + (
                "；" + "；".join(result.warnings) if result.warnings else ""
            )
        except (ConversionError, ValueError, SyntaxError) as exc:
            self.output.value = ""
            self.status.value = f"錯誤：{exc}"

    def _run(self, button: widgets.Button) -> None:
        self.results.clear_output()
        try:
            if self.direction.value == "cudaq":
                qc = source_to_qiskit(self.input.value)
                kernel = qiskit_to_cudaq(qc).to_kernel()
            else:
                result = cudaq_to_qiskit(self.input.value)
                qc = result.to_qiskit()
                # 原始碼僅以 AST 解析；從驗證過的 IR 重新產生可載入的 kernel。
                kernel = qiskit_to_cudaq(qc).to_kernel()
            report = compare(qc, kernel)
            rows = sorted(report.qiskit_counts.keys() | report.cudaq_counts.keys())
            with self.results:
                print(f"target: {report.target}")
                print("counts (Qiskit | CUDA-Q)")
                for key in rows:
                    print(
                        f"{key}: {report.qiskit_counts.get(key, 0)} | {report.cudaq_counts.get(key, 0)}"
                    )
                print(f"fidelity: {report.fidelity}; TVD: {report.tvd:.6f}")
                if report.distribution_only:
                    print("僅比較分佈（distribution only）；狀態向量不適用")
        except Exception as exc:  # noqa: BLE001
            # 按鈕回呼由前端觸發；比較錯誤必須留在狀態列而非輸出 traceback。
            self.status.value = f"錯誤：{exc}"
            with self.results:
                print(f"錯誤：{exc}")


def show() -> ConverterApp:
    """顯示預填 Bell 電路的雙欄編輯器。"""
    app = ConverterApp()
    app.input.value = BELL
    display(app.widget)  # type: ignore[no-untyped-call]  # IPython display 沒有型別宣告。
    return app
