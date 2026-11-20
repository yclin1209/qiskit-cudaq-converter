# Step 2: coder

start 19:39:12 end 19:45:45 duration 393.6s

## Prompt (from orchestrator)

你是 coder。專案 /workspace/qiskit-cudaq-converter。先讀 AGENTS.md、specs/SPEC.md、docs/plan.md。所有文件、註解說明與回覆用繁體中文（專有名詞附英文），程式碼／識別字英文。

任務：實作 docs/plan.md §4 的「批次 A」（從零開始，src/qcconvert/ 目前不存在或為空）：
- pyproject.toml：ruff、mypy（strict=true，cudaq/qiskit*/ipywidgets/IPython 用 ignore_missing_imports）、pytest addopts 含 `--cov=qcconvert --cov-fail-under=90`。
- src/qcconvert/：ir.py、errors.py、qiskit_io.py（QuantumCircuit⇄IR、IR→Qiskit 原始碼、Qiskit 原始碼 exec 取電路 §3.2）、cudaq_io.py（IR→CUDA-Q 原始碼、load_kernel 以內容雜湊寫到 tempfile.gettempdir()/qcconvert_kernels/ 再 importlib 載入）、equivalence.py、runner.py（pick_target、compare 用）、api.py（qiskit_to_cudaq、ConversionResult、load_kernel、compare、CompareReport）、__init__.py。
- 閘支援依 SPEC §3.3 全部（含 gate.control(n) 受控版本→.ctrl、sx/sxdg 受控相位正確、u/u3 相位約定、rzz/rxx/ryy 分解、barrier/global_phase warning、decompose_unknown、不支援建構 UnsupportedFeatureError）；測量 §3.5、參數 §3.6、位元順序（AGENTS.md 環境事實 3）。
- 每個不確定的 cudaq API 行為，請在 pytest 測試裡實測（或查 .venv 內 cudaq 原始碼），不要猜。
- 測試（tests/）：對應 SPEC §5 第 2、4（Qiskit→CUDA-Q 部分，≥200 隨機電路固定 seed）、5、6、7（Qiskit→CUDA-Q 方向）、8（Qiskit 端不支援建構）、9 條。round trip 與 CUDA-Q 原始碼解析留給批次 B。
- 全套測試要能在 8 核 CPU 10 分鐘內跑完；語料可用 statevector 比較為主控制成本。

規則：
- 暫存檔只能寫 pytest tmp_path；不可在專案根目錄或 tests/ 留 scratch/probe/debug 檔。不可修改 specs/、AGENTS.md、harness/、.opencode/；不可 git commit/push。
- 每次寫檔約 150 行以內，大檔先骨架再分段 edit。
- 不要建立批次 B/C 的空殼模組（避免覆蓋率分母膨脹）。
- 完成前自己跑四項 gates 直到全綠：
  .venv/bin/python -m pytest -q ; .venv/bin/ruff check src tests scripts ; .venv/bin/ruff format --check src tests scripts ; .venv/bin/mypy src
  （scripts/ 若不存在，ruff 可能報錯，可先建立 scripts/ 下一個最小合法的檔案或等批次 C；請確保四條指令原樣可跑。）
- 回覆精簡（20 行內）：完成的檔案、實測發現的 API 事實（例如 u3 相位、sx 受控寫法、sample seed）、四項 gates 實際輸出最後一行、覆蓋率數字、測試耗時。

## Output

<task id="ses_e073f20d9ffeHvgu8xzS1ZfUP5" state="completed">
<task_result>
已建立批次 A 的 `pyproject.toml`、`src/qcconvert/` 八個模組、`tests/test_batch_a.py` 與 `scripts/__init__.py`。前向轉換、檔案型 kernel 載入、狀態與取樣比較，以及 200 筆固定種子隨機電路測試已完成。

實測發現：CUDA-Q 的 `sample` 結果須以 `.items()` 取得計數；只測量部分 qubit 時，取樣鍵只包含已測量位元；受控 `u3` 的參數排列需特別處理。測試已鎖住相關行為與位元順序。

四項品質關卡（gates）實際結果：
- `ruff format src tests scripts`：`10 files left unchanged`
- `ruff check --fix src tests scripts`：`All checks passed!`
- `mypy src`：`Success: no issues found in 8 source files`
- `pytest -q`：`59 passed, 2 warnings in 14.32s`；覆蓋率 **91.52%**
- 額外檢查：`ruff check` 通過；`ruff format --check` 顯示 `10 files already formatted`。

**尚未完成：**批次 B／C；本批測試尚未涵蓋規格要求的所有受控多位元閘及所有不支援建構案例。
</task_result>
</task>
