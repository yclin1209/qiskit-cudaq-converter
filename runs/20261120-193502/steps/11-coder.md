# Step 11: coder

start 21:14:09 end 21:44:01 duration 1792.6s

## Prompt (from orchestrator)

你是 coder。專案 /workspace/qiskit-cudaq-converter（讀 AGENTS.md、specs/SPEC.md、docs/plan.md）。第 2 輪 reviewer 與 tester 皆 FAIL，請修正。回覆與文件用繁體中文（專有名詞附英文）。

tests/test_regressions.py 已有 10 個 xfail(strict=True) 案例重現下列問題；修好後移除 xfail 使其成為正常測試。
1. src/qcconvert/qiskit_io.py:299-310 — IR→Qiskit 原始碼（to_source）不可執行：受控閘寫成 qc.x(0, 1)、出現 qc.u3／qc.mx／qc.my、參數成為字串 qc.rx('2 * theta', 0)、缺 QuantumRegister／ClassicalRegister／Parameter／ParameterVector 宣告與 import（numpy/math 若運算式用到 np.pi、math.pi）。修法：受控用 cx/ccx/mcx 或 `XGate().control(n)` + `qc.append(..., [ctrls..., tgt])`（受控 u3 用 UGate），u3→u，mx→h+measure、my→sdg+h+measure，參數輸出為運算式（Parameter 物件運算），暫存器依名稱還原。產生的原始碼要能交給 qiskit_to_cudaq 的 Qiskit 原始碼路徑（exec）重新載入。加測試：對多種 CUDA-Q 原始碼（含 .ctrl、.adj、u3、mx/my、參數運算式、多暫存器、ParameterVector）exec result.code 取 qc，與 to_qiskit() 等價（綁定數值後 Statevector）。
2. src/qcconvert/cudaq_ast.py:10-27、README.md:9 — cudaq 0.17 有 sdg/tdg（見 .venv 內 cudaq/kernel/kernel_builder.py）。加入 GATES，支援 .ctrl／.adj，tests/test_cudaq_ast.py 補原始碼→Qiskit 與受控等價測試，更正 README。另查 cudaq 是否有其他 §3.3 名稱（如 cx、cy、cz、ch、ccx 等 kernel 內可用的函式）；若 cudaq kernel 內可直接用，也一併支援並各補一個測試。
3. widgets — Bell → 切到 CUDA-Q→Qiskit → 再切回 Qiskit→CUDA-Q 後狀態列要為成功且輸出 kernel 與原電路等價；tests/test_widgets.py:15-17 加強斷言。
4. 建議（時間允許）：widgets.py 補 debounce Timer 與錯誤分支測試；隨機語料加入 Parameter 物件、u、r、ccx、受控閘（維持全套 <2 分鐘左右）。

規則：暫存檔只寫 tmp_path；專案根與 tests/ 不留 scratch/probe/debug 檔；不可改 specs/、AGENTS.md、harness/、.opencode/；不可 git commit/push；每次寫檔約 150 行以內。
完成前跑四項 gates 直到全綠：
.venv/bin/python -m pytest -q ; .venv/bin/ruff check src tests scripts ; .venv/bin/ruff format --check src tests scripts ; .venv/bin/mypy src
回覆 15 行內：每項修正（檔案:行號）、gates 最後一行、覆蓋率、耗時、xfail 是否歸零。

## Output

<task id="ses_e06e832b6ffeXvPSF4BGl1KYGb" state="completed">
<task_result>
已修正第 2 輪回報的問題：

- `src/qcconvert/qiskit_io.py:299`：反向產生的 Qiskit 原始碼可執行，保留受控閘、參數運算式與暫存器，並處理 `u3`、`mx`、`my`。
- `src/qcconvert/cudaq_ast.py:10`、`README.md:9`：支援 `sdg`／`tdg` 與實測可用的單控制閘別名（alias）；明確拒絕 CUDA-Q 無法編譯的逆閘修飾形式。
- `src/qcconvert/widgets.py:61`：切換方向時取消待執行的防抖計時器（debounce timer）。
- `tests/test_regressions.py:194`、`tests/test_cudaq_ast.py:11`、`tests/test_widgets.py:8`：移除 10 個嚴格預期失敗（xfail）標記，補上產碼執行、狀態等價與切換測試。

品質關卡（gates）：`ruff format`：26 files left unchanged；`ruff check --fix`：All checks passed!；`mypy src`：Success: no issues found in 12 source files；`pytest -q`：267 passed, 2 warnings in 99.58s。覆蓋率 **92.06%**；xfail **歸零**。仍有 2 項上游警告；本輪無未解決的測試失敗。
</task_result>
</task>
