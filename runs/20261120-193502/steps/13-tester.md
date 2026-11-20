# Step 13: tester

start 22:04:36 end 22:35:09 duration 1833.3s

## Prompt (from orchestrator)

你是 tester。專案 /workspace/qiskit-cudaq-converter。讀 AGENTS.md、specs/SPEC.md、docs/plan.md，獨立跑 gates、補邊界測試、把問題重現成失敗測試。回覆用繁體中文（專有名詞附英文）。

第 3 輪。coder 宣稱修正：反向 Qiskit 原始碼可執行（src/qcconvert/qiskit_io.py:299）、sdg/tdg 與別名支援（src/qcconvert/cudaq_ast.py:10）、widget 方向來回切換（src/qcconvert/widgets.py:61）；tests/test_regressions.py 的 xfail 已歸零。
1. 獨立執行四項 gates，記錄最後一行、覆蓋率、耗時：
   .venv/bin/python -m pytest -q ; .venv/bin/ruff check src tests scripts ; .venv/bin/ruff format --check src tests scripts ; .venv/bin/mypy src
2. SPEC §5 凍結 14 條逐條 PASS／FAIL 附依據（檔案:行號）；範圍外只列「建議」，不可作為 FAIL 理由。
3. 獨立驗證上述三項修正（自行寫測試重現，不只看現有測試）。
4. reviewer 第 3 輪建議（出處：reviewer，非阻擋），請獨立檢查並判斷是否影響 §5 任一條：qiskit_io.py:307-328 反向原始碼中 kernel 參數名為 `qc` 或 `_base` 時覆蓋電路變數導致 CircuitError；test_gate_mapping_extra.py:142 隨機語料只抽 8 種閘且無 Parameter；widgets.py:83-106 執行按鈕只測 Qiskit→CUDA-Q 方向。能重現就寫成 xfail(strict=True) 測試放 tests/test_regressions.py。
規則：暫存檔只寫 tmp_path；專案根與 tests/ 不留 scratch/probe/debug 檔；只新增／修改測試，不改 src/。結束時 gates 維持全綠。
回覆 40 行內；最後一行必須是 `VERDICT: PASS` 或 `VERDICT: FAIL`。

## Output

<task id="ses_e06ba0061ffeTro4tcLZtqkXqI" state="completed">
<task_result>
**第 3 輪結論：四項品質關卡（gates）全綠，但反向產碼有已重現的缺陷，驗收未全過。**

SPEC §5 逐條核對：
1. **PASS** — 四項 gates 全過；覆蓋率 92.59%（本輪輸出）。
2. **PASS** — 支援閘及受控等價：`tests/test_gate_mapping.py:12-53`；獨立補驗 `tests/test_regressions.py:441`。
3. **PASS** — CUDA-Q 閘、`.ctrl`、`.adj` 等價：`tests/test_cudaq_ast.py:11-151`；別名獨立補驗 `tests/test_regressions.py:421`。
4. **PASS** — 固定 seed 的 200 個含符號參數電路、前 50 個 round trip：`tests/test_gate_mapping_extra.py:131-172`。
5. **PASS** — 參數、向量與運算式三組數值：`tests/test_gate_mapping_extra.py:102-121`、`tests/test_regressions.py:212-240`。
6. **PASS** — 位元順序、GHZ、部分測量與多 creg：`tests/test_gate_mapping_extra.py:124-128`、`tests/test_regressions.py:81-90,128-143`。
7. **PASS** — 多量子暫存器（QuantumRegister）雙向轉換：`tests/test_gate_mapping_extra.py:175-193`、`tests/test_regressions.py:112-125`。
8. **PASS** — 不支援建構及行號：`tests/test_errors.py:46-72`、`tests/test_cudaq_errors.py:8-49`。
9. **PASS** — Qiskit 原始碼四種選取／錯誤情況：`tests/test_gate_mapping_extra.py:85-92`。
10. **PASS** — 五種 kernel 物件含參數：`tests/test_kernel_object.py:12-30`。
11. **FAIL** — 一般雙向切換及按鈕通過，但反向 widget 對合法參數 `qc` 顯示「成功」，輸出卻無法執行：`tests/test_regressions.py:407-418`。
12. **PASS** — 兩個 cell magic 與等價檢查：`tests/test_magics.py:10-30`。
13. **PASS** — notebook 無頭執行：`tests/test_notebook.py:9-27`。
14. **PASS** — 暫存路徑打包、解壓匯入及 Bell 轉換：`tests/test_build_dist.py:8-37`。

**新增與重現：**補含 Parameter 的語料、反向 widget 執行按鈕、受控 `sx`／`u`、逆閘及別名；0／1 qubit、未測量、部分測量、多暫存器與深電路已有測試。CLI `python -m qcconvert ... --check` 及 `scripts/build_dist.py` 均由 `tests/test_regressions.py:162-183` 實際執行通過。Reviewer 所指 `qc`、`_base` 衝突已重現；另獨立找到 `_qr0` 衝突，均以 strict xfail 留存（`tests/test_regressions.py:355-369,392-402`）。用 `--runxfail` 確認錯誤為 `CircuitError: Invalid param type <class 'qiskit.circuit.quantumcircuit.QuantumCircuit'> for gate rx`；`_qr0` 為 `QuantumRegister` 型別。語料僅抽八種閘屬擴充**建議**，不另列 FAIL。

**最終 gates 實際摘要：**pytest `274 passed, 4 xfailed, 2 warnings in 42.46s`，覆蓋率 **92.59%**；ruff check `All checks passed!`；ruff format check `26 files already formatted`；mypy `Success: no issues found in 12 source files`。非 pytest 三項未獨立計時，不虛報耗時；已執行 `ruff format tests`。

VERDICT: FAIL
</task_result>
</task>
