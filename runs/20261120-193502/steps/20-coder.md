# Step 20: coder

start 01:27:08 end 02:13:51 duration 2803.4s

## Prompt (from orchestrator)

你是 coder。專案 /workspace/qiskit-cudaq-converter（讀 AGENTS.md、specs/SPEC.md §3.5、docs/plan.md）。第 5 輪 reviewer 與 tester 皆 FAIL（§5 第 6 條），請修正。回覆與文件用繁體中文（專有名詞附英文）。

問題（tests/test_regressions.py:544-627 已有 5 個 xfail(strict=True) 重現）：
1. src/qcconvert/runner.py:121-124、equivalence.py:37 — 多 qubit 中途測量（h(0); measure(0,0); cx(0,1); measure(1,1)）時 CUDA-Q 取樣位元字串長度不足，reorder_counts IndexError。
2. 同一 qubit 重複測量（測量→閘→再測量到不同／相同 clbit）TVD 1.0；reset 後測量 counts 錯（預期 {'01':128} 得 {'00':128}）。
3. src/qcconvert/__main__.py:36、widgets.py:106 — 上述例外未攔截：CLI --check 應回 exit 2（不是 1 或 traceback），widget 狀態列顯示錯誤訊息不含 traceback。

修法方向（請先查 .venv 內 cudaq 原始碼並實測 cudaq 0.17 行為，不要猜）：
- 中途測量時 CUDA-Q 取樣需要逐次（per-shot）取得每個測量結果與其對應 clbit。可評估：產生的 kernel 對每次測量用具名變數（例如 `c0 = mz(q[0])`），再用 SampleResult 的 register 名稱／`get_sequential_data(register)`／`get_register_counts` 重組每 shot 的完整 clbit 字串（同一 clbit 被多次寫入時取最後一次）；或 cudaq 的 explicit measurements 選項（若 0.17 有，如 `cudaq.sample(..., explicit_measurements=True)`）。
- Qiskit 端中途測量參考分佈用 qiskit_aer（已安裝、固定 seed_simulator）或其他正確方法；最終 counts 以 Qiskit clbit 順序呈現。
- reset 後測量要正確（確認產生的 kernel 有 reset 並在取樣結果正確對應）。
- compare 遇到無法比較的情況（例如使用者 kernel 測量數不一致）包成 ConversionError 帶清楚訊息；CLI 捕捉 ConversionError 及其他比較錯誤回 exit 2；widget 顯示簡短錯誤。
修好後移除這 5 個 xfail，並補測試：中途測量（跨 qubit、同 qubit 重複、reset 後）分佈等價且報告標示只比較分佈。

規則：暫存檔只寫 tmp_path；專案根與 tests/ 不留 scratch/probe/debug 檔；不可改 specs/、AGENTS.md、harness/、.opencode/；不可 git commit/push；每次寫檔約 150 行以內。
完成前跑四項 gates 直到全綠：
.venv/bin/python -m pytest -q ; .venv/bin/ruff check src tests scripts ; .venv/bin/ruff format --check src tests scripts ; .venv/bin/mypy src
回覆 12 行內：實測的 cudaq API 事實、修正（檔案:行號）、gates 最後一行、覆蓋率、耗時、xfail 是否歸零。

## Output

<task id="ses_e060093ceffes99cZxEncJfyB7" state="completed">
<task_result>
已修正中途測量的分佈比較；五個 `xfail` 已移除，並補上重複寫入同一 clbit、測量數不一致的回歸測試。

- **實測 CUDA-Q 0.17**：`sample(..., explicit_measurements=True)` 會依測量順序串接位元，但實測不能正確保留部分中途測量的關聯分佈；`run` 搭配回傳 `list[bool]` 的 kernel 可取得逐次（per-shot）結果。
- `src/qcconvert/runner.py:19`：由可讀的 kernel 原始碼產生逐次回傳測量值的 kernel，按測量順序寫入 Qiskit clbit；測量數不符時回報 `ConversionError`。
- `src/qcconvert/__main__.py:36`、`src/qcconvert/widgets.py:106`：比較錯誤分別回 CLI exit 2、顯示於 widget 狀態列，不洩漏 traceback。
- `tests/test_regressions.py:553`：跨 qubit、同 qubit 重測、reset 後測量及分佈限定報告均通過。
- 品質關卡（gates）：`ruff format`：26 files left unchanged；`ruff check --fix`：All checks passed!；`mypy src`：Success: no issues found in 12 source files。
- `pytest -q`：**300 passed, 2 warnings in 64.83s**；覆蓋率 **92.30%**；`xfail` **0**。另跑的唯讀 Ruff 檢查與格式檢查皆通過。
- 尚未解決：CUDA-Q 的命名測量子暫存器（sub-register）介面已標示將棄用；目前中途測量路徑不依賴它。
</task_result>
</task>
