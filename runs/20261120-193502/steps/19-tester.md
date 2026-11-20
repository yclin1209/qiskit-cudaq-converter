# Step 19: tester

start 00:42:55 end 01:26:48 duration 2632.7s

## Prompt (from orchestrator)

你是 tester。專案 /workspace/qiskit-cudaq-converter。讀 AGENTS.md、specs/SPEC.md、docs/plan.md，獨立跑 gates、補邊界測試、把問題重現成失敗測試。回覆用繁體中文（專有名詞附英文）。

第 5 輪。
1. 獨立執行四項 gates，記錄最後一行、覆蓋率、耗時：
   .venv/bin/python -m pytest -q ; .venv/bin/ruff check src tests scripts ; .venv/bin/ruff format --check src tests scripts ; .venv/bin/mypy src
2. SPEC §5 凍結 14 條逐條 PASS／FAIL 附依據（檔案:行號）；範圍外只列「建議」，不可作為 FAIL 理由。
3. 獨立驗證上輪修正：src/qcconvert/runner.py:17,34,44（compare args 依 kernel 簽章順序）、runner.py:88（末端測量從使用者 kernel 重建；不能則只比分佈）。
4. reviewer 第 5 輪發現（出處：reviewer），請獨立檢查並重現成 xfail(strict=True) 測試放 tests/test_regressions.py：
   - src/qcconvert/runner.py:121-124、equivalence.py:37 — 電路 h(0); measure(0,0); cx(0,1); measure(1,1)（多 qubit 中途測量），CUDA-Q 取樣位元字串長度不足，reorder_counts IndexError，compare 當掉。
   - src/qcconvert/__main__.py:36、widgets.py:106 — 上述例外未攔截：CLI --check 印 traceback 而非 exit 2；widget 執行按鈕丟出例外／traceback。
5. 另外獨立找其他中途測量、reset 後測量、重複測量同一 qubit 的邊界問題。
規則：暫存檔只寫 tmp_path；專案根與 tests/ 不留 scratch/probe/debug 檔；只新增／修改測試，不改 src/。結束時 gates 維持全綠（xfail 可）。
回覆 35 行內；最後一行必須是 `VERDICT: PASS` 或 `VERDICT: FAIL`。

## Output

<task id="ses_e06290ed7ffeERbijn7Lwx5qOD" state="completed">
<task_result>
**第 5 輪結論：四項品質關卡（gates）全綠，但中途測量的等價比較仍有已重現缺陷，驗收不通過。**

SPEC §5 逐條核對：
1. PASS — 四項 gates 全過；行覆蓋率 92.44%（下列實際輸出）。
2. PASS — 支援閘及受控閘的等價測試：`tests/test_gate_mapping.py:12-53`。
3. PASS — CUDA-Q 閘、`.ctrl`、`.adj`：`tests/test_cudaq_ast.py:11-66,138-151`。
4. PASS — 固定 seed、200 個電路及其中 50 個往返：`tests/test_gate_mapping_extra.py:131-172`。
5. PASS — 純量、向量、運算式及三組綁定值：`tests/test_gate_mapping_extra.py:102-121`。
6. **FAIL** — 部分測量與位元順序有測試，但多 qubit 中途測量觸發 `IndexError`；重複測量的 TVD 為 1.0：`tests/test_regressions.py:553-559,605-615`。
7. PASS — 多暫存器雙向案例：`tests/test_gate_mapping_extra.py:175-193`、`tests/test_regressions.py:112-125`。
8. PASS — 不支援建構與行號斷言：`tests/test_errors.py:46-72`、`tests/test_cudaq_errors.py:8-49`。
9. PASS — `qc` 優先、最後電路、缺失及語法錯誤：`tests/test_gate_mapping_extra.py:85-92`。
10. PASS — 五種 kernel 物件，含參數：`tests/test_kernel_object.py:12-30`。
11. PASS — widget 即時雙向轉換及執行按鈕：`tests/test_widgets.py:11-50`；但本輪新增的異常案例失敗。
12. PASS — 兩種 cell magic 與命名空間驗證：`tests/test_magics.py:10-30`。
13. PASS — notebook 無頭執行測試：`tests/test_notebook.py:9-27`。
14. PASS — 暫存路徑打包、解壓匯入及 Bell 轉換：`tests/test_build_dist.py:8-37`。

**新增並重現**五個 `xfail(strict=True)`：跨 qubit 中途測量、CLI `--check`、widget 按鈕、同 qubit 重複測量、reset 後測量（`tests/test_regressions.py:544-627`）。以 `--runxfail` 執行得 **5 failed**：前三項分別呈現 `IndexError: string index out of range`、CLI exit **1** 且印 traceback、widget callback 記錄 traceback；後兩項分別為 TVD **1.0**、預期 `{'01': 128}` 卻得到 CUDA-Q `{'00': 128}`。上輪參數簽章順序與使用者 kernel 重建的回歸測試仍通過：`tests/test_regressions.py:489-532`。

實際 CLI `--check` 與 `scripts/build_dist.py` 的 `tmp_path` 子程序測試通過（`tests/test_regressions.py:162-183`）；缺陷 CLI 案例則如上失敗。已執行 `ruff format tests`。

Gates 最終輸出摘要：pytest **293 passed, 5 xfailed**，覆蓋率 **92.44%**，**56.68s**；ruff check：`All checks passed!`；ruff format check：`26 files already formatted`；mypy：`Success: no issues found in 12 source files`。後三項未另計耗時。

VERDICT: FAIL
</task_result>
</task>
