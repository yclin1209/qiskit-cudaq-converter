# Step 16: tester

start 23:23:08 end 23:59:34 duration 2186.4s

## Prompt (from orchestrator)

你是 tester。專案 /workspace/qiskit-cudaq-converter。讀 AGENTS.md、specs/SPEC.md、docs/plan.md，獨立跑 gates、補邊界測試、把問題重現成失敗測試。回覆用繁體中文（專有名詞附英文）。

第 4 輪。
1. 獨立執行四項 gates，記錄最後一行、覆蓋率、耗時：
   .venv/bin/python -m pytest -q ; .venv/bin/ruff check src tests scripts ; .venv/bin/ruff format --check src tests scripts ; .venv/bin/mypy src
2. SPEC §5 凍結 14 條逐條 PASS／FAIL 附依據（檔案:行號）；範圍外只列「建議」，不可作為 FAIL 理由。
3. 獨立驗證上一輪修正：反向 Qiskit 原始碼參數名衝突（src/qcconvert/qiskit_io.py:299 起；測試 tests/test_regressions.py:355、392）。
4. reviewer 第 4 輪發現（出處：reviewer），請獨立檢查並重現成 xfail(strict=True) 測試放 tests/test_regressions.py：
   - src/qcconvert/runner.py:41-48 — compare 依參數名排序綁定 args，但 kernel args 依簽章順序；kernel(theta: float, alpha: float) 反向後 compare(r.to_qiskit(), k, args=(0.3, 1.9)) fidelity 0.2356。
   - src/qcconvert/runner.py:81 — 有測量時狀態向量比較用 qiskit_to_cudaq(clean) 重新產生的 kernel，而非使用者傳入的 kernel；a=h;measure 對照 kernel b=h;z;measure 回報 statevector_equal=True。
5. 另外獨立找其他 compare／CLI --check／widget 執行按鈕的邊界問題。
規則：暫存檔只寫 tmp_path；專案根與 tests/ 不留 scratch/probe/debug 檔；只新增／修改測試，不改 src/。結束時 gates 維持全綠（xfail 可）。
回覆 35 行內；最後一行必須是 `VERDICT: PASS` 或 `VERDICT: FAIL`。

## Output

<task id="ses_e06721c38ffei1KD9u8zh3kmMO" state="completed">
<task_result>
第 4 輪驗證結果：四項品質關卡（gates）全綠；reviewer 提出的兩項 `compare` 問題均已獨立重現，並以嚴格預期失敗（`xfail(strict=True)`）保留測試。

**SPEC §5 逐條結果**
1. PASS — 四項 gates 全過、覆蓋率 92.70%；本輪 pytest 耗時 430.18 秒。
2. PASS — 支援閘及受控等價：`tests/test_gate_mapping.py:12-53`。
3. PASS — CUDA-Q 閘、`.ctrl`、`.adj`：`tests/test_cudaq_ast.py:11-151`。
4. PASS — 固定 seed 的 200 個電路、其中 50 個反向轉換：`tests/test_gate_mapping_extra.py:131-172`。
5. PASS — 參數、向量與運算式，三組數值：`tests/test_gate_mapping_extra.py:102-121`。
6. PASS — 位元順序與測量分佈：`tests/test_gate_mapping_extra.py:124-128,175-203`；`tests/test_regressions.py:81-89,128-143`。
7. PASS — 多量子暫存器雙向轉換：`tests/test_gate_mapping_extra.py:175-193`；`tests/test_regressions.py:112-125`。
8. PASS — 不支援建構及錯誤訊息：`tests/test_errors.py`、`tests/test_cudaq_errors.py`。
9. PASS — Qiskit 原始碼四種選取／錯誤情況：`tests/test_gate_mapping_extra.py:85-92`。
10. PASS — kernel 物件反向轉換：`tests/test_kernel_object.py`。
11. PASS — widget 即時轉換、方向與按鈕：`tests/test_widgets.py:11-50`。
12. PASS — 兩種 cell magic：`tests/test_magics.py`。
13. PASS — notebook 無頭執行：`tests/test_notebook.py:9-27`。
14. PASS — 暫存路徑打包、解壓與匯入：`tests/test_build_dist.py:8-37`。

**新增與重現**：上一輪參數名稱衝突測試及反向 widget 按鈕測試通過（`tests/test_regressions.py:355-445`）。本輪新增三項：簽章順序、測量電路狀態向量、測量後作用於另一 qubit（`tests/test_regressions.py:489-520`）；第三項通過。以 `--runxfail` 重現前兩項失敗：簽章順序的 fidelity 為 **0.6443345396**，低於 `1 - 1e-6`；傳入不等價的已測量 kernel，卻得到 `statevector_equal=True`、fidelity **0.9999999999999996**。兩項均屬待修問題，不是通過的等價證明。

**Gates 實際輸出摘要**：pytest `289 passed, 2 xfailed, 2 warnings in 430.18s`，覆蓋率 **92.70%**；ruff check `All checks passed!`；ruff format check `26 files already formatted`；mypy `Success: no issues found in 12 source files`。已執行 `ruff format tests`。CLI `--check` 與打包結果由 `tests/test_regressions.py:162-183` 的實際子程序測試驗證通過；未另行取得三項靜態關卡的獨立耗時數字。

VERDICT: PASS
</task_result>
</task>
