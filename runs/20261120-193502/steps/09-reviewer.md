# Step 9: reviewer

start 20:26:05 end 20:47:50 duration 1304.8s

## Prompt (from orchestrator)

你是 reviewer（唯讀）。專案 /workspace/qiskit-cudaq-converter。讀 AGENTS.md、specs/SPEC.md、docs/plan.md，審查 src/qcconvert/、tests/、scripts/build_dist.py、colab/、README.md。回覆用繁體中文（專有名詞附英文）。

這是第 2 輪。第 1 輪的阻擋問題已由 coder 宣稱修正，請逐一驗證：
- runner.py counts 映射（非遞增測量、多 creg 部分測量）；compare(args=…) 帶 ParameterVector；參數名避開 CUDA-Q 閘名；§5 第 3 條每個 CUDA-Q 閘名（含 .ctrl、.adj、mz/mx/my、reset）都有原始碼→Qiskit 等價測試；README 宣稱 cudaq 0.17 無 sdg/tdg（請查 .venv 內 cudaq 原始碼核實）；§5 第 6 條 GHZ／部分測量／多 creg；§5 第 8 條 CUDA-Q 端各類不支援建構含行號。
同時全面複查其餘條款與受控相位正確性，可用 .venv/bin/python -c 實驗（不寫檔）。
- 驗收以 SPEC §5 凍結 14 條為準，逐條 PASS／FAIL 附依據（檔案:行號）。範圍外只列「建議」，不可作為 FAIL 理由。
- 可執行四項 gates：.venv/bin/python -m pytest -q ; .venv/bin/ruff check src tests scripts ; .venv/bin/ruff format --check src tests scripts ; .venv/bin/mypy src
回覆 40 行內；FAIL 問題以「檔案:行號 — 一句描述」列出。最後一行必須是 `VERDICT: PASS` 或 `VERDICT: FAIL`。

## Output

<task id="ses_e07143318ffedG3RY6jeTQ0oqM" state="completed">
<task_result>
**第 2 輪審查結果**

四項品質關卡（gates）都實際跑過：pytest 237 passed，53.1 秒，覆蓋率（coverage）91.93%；`ruff check` 回報 All checks passed；`ruff format --check` 回報 26 files already formatted；`mypy` 回報 Success。根目錄只有允許的檔案和目錄。

**第 1 輪阻擋問題的驗證**
- counts 映射：已修好。非遞增測量和多 creg 部分測量，兩邊 counts 都一致（`tests/test_regressions.py:14,127`）。我另外用 `-c` 實驗：3q／2 creg 的 TVD 為 0.0087，`measure(2,0);(0,2);(1,1)` 兩邊都是 `{'001':4000}`。
- `compare(args=…)` 帶 ParameterVector：已修好。參數順序是純量在前、list 在後，fidelity 為 1.0（`runner.py:39-56`）。
- 參數名避開 CUDA-Q 閘名：已修好。名稱會加上 `param_` 前綴（`cudaq_io.py:20-75`，`test_regressions.py:69`）。
- README 說 cudaq 0.17 沒有 `sdg`／`tdg`：**不實**。`.venv` 內的 `cudaq/kernel/kernel_builder.py` 有定義 `sdg`／`tdg`。我直接在 `@cudaq.kernel` 寫 `sdg(q[0])`、`tdg(q[1])`、`cx(...)`，`get_state` 都正常算出結果；但 qcconvert 對同樣的原始碼會丟「第 5 行：不支援 sdg」。
- 受控相位：sx、sxdg、u、u2、p、r、rzz、rxx、ryy、sdg、tdg、h、swap、u1、rz、y、cu 都測了。控制位元處於 |+>，1 個和 2 個控制位元都試過，fidelity 全部為 1.0。

**SPEC §5 驗收條件**
1. PASS — gates 全綠，覆蓋率 91.93%。
2. PASS — `tests/test_gate_mapping.py:13-53`，每個閘有一般版和受控版（控制位元 |+>）；我的實驗也確認了。
3. FAIL — `sdg`／`tdg` 是 CUDA-Q 0.17 實際可用的閘名，卻被拒絕（`src/qcconvert/cudaq_ast.py:10-27`），也沒有測試。其餘閘名、`.ctrl`、`.adj`、mz／mx／my、reset 都有測試（`tests/test_cudaq_ast.py:11-149`）。
4. PASS — `tests/test_gate_mapping_extra.py:131-163`：200 個電路，其中 50 個做 round trip，seed 4831。
5. PASS — `test_gate_mapping_extra.py:102-121` 有 3 組數值；`test_regressions.py:24-44` 有 ParameterVector 和運算式。
6. PASS — GHZ 在 `test_regressions.py:80`，部分測量／多 creg 在 `:127`，位元順序在 `test_gate_mapping_extra.py:124`。
7. PASS — `test_gate_mapping_extra.py:166-184`、`test_regressions.py:111`。
8. PASS — CUDA-Q 端的 if、while、其他 kernel、exp_pauli、cudaq.control、非常數索引／range、參數型別都有測試，且斷言行號（`tests/test_cudaq_errors.py:8-49`）。
9. PASS — Qiskit 原始碼輸入的四種情況都有測試（依測試檔確認）。
10. PASS — `tests/test_kernel_object.py`（依測試檔確認）。
11. FAIL — 方向切換是壞的。實測流程：Bell → 切到 CUDA-Q→Qiskit → 再切回 Qiskit→CUDA-Q，狀態列顯示「錯誤：第 4 行：'int' object is not an instance of 'str'」。原因是產生的 Qiskit 原始碼無效；`tests/test_widgets.py:15-17` 只檢查有沒有出現字串 "QuantumCircuit"。
12. PASS — 斷言命名空間內有 kernel／`QuantumCircuit` 並做等價比較；但 `%%cudaq2qiskit` 印出的 Qiskit 程式碼也受阻擋問題 1 影響。
13. PASS — `tests/test_notebook.py` 用 nbclient 無頭執行，測試通過。
14. PASS — `tests/test_build_dist.py`：在 tmp_path 檢查 zip 內容，解壓後能 import 並轉換 Bell。

**阻擋問題（blocking）**
1. `src/qcconvert/qiskit_io.py:299-310` — `to_source` 產生的 Qiskit 原始碼不能執行。受控閘會寫成 `qc.x(0, 1)`，還會出現 `qc.u3(...)`、`qc.mx(2, 0)`，參數變成字串 `qc.rx('2 * theta', 0)`；暫存器名稱和 `Parameter`／`ParameterVector` 宣告都沒有產生。我直接 `exec` 輸出會丟 TypeError，影響 CLI `--to qiskit`、widget 和 magic。修法：受控閘改寫成 `.control(n)` 加 `append`（或 cx／ccx／mcx），`u3` 改 `u`，mx／my 展開成 h／sdg 再 measure，並輸出 `QuantumRegister`／`ClassicalRegister`／`Parameter` 宣告。另外要加測試：exec `result.code` 後和 `to_qiskit()` 比較等價。
2. `src/qcconvert/cudaq_ast.py:10-27` 與 `README.md:9` — CUDA-Q 0.17 有 `sdg`／`tdg`，README 說沒有是錯的，解析器也拒收。修法：把 `sdg`／`tdg` 加進 GATES（也支援 `.ctrl`／`.adj`），在 `tests/test_cudaq_ast.py` 補上原始碼→Qiskit 和受控的等價測試，並更正 README。
3. `tests/test_widgets.py:15-17` — 方向切換的測試沒有把輸出再轉一次。修法：切回 Qiskit→CUDA-Q 後，斷言狀態列是「成功」，而且輸出的 kernel 和原電路等價。

**建議（non-blocking）**
- 隨機語料只抽 8 種閘，角度都是浮點數；可以加入 `Parameter`、u、r、ccx 和受控閘。
- `widgets.py` 覆蓋率 79%，debounce Timer 和錯誤分支沒有被測到。
- `cudaq_ast.py:178` 的 `u3.adj` 參數換位邏輯已有測試，可以再補一個受控的 `u3.adj`。

VERDICT: FAIL
</task_result>
</task>
