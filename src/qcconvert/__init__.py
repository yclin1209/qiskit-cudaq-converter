"""Qiskit 與 CUDA-Q 電路轉換。

核心 API 不需要 ipywidgets／IPython；`show()` 與 `load_ipython_extension()` 在呼叫時才載入。
"""

from typing import Any

from .api import ConversionResult, cudaq_to_qiskit, qiskit_to_cudaq
from .cudaq_io import load_kernel
from .equivalence import CompareReport
from .errors import ConversionError, UnsupportedFeatureError
from .runner import compare, pick_target


def show(*args: Any, **kwargs: Any) -> Any:
    """開啟雙欄編輯器（需要 ipywidgets：`pip install ipywidgets` 或 `pip install qcconvert[colab]`）。"""
    try:
        from .widgets import show as _show
    except ImportError as exc:
        raise ImportError(
            "qcconvert.show() 需要 ipywidgets；請執行 `pip install ipywidgets`"
        ) from exc
    return _show(*args, **kwargs)


def load_ipython_extension(ipython: Any) -> None:
    """`%load_ext qcconvert` 進入點（需要 IPython）。"""
    from .magics import load_ipython_extension as _load

    _load(ipython)


__all__ = [
    "CompareReport",
    "ConversionError",
    "ConversionResult",
    "UnsupportedFeatureError",
    "compare",
    "cudaq_to_qiskit",
    "load_ipython_extension",
    "load_kernel",
    "pick_target",
    "qiskit_to_cudaq",
    "show",
]
