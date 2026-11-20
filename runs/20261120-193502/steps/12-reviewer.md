# Step 12: reviewer

start 21:44:08 end 22:04:27 duration 1219.4s

## Prompt (from orchestrator)

你是 reviewer（唯讀）。專案 /workspace/qiskit-cudaq-converter。讀 AGENTS.md、specs/SPEC.md、docs/plan.md，審查 src/qcconvert/、tests/、scripts/build_dist.py、colab/、README.md。回覆用繁體中文（專有名詞附英文）。

第 3 輪。coder 宣稱已修正第 2 輪阻擋問題，請逐一驗證：
- src/qcconvert/qiskit_io.py:299 — 反向產生的 Qiskit 原始碼可執行（受控閘、u3→u、mx/my、參數運算式、暫存器與 Parameter/ParameterVector 宣告），exec 後與 to_qiskit() 等價；CLI --to qiskit、%%cudaq2qiskit 輸出亦然。
- src/qcconvert/cudaq_ast.py:10、README.md:9 — sdg/tdg 與別名支援、.ctrl/.adj、測試。
- src/qcconvert/widgets.py:61 — 方向來回切換後狀態成功、輸出等價（tests/test_widgets.py）。
並全面複查其他條款，可用 .venv/bin/python -c 實驗（不寫檔）。
- 驗收以 SPEC §5 凍結 14 條為準，逐條 PASS／FAIL 附依據（檔案:行號）。範圍外只列「建議」，不可作為 FAIL 理由。
- 可執行四項 gates：.venv/bin/python -m pytest -q ; .venv/bin/ruff check src tests scripts ; .venv/bin/ruff format --check src tests scripts ; .venv/bin/mypy src
回覆 40 行內；FAIL 問題以「檔案:行號 — 一句描述」列出。最後一行必須是 `VERDICT: PASS` 或 `VERDICT: FAIL`。

## Output

<task id="ses_e06ccbe38ffeKMQFfLQa1KVMQd" state="completed">
<task_result>
第 3 輪審查完成：第 2 輪的三個阻擋問題都已修正，14 條驗收全部 PASS。

**四項 gates（實際執行）**：pytest 267 passed，用時 71.96s，覆蓋率 92.06%（門檻 90%）。`ruff check` 回報 All checks passed；`ruff format --check` 回報 26 files already formatted；`mypy src` 回報 no issues（12 個檔案）。

**第 2 輪阻擋問題的驗證**
- `qiskit_io.py:299`：已修正。我用 `-c` 做了一個綜合實驗：一個 kernel 同時放進 `ParameterVector`、運算式、多暫存器、`u3.ctrl`、`u3.adj`、`swap.ctrl`、`x.ctrl([..])`、迴圈、`s.adj`/`t.adj`、`sdg`/`tdg` 和別名。產生的原始碼 exec 後與 `to_qiskit()` 在 3 組參數值下 `Operator.equiv` 都是 True，與 `cudaq.get_state` 的 fidelity 都 ≥ 1-3e-15。`mx`/`my`/`mz` 另有測試覆蓋（`tests/test_cudaq_ast.py:111`、`test_regressions.py:201`）。CLI `--to qiskit` 與 `%%cudaq2qiskit` 的輸出可執行，有測試鎖住（`test_regressions.py:291`、`:309`）。
- `cudaq_ast.py:10`／`README.md:9`：已修正。我實測 cudaq 0.17 對 `sdg.ctrl`、`tdg.ctrl`、`sdg.adj` 確實無法編譯，AST 會給出含行號的拒絕訊息，有測試（`test_cudaq_ast.py:154`）。別名 `cx`…`cr1` 也有測試（`test_cudaq_ast.py:164`）。
- `widgets.py:61`：已修正。方向來回切換兩次後狀態都是「成功」，且輸出用 Statevector 驗證等價（`tests/test_widgets.py:18-28`、`test_regressions.py:279`）。

**額外實驗（只用 `-c`，沒有寫檔）**
- 35 種閘（含 `cu`、`u2`、`r`、`rxx`/`ryy`/`rzz`、`cswap`）分別在 0、1、2 個控制位元下轉換，與 `cudaq.get_state` 比較：沒有任何一項 fidelity 低於 1-1e-6。
- 參數名稱清理：`q`、`lambda` 會被改成 `param_q`、`param_lambda`，Unicode 的 `θ` 保留。3 組數值帶入後 fidelity 都約為 1。
- kernel 物件路徑：經 `synthesize` 加 OpenQASM 2，含 `r1.ctrl`、`u3.ctrl` 時 fidelity 約為 1，反向產生的原始碼可以 exec。

**SPEC §5 驗收條件**
1. PASS：四項 gates 全綠，覆蓋率 92.06%，`pyproject.toml` addopts 已設 `--cov-fail-under=90`。
2. PASS：每個閘都有一般版和受控版（控制位元在 |+>）的測試（`tests/test_gate_mapping.py:30-53`）。
3. PASS：一般閘、`.ctrl`、`.adj`、別名、`mz`/`mx`/`my`、`reset` 都有測試（`tests/test_cudaq_ast.py:11-179`）。
4. PASS：固定 seed 跑 200 個電路，其中 50 個做來回轉換（round trip）（`tests/test_gate_mapping_extra.py:131-163`）。
5. PASS：`Parameter`、`ParameterVector`、運算式各有測試，每項用 3 組數值（`test_gate_mapping_extra.py:102`、`test_regressions.py:212`、`:223`）。
6. PASS：位元順序有 `'001'` 測試（`test_gate_mapping_extra.py:124`）；GHZ、部分測量、多 creg 都有測試（`test_regressions.py:81`、`:128`）。
7. PASS：多暫存器兩個方向都有測試（`test_gate_mapping_extra.py:166`、`test_regressions.py:112`、`:259`）。
8. PASS：Qiskit 端各類不支援建構有測試（`tests/test_errors.py:46-72`）；CUDA-Q 端的拒絕訊息含行號（`tests/test_cudaq_errors.py:8-49`）。
9. PASS：`qc` 優先、取最後一個電路、找不到電路、語法錯誤含行號四種情況都有測試（`test_gate_mapping_extra.py:85-92`）。
10. PASS：kernel 物件路徑有 5 個參數化測試加 1 個警告測試，其中含 `synthesize`（`tests/test_kernel_object.py:12-47`）。
11. PASS：即時轉換、錯誤顯示、方向切換、執行按鈕（`qpp-cpu`）都有測試（`tests/test_widgets.py:11-50`）。
12. PASS：兩個 cell magic 都放進命名空間且結果等價（`tests/test_magics.py:10-30`）。
13. PASS：notebook 以 nbclient 執行、逾時 600 秒、跳過安裝 cell（`tests/test_notebook.py:9-27`）；cell 結構符合 §6。
14. PASS：zip 在 `tmp_path` 建立，內容與排除項目都有檢查，解壓後能 import 並轉換 Bell 電路（`tests/test_build_dist.py:8-37`）。

**阻擋問題（blocking）**：沒有。

**建議（non-blocking）**
1. `qiskit_io.py:307-328`：反向產生的原始碼沒有避開名稱衝突。kernel 參數若叫 `qc` 或 `_base` 會覆蓋電路變數，我實測會出現 CircuitError。建議比照 `cudaq_io._identifier` 清理名稱，或改用帶前綴的暫時變數名。
2. `test_gate_mapping_extra.py:142`：隨機語料只從 8 種閘抽樣，而且沒有使用符號參數 `Parameter`。建議把整個支援閘集合和 `Parameter` 都納入抽樣。
3. `widgets.py:83-106`：執行按鈕只在 Qiskit → CUDA-Q 方向有測試，建議補上 CUDA-Q → Qiskit 方向的執行測試。

VERDICT: PASS
</task_result>
</task>
