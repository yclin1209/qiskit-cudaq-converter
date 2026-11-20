# Step 5: coder

start 19:58:07 end 20:03:38 duration 331.4s

## Prompt (from orchestrator)

你是 coder。專案 /workspace/qiskit-cudaq-converter。先讀 AGENTS.md、specs/SPEC.md（尤其 §3.8、§3.9、§5 第 11～14 條、§6、§7）、docs/plan.md §4 批次 C，並看現有 src/qcconvert/（批次 A、B 已完成）。文件、notebook 說明、回覆用繁體中文（專有名詞附英文）。

任務：實作批次 C：
- src/qcconvert/widgets.py：ConverterApp(debounce=0.3)，屬性 input／output（唯讀 Textarea）、方向 ToggleButtons（Qiskit → CUDA-Q／CUDA-Q → Qiskit）、狀態列（成功／錯誤含行號，不顯示 traceback）、「在 CUDA-Q 執行並對照」按鈕、Output 區顯示 target、counts 對照表、fidelity、TVD；observe value 自動轉換，debounce=0 時同步；切換方向把右欄搬到左欄再轉換。qcconvert.show() 顯示並預填 Bell／GHZ 範例。
- src/qcconvert/magics.py：load_ipython_extension；%%qiskit2cudaq [--run] [--name NAME]（kernel 放進使用者命名空間）、%%cudaq2qiskit [--name NAME]（QuantumCircuit 放進命名空間）。確保 `%load_ext qcconvert` 可用（__init__.py 匯出 load_ipython_extension）。
- src/qcconvert/__main__.py：CLI `python -m qcconvert INPUT.py --to cudaq|qiskit [-o OUT.py] [--check]`，exit code 0 等價、1 不等價、2 轉換錯誤。
- colab/qcconvert_demo.ipynb：依 SPEC §6 九項內容；QCCONVERT_SKIP_INSTALL=1 跳過安裝；Colab 以外不呼叫 google.colab；明說「會執行輸入的程式碼」。用 Python 腳本（nbformat）在 tmp 或直接用 Write 分段寫出 JSON 皆可，但專案內不留產生腳本以外的暫存檔。
- colab/README_colab.md、README.md（SPEC §7 內容，含支援／不支援清單、Colab 步驟、gates、已知限制，如受控 r1 經 OpenQASM 2 的限制）。
- scripts/build_dist.py：產生 dist/qcconvert_colab.zip（內含 qcconvert/ 原始碼、qcconvert_demo.ipynb、README_colab.md；不含 .venv、__pycache__、測試）；支援指定輸出目錄參數以便測試用 tmp_path。若 scripts/__init__.py 不需要可移除（只能刪自己建立的檔案）。
- 測試：tests/test_widgets.py（第 11 條，含執行按鈕在 qpp-cpu 並斷言 Output 內容）、tests/test_magics.py（第 12 條，InteractiveShell.instance()）、tests/test_cli.py、tests/test_notebook.py（第 13 條，nbclient，env QCCONVERT_SKIP_INSTALL=1、QCCONVERT_TARGET=qpp-cpu，timeout 600，工作目錄用 tmp_path）、tests/test_build_dist.py（第 14 條，tmp_path，解壓後 sys.path import qcconvert 轉換 Bell；注意 import 隔離，可用 subprocess）。
規則：暫存檔只寫 tmp_path；專案根與 tests/ 不留 scratch/probe/debug 檔；dist/ 不要留在專案（測試只寫 tmp_path）；不可改 specs/、AGENTS.md、harness/、.opencode/；不可 git commit/push。每次寫檔約 150 行以內。
完成前跑四項 gates 直到全綠：
.venv/bin/python -m pytest -q ; .venv/bin/ruff check src tests scripts ; .venv/bin/ruff format --check src tests scripts ; .venv/bin/mypy src
回覆 15 行內：完成項目、gates 最後一行、覆蓋率、總耗時。

## Output

<task id="ses_e072dcdb8ffeI8OhGZ5dlwNmA6" state="completed">
<task_result>
已完成批次 C：新增雙欄編輯器（widget）、cell magic、命令列（CLI）、Colab notebook、zip 打包腳本與驗收測試，並更新繁體中文使用文件。

**變更檔案：** `src/qcconvert/{widgets,magics,__main__,__init__}.py`、`tests/test_{widgets,magics,cli,notebook,build_dist}.py`、`scripts/build_dist.py`、`colab/{qcconvert_demo.ipynb,README_colab.md}`、`README.md`。

**品質關卡（gates）實際結果：**
- `ruff format src tests scripts`：25 files left unchanged
- `ruff check --fix src tests scripts`：All checks passed!
- `mypy src`：Success: no issues found in 12 source files
- `pytest -q`：197 passed, 2 warnings in 33.18s；覆蓋率（coverage）91.31%
- 額外檢查：`ruff check` 通過；`ruff format --check` 顯示 25 files already formatted。

**尚未解決：** CLI 的 `--to qiskit --check` 因 CUDA-Q 原始碼僅作 AST 靜態解析，不安全執行原始參考，仍回傳錯誤碼 2；另有 CUDA-Q 預覽與 API 的兩則警告，不影響測試。
</task_result>
</task>
