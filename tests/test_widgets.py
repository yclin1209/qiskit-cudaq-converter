"""雙欄編輯器（widget）驗收。"""

import ipywidgets as widgets
from qiskit.quantum_info import Statevector

from qcconvert import qiskit_to_cudaq
from qcconvert.qiskit_io import source_to_qiskit
from qcconvert.widgets import BELL, ConverterApp


def test_live_direction_and_errors() -> None:
    app = ConverterApp(debounce=0)
    app.input.value = BELL
    assert isinstance(app.input, widgets.Textarea)
    assert app.output.disabled and "@cudaq.kernel" in app.output.value
    assert "成功" in app.status.value
    generated = app.output.value
    app.direction.value = "qiskit"
    assert app.input.value == generated
    assert "成功" in app.status.value
    assert "QuantumCircuit" in app.output.value
    assert Statevector(source_to_qiskit(app.output.value)).equiv(
        Statevector(source_to_qiskit(BELL))
    )
    app.direction.value = "cudaq"
    assert "成功" in app.status.value and "@cudaq.kernel" in app.output.value
    assert Statevector(source_to_qiskit(app.input.value)).equiv(Statevector(source_to_qiskit(BELL)))
    assert qiskit_to_cudaq(app.input.value).circuit.ops
    app.direction.value = "qiskit"
    app.input.value = "@cudaq.kernel\ndef broken(:"
    assert "錯誤" in app.status.value and "行" in app.status.value
    assert "Traceback" not in app.status.value


def test_run_button(monkeypatch: object, capsys: object) -> None:
    import os

    from _pytest.capture import CaptureFixture
    from _pytest.monkeypatch import MonkeyPatch

    assert isinstance(monkeypatch, MonkeyPatch)
    assert isinstance(capsys, CaptureFixture)
    monkeypatch.setenv("QCCONVERT_TARGET", "qpp-cpu")
    app = ConverterApp(debounce=0)
    app.input.value = BELL
    app.run_button.click()
    printed = capsys.readouterr().out
    assert "qpp-cpu" in printed
    assert "counts" in printed and "fidelity" in printed and "TVD" in printed
    assert os.environ["QCCONVERT_TARGET"] == "qpp-cpu"
