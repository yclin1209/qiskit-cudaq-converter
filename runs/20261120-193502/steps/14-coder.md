# Step 14: coder

start 22:35:26 end 22:52:40 duration 1034.1s

## Prompt (from orchestrator)

你是 coder。專案 /workspace/qiskit-cudaq-converter（讀 AGENTS.md、specs/SPEC.md、docs/plan.md）。第 3 輪 reviewer PASS、tester FAIL，請修正。回覆與文件用繁體中文（專有名詞附英文）。

問題（tester 第 3 輪，已在 tests/test_regressions.py:355-369、392-402、407-418 以 xfail(strict=True) 重現）：
- src/qcconvert/qiskit_io.py:307-328 — 反向產生的 Qiskit 原始碼中，kernel 參數名若為 `qc`、`_base`、`_qr0`（或其他與產生的內部變數、`circuit_name`、暫存器變數、import 名稱 `np`/`math`/`QuantumCircuit`/`Parameter` 等衝突者）會覆蓋變數，exec 後 CircuitError；widget 對此顯示「成功」但輸出不可執行。
修法：反向產碼時對 Parameter 的 Python 變數名做清理／去衝突（Parameter 顯示名稱可保留原名，例如 `theta_qc = Parameter("qc")`），內部暫存變數也用不會與使用者名稱衝突的命名；保證任何合法 kernel 參數名產碼都可 exec，且與 to_qiskit() 等價。修好後移除那些 xfail，並補一個參數化測試涵蓋多個衝突名稱（qc、_base、_qr0、np、math、Parameter、QuantumCircuit、circuit_name 本身）。
建議（順手做）：隨機語料擴大閘集合（u、r、sxdg、ccx、受控閘等）但全套維持 2 分鐘內。

規則：暫存檔只寫 tmp_path；專案根與 tests/ 不留 scratch/probe/debug 檔；不可改 specs/、AGENTS.md、harness/、.opencode/；不可 git commit/push；每次寫檔約 150 行以內。
完成前跑四項 gates 直到全綠：
.venv/bin/python -m pytest -q ; .venv/bin/ruff check src tests scripts ; .venv/bin/ruff format --check src tests scripts ; .venv/bin/mypy src
回覆 12 行內：修正（檔案:行號）、gates 最後一行、覆蓋率、耗時、xfail 是否歸零。

## Output

<task id="ses_e069dc805ffeJgdhiIZxL3ovaH" state="completed">
<task_result>
已修正反向產碼的名稱衝突：參數保留原顯示名稱，Python 變數、import 別名與內部暫存變數則避開衝突；參數運算式同步改寫（`src/qcconvert/qiskit_io.py:299`）。
已移除三處 `xfail`，並加入多個衝突名稱及複合運算式回歸測試（`tests/test_regressions.py:355`、`tests/test_regressions.py:392`）。
- `ruff format src tests scripts`：26 files left unchanged
- `ruff check --fix src tests scripts`：All checks passed!
- `mypy src`：Success: no issues found in 12 source files
- `pytest -q`：288 passed, 2 warnings in 48.95s；覆蓋率 92.70%；`xfail` 0
- 固定 gates 複查：`ruff check` 全過；`ruff format --check` 26 files already formatted；`mypy` 全過。
尚未解決：無本次修正相關問題；仍有 2 項既有套件警告。
</task_result>
</task>
