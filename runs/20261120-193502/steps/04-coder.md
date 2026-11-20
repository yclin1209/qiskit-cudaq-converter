# Step 4: coder

start 19:50:16 end 19:57:54 duration 457.9s

## Prompt (from orchestrator)

你是 coder。專案 /workspace/qiskit-cudaq-converter。先讀 AGENTS.md、specs/SPEC.md、docs/plan.md（§4 批次 B），再看現有 src/qcconvert/（批次 A 已完成：IR、qiskit_io、cudaq_io 的 IR→CUDA-Q、api.qiskit_to_cudaq、compare 等）。文件與回覆用繁體中文（專有名詞附英文）。

任務：實作批次 B（CUDA-Q → Qiskit）：
- cudaq_io.py：CUDA-Q 原始碼 AST 靜態解析（不執行）→ IR，依 SPEC §3.4：單一或指定名稱 @cudaq.kernel；參數 float／list[float]（theta[i] 常數索引）；cudaq.qvector(N)／cudaq.qubit() 多暫存器依序串接；所有 §3.3 CUDA-Q 閘名、r1、u3、.ctrl（單一或 list 控制）、.adj、mz/mx/my（整個暫存器或單一 qubit）、reset；for i in range(常數) 展開、常數算術索引；參數運算式（2*theta、np.pi/2、math.pi）保留為運算式。不支援（測量結果 if、while、呼叫其他 kernel、exp_pauli、cudaq.control 等）→ UnsupportedFeatureError，訊息含建構名稱與行號。
- kernel 物件 → IR：cudaq.synthesize（有參數）→ cudaq.translate(format="openqasm2") → qiskit.qasm2.loads → IR；處理 r1→rz 全域相位（受控時才影響，必要時加 warning）。
- api.cudaq_to_qiskit(src, *, args=(), circuit_name="qc") 與 ConversionResult.to_qiskit()；多 QuantumRegister 名稱能還原時還原（SPEC §3.5）。
- 測試：SPEC §5 第 3 條（每個 CUDA-Q 閘名含 .ctrl、.adj 各一個原始碼→Qiskit 等價測試）、第 4 條（≥50 個隨機電路 round trip Qiskit→CUDA-Q→Qiskit 等價，固定 seed）、第 7 條（多暫存器反向）、第 8 條（CUDA-Q 端每類不支援建構，含行號）、第 10 條（kernel 物件→Qiskit ≥5 個，含 synthesize 有參數 kernel）。kernel 物件測試要用 load_kernel 從原始碼載入（exec 定義會失敗，環境事實 2）。
- 不確定的 cudaq API 行為請查 .venv 內 cudaq 原始碼或在測試中實測，不要猜。

規則：暫存檔只寫 pytest tmp_path；專案根目錄與 tests/ 不留 scratch/probe/debug 檔；不可改 specs/、AGENTS.md、harness/、.opencode/；不可 git commit/push。每次寫檔約 150 行以內。順便把 tests/test_batch_a.py 拆成有意義的檔名（test_parameters.py、test_measurements.py、test_qiskit_source.py、test_corpus.py 等）。
完成前跑四項 gates 直到全綠：
.venv/bin/python -m pytest -q ; .venv/bin/ruff check src tests scripts ; .venv/bin/ruff format --check src tests scripts ; .venv/bin/mypy src
回覆 15 行內：完成項目、實測 API 發現、gates 最後一行、覆蓋率、測試耗時。

## Output

<task id="ses_e0734fde7ffeWwGE1cIn7od9ka" state="completed">
<task_result>
已實作批次 B 的 CUDA-Q → Qiskit 反向轉換：AST 靜態解析（不執行輸入）、kernel 物件經 OpenQASM 2 轉換，以及 `cudaq_to_qiskit()`／`ConversionResult.to_qiskit()`。

變更檔案：`src/qcconvert/{cudaq_ast,cudaq_io,qiskit_io,api,__init__}.py`；新增 `tests/test_{cudaq_ast,cudaq_errors,kernel_object}.py`；將 `test_batch_a.py` 更名為 `test_gate_mapping_extra.py`，並加入 50 個固定 seed 的反向 round trip 測試。

實測 API：有參數 kernel 經 `cudaq.synthesize` 後可轉 OpenQASM 2；`r1` 翻譯為 `rz` 的相位風險會提出警告。

四項指令結果：`ruff format`：2 files reformatted；`ruff check --fix`：All checks passed；`mypy src`：Success，9 source files；`pytest -q`：**191 passed，覆蓋率 90.71%，27.60 秒**。另跑唯讀檢查：`ruff check` 全過、`ruff format --check` 顯示 16 files already formatted。

未解決：kernel 物件經 OpenQASM 2 翻譯後，受控 `r1` 的相對相位仍無法保證；目前僅警告，不能據此宣稱等價。
</task_result>
</task>
