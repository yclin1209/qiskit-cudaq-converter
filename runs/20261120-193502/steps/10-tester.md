# Step 10: tester

start 20:47:59 end 21:13:53 duration 1554.4s

## Prompt (from orchestrator)

你是 tester。專案 /workspace/qiskit-cudaq-converter。讀 AGENTS.md、specs/SPEC.md、docs/plan.md，獨立跑 gates、補邊界測試、把問題重現成失敗測試。回覆用繁體中文（專有名詞附英文）。

1. 獨立執行四項 gates，記錄最後一行、覆蓋率、耗時：
   .venv/bin/python -m pytest -q ; .venv/bin/ruff check src tests scripts ; .venv/bin/ruff format --check src tests scripts ; .venv/bin/mypy src
2. SPEC §5 凍結 14 條逐條 PASS／FAIL 附依據（檔案:行號）；範圍外只列「建議」。
3. reviewer 第 2 輪發現（出處：reviewer），請獨立檢查，能重現就寫成 pytest.mark.xfail(strict=True) 測試放 tests/test_regressions.py：
   - src/qcconvert/qiskit_io.py:299-310 — IR→Qiskit 原始碼（to_source）不能執行：受控閘寫成 qc.x(0, 1)、出現 qc.u3／qc.mx、參數變成字串 '2 * theta'、缺 Register／Parameter 宣告。測法：cudaq_to_qiskit(...) 的 result.code 在新命名空間 exec 後取 qc，與 to_qiskit() 等價。
   - src/qcconvert/cudaq_ast.py:10-27、README.md:9 — cudaq 0.17 有 sdg/tdg（見 .venv 內 cudaq/kernel/kernel_builder.py 等），解析器卻拒收。
   - tests/test_widgets.py:15-17 — 方向切換來回後狀態列顯示錯誤（Bell → CUDA-Q→Qiskit → 再切回）。
4. 另外獨立找邊界問題（CLI --to qiskit 輸出是否可執行、magic %%cudaq2qiskit 印出的程式碼、多暫存器名稱還原後原始碼）。
規則：暫存檔只寫 tmp_path；專案根與 tests/ 不留 scratch/probe/debug 檔；只新增／修改測試，不改 src/。gates 結束時要維持全綠（xfail 可）。
回覆 40 行內；最後一行必須是 `VERDICT: PASS` 或 `VERDICT: FAIL`。

## Output

<task id="ses_e0700264fffelHtpGlKWMG75yF" state="completed">
<task_result>
**SPEC §5 驗收（1～14）**

1. PASS — 四項 gates 全過，行覆蓋率 91.93%。
2. PASS — 支援閘及受控閘等價測試：`tests/test_gate_mapping.py:12-53`。
3. **FAIL** — CUDA-Q `sdg`、`tdg` 原始碼遭 AST 解析器拒絕：`tests/test_regressions.py:237-245`。
4. PASS — 固定 seed 的 200 個電路、其中 50 個往返轉換：`tests/test_gate_mapping_extra.py:131-163`。
5. PASS — 參數、向量及運算式三組數值：`tests/test_gate_mapping_extra.py:102-121`。
6. PASS — 位元順序、GHZ、部分測量及多古典暫存器：`tests/test_gate_mapping_extra.py:124-128`、`tests/test_regressions.py:80-89,127-143`。
7. PASS — 多量子暫存器雙向轉換：`tests/test_gate_mapping_extra.py:166-183`、`tests/test_regressions.py:111-124`。
8. PASS — 不支援建構與行號斷言：`tests/test_errors.py:46-72`、`tests/test_cudaq_errors.py:8-49`。
9. PASS — Qiskit 原始碼四種選取／錯誤情況：`tests/test_gate_mapping_extra.py:85-92`。
10. PASS — 五個 kernel 物件案例，含參數：`tests/test_kernel_object.py:12-30`。
11. **FAIL** — 編輯器（widget）切換方向來回後狀態顯示錯誤：`tests/test_regressions.py:248-258`。
12. PASS — 兩種 cell magic 的命名空間與等價測試：`tests/test_magics.py:10-30`。
13. PASS — notebook 無頭執行：`tests/test_notebook.py:9-27`。
14. PASS — 暫存路徑打包、解壓匯入與 Bell 轉換：`tests/test_build_dist.py:8-37`。

**新增測試與問題：** `tests/test_regressions.py:186-324` 新增 10 個嚴格預期失敗（`xfail(strict=True)`）案例，以及固定 seed、深度 80 的隨機電路和 0 qubit IR 檢查。獨立重現反向 CLI 與 magic 印出的程式碼不可執行；多暫存器名稱亦無法由產生的原始碼還原。強制執行部分預期失敗案例時，實際錯誤包括 `QuantumCircuit has no attribute 'u3'`、`has no attribute 'mx'`、`Invalid param type <class 'str'> for gate rx`，以及 `第 6 行：不支援 sdg/tdg`。CLI `--check` 與打包腳本的實際子程序檢查見 `tests/test_regressions.py:161-183`。反向原始碼可執行性屬本次另列的問題，不改動凍結驗收條件。

**最終 gates：** pytest：239 passed、10 xfailed、2 warnings，91.93%，51.75 秒；ruff check：`All checks passed!`；ruff format check：`26 files already formatted`；mypy：`Success: no issues found in 12 source files`。已執行 `ruff format tests`；僅修改 `tests/`。

VERDICT: FAIL
</task_result>
</task>
