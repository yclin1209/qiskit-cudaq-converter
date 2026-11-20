# Step 7: tester

start 20:08:07 end 20:21:09 duration 782.1s

## Prompt (from orchestrator)

你是 tester。專案 /workspace/qiskit-cudaq-converter。讀 AGENTS.md、specs/SPEC.md、docs/plan.md，獨立跑 gates、補邊界測試、把問題重現成失敗的測試。回覆用繁體中文（專有名詞附英文）。

1. 獨立執行四項 gates，記錄每項實際最後一行與覆蓋率、耗時：
   .venv/bin/python -m pytest -q ; .venv/bin/ruff check src tests scripts ; .venv/bin/ruff format --check src tests scripts ; .venv/bin/mypy src
2. 以 SPEC §5 凍結 14 條逐條標 PASS／FAIL 並附依據（檔案:行號）；範圍外要求只列「建議」。
3. 以下為 reviewer 的發現（出處：reviewer 第 1 輪），請另外獨立檢查、能重現就寫成失敗測試（放 tests/test_regressions.py，可用 pytest.mark.xfail(strict=True) 標註以免讓 gates 變紅；或直接寫失敗測試並在回覆說明）：
   - src/qcconvert/runner.py:73-76 — 非遞增測量順序（x(2); measure(2,0); measure(0,1)）counts 映射錯誤，tvd=1.0。
   - src/qcconvert/runner.py:39 — compare(args=…) 帶 ParameterVector 值 TypeError；參數順序與 kernel 簽名不一致。
   - src/qcconvert/cudaq_io.py:26 — Parameter("rx") 等與 CUDA-Q 閘名衝突，產生的 kernel 編譯失敗。
   - 第 6 條缺 GHZ 分佈等價測試；第 3 條 .ctrl 只測 x/s/r1/u3、reset 無反向測試、sdg/tdg 被拒。
4. 自行再找其他邊界問題（例如多 creg、部分測量、無測量、中途測量報告標記、mx/my、多暫存器還原、CLI exit code、load_kernel 重複載入不洩漏暫存檔）。
規則：暫存檔只寫 tmp_path；專案根與 tests/ 不留 scratch/probe/debug 檔；只能新增測試檔，不修改 src/。
回覆 40 行內：gates 結果、14 條 PASS/FAIL、確認重現的問題（檔案:行號 — 一句描述，以及對應測試名稱）、新發現問題。最後一行必須是 `VERDICT: PASS` 或 `VERDICT: FAIL`。

## Output

<task id="ses_e0724a5b8ffe5xiuwgVzVmnyK3" state="completed">
<task_result>
**四項品質關卡（gates，補測後實際執行）**
- `pytest -q`：206 passed、4 xfailed、2 warnings；覆蓋率（coverage）91.60%；44.48 秒。四個預期失敗（xfail）是已重現、尚未修復的問題。
- `ruff check src tests scripts`：`All checks passed!`
- `ruff format --check src tests scripts`：`26 files already formatted`；已先執行 `ruff format tests`。
- `mypy src`：`Success: no issues found in 12 source files`

**SPEC §5 逐條判定**
1. PASS — 四項 gates 全過，覆蓋率與耗時達標（本次輸出）。
2. PASS — 逐閘與受控等價測試：`tests/test_gate_mapping.py:30`。
3. FAIL — `.ctrl` 反向測試只涵蓋四種閘；`mx/my` 僅檢查結構、未驗等價：`tests/test_cudaq_ast.py:37,94`。
4. PASS — 固定 seed 的 200 個電路、前 50 個往返：`tests/test_gate_mapping_extra.py:131`。
5. FAIL — 三組參數數值測試存在，但 `compare` 的 `ParameterVector` 帶值失敗：`tests/test_gate_mapping_extra.py:102`、`tests/test_regressions.py:26`。
6. FAIL — 新增 GHZ 分佈測試，但非遞增及多 creg 部分測量映射仍錯：`tests/test_regressions.py:59,14,105`。
7. PASS — 前向暫存器及反向名稱檢查：`tests/test_gate_mapping_extra.py:166`、`tests/test_regressions.py:89`。
8. FAIL — 已列不支援類別有測試，但 CUDA-Q 非法參數類別未逐類覆蓋：`tests/test_errors.py:46`、`tests/test_cudaq_errors.py:8`。
9. PASS — 四種原始碼選取／錯誤情況：`tests/test_gate_mapping_extra.py:85`。
10. PASS — 五種 kernel 物件案例，含參數：`tests/test_kernel_object.py:12`。
11. PASS — 雙向、錯誤、切換與按鈕：`tests/test_widgets.py:8,23`。
12. PASS — 兩種 cell magic：`tests/test_magics.py:10`。
13. PASS — notebook 無頭執行測試隨全套通過：`tests/test_notebook.py:9`。
14. PASS — `tmp_path` 打包、解壓匯入測試隨全套通過：`tests/test_build_dist.py:8`。

**新增與重現**：`tests/test_regressions.py` 新增 13 個案例；實際 CLI `--check` 成功回傳 0、錯誤輸入回傳 2，`scripts/build_dist.py` 在 `tmp_path` 產生 zip（`:134`）。重複載入未增加 `.py` 檔（`:124`）；1 qubit、未測量、GHZ、反向 reset／adjoint 均通過。  
- `src/qcconvert/runner.py:73-76` — 非遞增測量 counts 錯位：`test_measurement_out_of_order`（xfail）。
- `src/qcconvert/runner.py:39` — `ParameterVector` 帶值比較失敗：`test_compare_parameter_vector_args`（xfail）。
- `src/qcconvert/cudaq_io.py:26` — 參數名 `rx` 與閘衝突；`q`、`cudaq` 通過：`test_parameter_identifier_conflict`（rx xfail）。
- **獨立新發現**：`src/qcconvert/runner.py:73-76` — 多 creg 的部分測量由預期 `{'100': 128}` 錯映為 `{'010': 128}`：`test_partial_multiple_cregs_distribution`（xfail）。

建議（範圍外）：零 qubit 目前產生 `cudaq.qvector(0)`；僅記錄於 `tests/test_regressions.py:116`，未宣稱可執行等價比較。

VERDICT: FAIL
</task_result>
</task>
