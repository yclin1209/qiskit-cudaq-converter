# Step 6: reviewer

start 20:03:48 end 20:07:57 duration 249.2s

## Prompt (from orchestrator)

你是 reviewer（唯讀）。專案 /workspace/qiskit-cudaq-converter。讀 AGENTS.md、specs/SPEC.md、docs/plan.md，審查 src/qcconvert/、tests/、scripts/build_dist.py、colab/、README.md 的正確性與規格符合度。回覆用繁體中文（專有名詞附英文）。

要求：
- 驗收以 SPEC §5 凍結 14 條為準，逐條標示 PASS／FAIL，每條附依據（檔案:行號）。範圍外的新要求只能列為「建議」，不可作為 FAIL 理由。
- 重點檢查：受控閘相對相位（sx/sxdg、p/u1、u/u3、r）、位元順序（環境事實 3，sample 鍵 qubit 0 在左）、多 creg／部分測量 counts 映射、參數名清理、load_kernel 雜湊快取、AST 子集與不支援建構訊息含行號、kernel 物件經 OpenQASM 2、§5 第 2/3 條是否「每個」閘都有測試、第 4 條數量（≥200、≥50 round trip）、測試斷言是否有意義、專案根與 tests/ 是否留下暫存／探測檔、dist/ 是否被留在專案內。
- 可以執行四項 gates 以確認（唯讀不改檔）：
  .venv/bin/python -m pytest -q ; .venv/bin/ruff check src tests scripts ; .venv/bin/ruff format --check src tests scripts ; .venv/bin/mypy src
- 回覆精簡（40 行內）：14 條逐條 PASS/FAIL；FAIL 問題以「檔案:行號 — 一句描述」列出；建議另列。最後一行必須是 `VERDICT: PASS` 或 `VERDICT: FAIL`。

## Output

<task id="ses_e07289906ffeTkR92C3qncyPFt" state="completed">
<task_result>
## 審查結果（四項 gates 已實際執行）

四項 gates 全部通過：pytest 197 passed（31.9 秒），覆蓋率 91.31%；ruff check 通過；format --check 顯示 25 files already formatted；mypy 沒有問題。專案根目錄沒有暫存檔，`dist/` 也不在專案內。

但我用 `.venv/bin/python -c` 實驗，找到 3 個測試沒抓到的缺陷，另外第 3、6 條驗收也不符合。

### SPEC §5 驗收條件
1. PASS — 四項 gates 全過，覆蓋率 91.31% ≥ 90%。
2. PASS — `tests/test_gate_mapping.py:12-53` 涵蓋 §3.3 全部閘，每個都有普通版與受控版（控制位元先做 `h`，處於 |+>）。
3. FAIL — `.ctrl` 只測了 x/s/r1/u3（`tests/test_cudaq_ast.py:37-38`）；`reset` 沒有反向測試；`sdg`/`tdg`/`cx`/`ch` 等 CUDA-Q 本身可用的名稱一律被拒（`src/qcconvert/cudaq_ast.py:10-27`，實測報「不支援 sdg」）。
4. PASS（但抽樣範圍偏窄）— `tests/test_gate_mapping_extra.py:131-163`：200 個電路、前 50 個做 round trip、固定 seed；但閘只抽 8 種，角度是浮點數，不是 `Parameter`。
5. PASS — `test_gate_mapping_extra.py:102-121`、`test_cudaq_ast.py:52-77`。不過只直接呼叫 `get_state`，沒經過 `compare(args=…)`，所以沒發現下面阻擋問題 2。
6. FAIL — `tests/` 完全沒有 GHZ 分佈等價測試（grep 無結果）。部分測量／多 creg 只測了「qubit 依序遞增測量」的情況（`test_gate_mapping_extra.py:166-184`），所以沒抓到阻擋問題 1。
7. PASS — 正向見 `test_gate_mapping_extra.py:166-183`，反向見 `test_cudaq_ast.py:52-77`。
8. PASS — `tests/test_errors.py:46-72`；`tests/test_cudaq_errors.py:8-26` 有斷言「第 5 行」。
9. PASS — `test_gate_mapping_extra.py:85-92`。
10. PASS — `tests/test_kernel_object.py:12-30`：5 個測試，其中包含有參數的 kernel（`rx`/`synthesize`）。
11. PASS — `tests/test_widgets.py:8-38`。
12. PASS（偏弱）— `tests/test_magics.py:10-29`：kernel 端只檢查轉回後是 `QuantumCircuit`，沒做等價比較。
13. PASS — `tests/test_notebook.py` 有在 gates 內跑過並通過。
14. PASS — `tests/test_build_dist.py:8-37`：在 `tmp_path` 打包、檢查 zip 內容，解壓後能匯入並轉換 Bell 電路。

### 阻擋問題（blocking）
1. `src/qcconvert/runner.py:73-76` — counts 映射錯誤：`sample_mapping` 依「測量順序」取 `key[index]`，但 CUDA-Q 的 bitstring 依 qubit 索引排列。
   - 實測 `x(2); measure(2,0); measure(0,1)`：Qiskit 是 `{'01'}`，CUDA-Q 卻是 `{'10'}`，`tvd=1.0`，同時 `statevector_equal=True`。
   - 修法：把測量的 qubit 依索引排序後，再對應 bitstring 位置；並補上非遞增測量順序的測試。
2. `src/qcconvert/runner.py:39` — `compare(args=…)` 帶 `ParameterVector` 的值時會 TypeError（實測 `args=(0.3,[0.1,0.2])`）。
   - 另外參數順序依 `p.name` 排序，但 kernel 簽名是「純量在前、list 在後」（`cudaq_io.py:43`），兩邊順序會錯位。
   - 修法：統一 kernel 簽名與 `assign_parameters` 的參數順序，並展開 vector 參數。
3. `src/qcconvert/cudaq_io.py:26` — 參數名清理沒有避開 CUDA-Q 閘名（`rx`、`x`、`h`…）。實測 `Parameter("rx")` 產生的 kernel 編譯失敗。
   - 修法：保留字集合加入所有 CUDA-Q 閘／測量名稱，例如 `cudaq_ast.GATES`。
4. `tests/test_gate_mapping_extra.py` — 缺 GHZ 分佈等價測試（第 6 條）。
5. `tests/test_cudaq_ast.py:37-38` — 補上其餘閘的 `.ctrl` 測試和 `reset` 反向測試；同時讓 `cudaq_ast.py:10` 支援 `sdg`/`tdg`，或在文件中明列為不支援（第 3 條）。

### 建議（non-blocking）
- 隨機語料加入 `Parameter` 物件，並擴大抽樣的閘集合（u、r、sxdg、ccx、受控閘等）。
- `test_magics.py:23` 對 kernel 也做 `compare` 等價斷言。
- `cudaq_io.py:160-161` 的 r1→rz 警告只看 qasm 裡有沒有 `rz(`，判斷太粗；可以改成只在受控的 rz 時才警告。
- `cudaq_io.py:114` 的 `u` 四參數分支（`cu`）依賴 `ctrl[-1]`，建議補一條專門測試。

VERDICT: FAIL
</task_result>
</task>
