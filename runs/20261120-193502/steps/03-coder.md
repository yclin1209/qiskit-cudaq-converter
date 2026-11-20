# Step 3: coder

start 19:45:54 end 19:50:05 duration 251.3s

## Prompt (from orchestrator)

請補齊批次 A 尚未完成的部分（繁體中文回覆）：
1. SPEC §5 第 2 條：§3.3 每個支援的閘（id h x y z s sdg t tdg sx sxdg rx ry rz p u u3 u1 u2 r cx cy cz ch swap crx cry crz cp cu1 ccx cswap mcx rzz rxx ryy，以及 barrier/reset/measure）各有一個 Qiskit→CUDA-Q 等價測試，能受控者各有一個「控制位元處於 |+>」的受控等價測試（用 gate.control(1) 並在控制位元先 h）。建議用 pytest.mark.parametrize，放在 tests/test_gate_mapping.py。
2. SPEC §5 第 8 條（Qiskit 端）：if_test、c_if（qiskit 2.x 若已移除 c_if，請測等價的建構或說明並以 if_test/IfElseOp 舊式表示）、while_loop、for_loop、switch、initialize、StatePreparation（decompose_unknown=False）、delay、pulse（若 qiskit 2.x 無 pulse，用自訂帶 calibration 的名義或說明以 待確認 記錄於 docs/plan.md §7）各有測試，斷言 UnsupportedFeatureError 且訊息含建構名稱。放 tests/test_errors.py。
3. 可將 tests/test_batch_a.py 依 docs/plan.md §5 拆成有意義的檔名（test_parameters.py、test_measurements.py、test_qiskit_source.py、test_corpus.py 等），每次寫檔 ≤150 行。
完成後四項 gates 全綠，回覆 15 行內：新增測試數、gates 最後一行、覆蓋率、耗時。

## Output

<task id="ses_e073f20d9ffeHvgu8xzS1ZfUP5" state="completed">
<task_result>
已補齊批次 A 的閘測試與 Qiskit 端不支援建構測試：新增 `tests/test_gate_mapping.py`、`tests/test_errors.py`，並修正 `src/qcconvert/qiskit_io.py` 對受控 `id`、舊式條件與脈衝替代建構的處理。新增 **91 個測試案例**；全套現有 150 個通過。

Qiskit 2.x 已移除 `InstructionSet.c_if` 與 pulse／calibration API；測試分別以舊式條件 `Gate` 及命名閘替代，**未宣稱測到原生 pulse API**。`tests/test_batch_a.py` 本輪未拆檔。

- `ruff format src tests scripts`：`2 files reformatted, 10 files left unchanged`
- `ruff check --fix src tests scripts`：`Found 1 error (1 fixed, 0 remaining).`
- `mypy src`：`Success: no issues found in 8 source files`
- `pytest -q`：`150 passed, 2 warnings in 18.93s`；覆蓋率 **93.04%**
- 原樣檢查：`ruff check` → `All checks passed!`；`ruff format --check` → `12 files already formatted`

尚未解決：Qiskit 2.x 原生 pulse API 無法直接驗證；批次 B／C 不在本輪範圍。
</task_result>
</task>
