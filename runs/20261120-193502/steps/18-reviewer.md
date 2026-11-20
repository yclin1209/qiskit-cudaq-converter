# Step 18: reviewer

start 00:24:02 end 00:42:45 duration 1123.3s

## Prompt (from orchestrator)

你是 reviewer（唯讀）。專案 /workspace/qiskit-cudaq-converter。讀 AGENTS.md、specs/SPEC.md、docs/plan.md，審查 src/qcconvert/、tests/、scripts/build_dist.py、colab/、README.md。回覆用繁體中文（專有名詞附英文）。

第 5 輪。你上一輪的兩個阻擋問題，coder 宣稱已修正：
- src/qcconvert/runner.py:17,34,44 — compare 的 args 依 kernel 簽章順序綁定（含清理後名稱與 ParameterVector）。
- src/qcconvert/runner.py:88 — 有末端測量時從使用者 kernel 重建測量前演化；無法重建時只比較分佈（statevector_equal 不宣稱 True）；widgets.py:103、README.md:11 有標示。
測試在 tests/test_regressions.py:489 起。請用 .venv/bin/python -c 實驗驗證（不寫檔），含：非字母序參數、ParameterVector＋純量混合、錯誤 kernel 加測量、中途測量、kernel=None、CLI --check 與 widget 對「只比較分佈」的處理。確認無迴歸後全面複查。
- 驗收以 SPEC §5 凍結 14 條為準，逐條 PASS／FAIL 附依據（檔案:行號）。範圍外只列「建議」，不可作為 FAIL 理由。
- 可執行四項 gates：.venv/bin/python -m pytest -q ; .venv/bin/ruff check src tests scripts ; .venv/bin/ruff format --check src tests scripts ; .venv/bin/mypy src
回覆 35 行內；FAIL 問題以「檔案:行號 — 一句描述」列出。最後一行必須是 `VERDICT: PASS` 或 `VERDICT: FAIL`。

## Output

<task id="ses_e063a5933ffe43UswwCbhVryo6" state="completed">
<task_result>
上一輪的兩個阻擋問題都修好了，但這輪實驗找到一個新缺陷：兩個 qubit 的中途測量（mid-circuit measurement）會讓 `compare` 當掉，所以判定 FAIL。

**四項 gates（實際執行結果）**：pytest 293 passed（73 秒），覆蓋率 92.32%；`ruff check` 全過；`ruff format --check` 26 files already formatted；`mypy` 12 個檔案無問題。根目錄沒有多餘檔案。

**上一輪問題的實驗驗證**：
- **參數順序**：非字母序的 `b, a` 加 `ParameterVector th`，以及簽章順序 `(th: list[float], b, a)` 的手寫 kernel，fidelity 約 1，結果為 True。
- **錯誤 kernel 加測量**：手寫 kernel 多一個 `s` 閘再加 `mz`，fidelity 0.956，`statevector_equal=False`。這次有正確抓出來，但這個例子的 TVD 只有 0.003，靠分佈比較抓不到。
- **`kernel=None`**、測量後只作用在別的 qubit 的閘、單一 qubit 中途測量後接 `x`：都正確，`distribution_only=True`、`statevector_equal=None`。
- **對「只比較分佈」的處理**：CLI `--check` 回 exit 0；widget 會印「僅比較分佈」（`widgets.py:104`）。

**新發現的缺陷（重現步驟）**：電路為 `h(0); measure(0,0); cx(0,1); measure(1,1)`。
- 產生的 kernel 只取樣得到長度 1 的位元字串（register `__global__`）。
- `reorder_counts` 因而丟出 `IndexError`。
- CLI `--check` 沒有攔截這個例外，直接印 traceback，沒有回 exit 2。
- widget 的執行按鈕同樣沒攔截，也會丟例外。

**SPEC §5 驗收**
1. PASS — 四項 gates 全綠，覆蓋率 92.32%（大於 90%）。
2. PASS — 每個閘與受控版本都有測試（`tests/test_gate_mapping*.py`），全部通過。
3. PASS — CUDA-Q 原始碼轉 Qiskit 的逐閘、`.ctrl`、`.adj` 測試（`tests/test_cudaq_ast.py`）。
4. PASS — 隨機電路語料（固定 seed）與 round trip 測試都通過。
5. PASS — `Parameter`、`ParameterVector`、運算式都有測試；簽章順序有回歸測試（`test_regressions.py:489-532`）。
6. FAIL — 位元順序、GHZ、部分測量、多 creg 的測試都在且通過（`test_regressions.py:81,128`）。但多 qubit 中途測量的分佈比較會當掉，違反 §3.5（見阻擋問題 1）。
7. PASS — 多個 `QuantumRegister` 兩個方向的測試都通過。
8. PASS — 不支援的建構與含行號的錯誤訊息（`tests/test_errors.py`、`tests/test_cudaq_errors.py`）。
9. PASS — Qiskit 原始碼輸入的四種情況都有測試，且通過。
10. PASS — kernel 物件轉 Qiskit（經 OpenQASM 2）的測試（`tests/test_kernel_object.py`），含 `synthesize`。
11. PASS（但有缺口）— widget 的既有測試通過，但執行按鈕遇到上面的情境會丟出未攔截的例外。
12. PASS — `tests/test_magics.py`。
13. PASS — `tests/test_notebook.py` 用 `nbclient` 跑完，全部通過。
14. PASS — `tests/test_build_dist.py` 檢查 zip 內容，並解壓後 import。

**阻擋問題（blocking）**
1. `src/qcconvert/runner.py:121-124` — 中途測量時 CUDA-Q 取樣的位元字串比測量的 qubit 數短，`reorder_counts`（`equivalence.py:37`）丟出 `IndexError`，`compare` 當掉，違反 §3.5「中途測量只比較分佈」。修法：`mid` 為真時要用其他方式取得每次 `mz` 的結果，例如逐次取樣，或把中途測量的位元另外分開處理；並為這個電路加回歸測試。
2. `src/qcconvert/__main__.py:36` 與 `src/qcconvert/widgets.py:106` — 沒有攔截上述例外：CLI `--check` 印 traceback 而不是回 exit 2（違反 §3.9），widget 會顯示 traceback（違反 §3.8）。修法：`compare` 內部把這類錯誤包成 `ConversionError`，或在這兩處擴大攔截範圍。

**建議（non-blocking）**
- 拿使用者自己寫、和電路不一致的 kernel（中途測量 `h, mz, h, mz` 對 `h, h, measure`）呼叫 `compare`，也會丟 `IndexError`。宜在比較前檢查位元字串長度，給出清楚的錯誤訊息。
- `widgets.py` 的覆蓋率 81% 偏低，建議補執行按鈕出錯路徑的測試。

VERDICT: FAIL
</task_result>
</task>
