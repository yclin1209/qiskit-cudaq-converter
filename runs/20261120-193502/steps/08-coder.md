# Step 8: coder

start 20:21:27 end 20:25:58 duration 270.8s

## Prompt (from orchestrator)

你是 coder。專案 /workspace/qiskit-cudaq-converter（讀 AGENTS.md、specs/SPEC.md、docs/plan.md）。第 1 輪審查 FAIL，請修正以下問題。回覆與文件用繁體中文（專有名詞附英文）。

reviewer＋tester 發現（tests/test_regressions.py 已有對應 xfail(strict=True) 測試，修好後移除 xfail 標記使其成為正常測試）：
1. src/qcconvert/runner.py:73-76 — counts 映射錯誤：CUDA-Q sample bitstring 依 qubit 索引排列（只含被測量 qubit，qubit 索引小者在左），而程式依測量順序取 key[index]。非遞增測量（x(2); measure(2,0); measure(0,1)）與多 creg 部分測量（test_partial_multiple_cregs_distribution）都錯。修正並確保 clbit 映射正確（未測量的 clbit 為 0）。
2. src/qcconvert/runner.py:39 — compare(args=…) 帶 ParameterVector 值 TypeError；Qiskit assign_parameters 順序與 kernel 簽名（cudaq_io.py:43，純量在前、list 在後）不一致。統一順序並展開 vector。
3. src/qcconvert/cudaq_io.py:26 — 參數名清理要避開所有 CUDA-Q 閘／測量名（rx、x、h、mz、r1、u3、reset…）、cudaq、q、np、math、Python 內建與關鍵字。
4. §5 第 3 條：每個 CUDA-Q 閘名稱（h x y z s t sdg? tdg? rx ry rz r1 u3 swap 及 mz/mx/my/reset）各有一個原始碼→Qiskit 等價測試，且每個可受控閘各有 `.ctrl` 等價測試、可 adj 的有 `.adj` 測試（tests/test_cudaq_ast.py:37-38 目前只有 x/s/r1/u3）。請查 .venv 內 cudaq 原始碼確認 cudaq 0.17 是否真的有 sdg/tdg 等名稱；若有就在 cudaq_ast.py:10 支援並測試，若沒有就在 README 明列。mx/my 要驗分佈等價（tests/test_cudaq_ast.py:94 目前只驗結構）。
5. §5 第 8 條（tester 指出）：CUDA-Q 端「非法參數型別」（例如 int、str、無註記參數）、非常數索引、非常數 range、測量結果 if、while、呼叫其他 kernel、exp_pauli、cudaq.control 各有測試，斷言 UnsupportedFeatureError、訊息含建構名稱與行號（tests/test_cudaq_errors.py）。
6. 建議（順手做）：tests/test_magics.py:23 對 kernel 做 compare 等價斷言；隨機語料加入 Parameter 物件與更多閘（u、r、sxdg、ccx、受控閘）但維持總耗時合理；cudaq_io.py:160 r1→rz warning 只在受控 rz 出現時發出。

規則：暫存檔只寫 tmp_path；專案根與 tests/ 不留 scratch/probe/debug 檔；不可改 specs/、AGENTS.md、harness/、.opencode/；不可 git commit/push；每次寫檔約 150 行以內。
完成前跑四項 gates 直到全綠：
.venv/bin/python -m pytest -q ; .venv/bin/ruff check src tests scripts ; .venv/bin/ruff format --check src tests scripts ; .venv/bin/mypy src
回覆 15 行內：每項修正（檔案:行號）、gates 最後一行、覆蓋率、耗時、xfail 是否歸零。

## Output

<task id="ses_e0718714effeNUySx7IH7smsyf" state="completed">
<task_result>
已修正並通過品質關卡（gates）：

- `src/qcconvert/runner.py:39,73`：修正 `ParameterVector` 綁定順序，以及部分、非遞增測量的 classical bit 映射；`tests/test_regressions.py:14,24,104` 的對應測試已移除 `xfail`。
- `src/qcconvert/cudaq_io.py:20,160`：避開閘名、測量名及 Python 內建名稱；僅在翻譯結果出現受控 `rz` 時提出相位警告。
- `tests/test_cudaq_ast.py:37,94`：擴充受控閘測試，加入 `mz/mx/my` 分佈與 `reset` 驗證；`tests/test_cudaq_errors.py:29` 補齊非法參數及非常數索引測試；`tests/test_magics.py:23` 加入等價斷言。
- `README.md:9`：註明 CUDA-Q 0.17 無獨立 `sdg`／`tdg` 名稱，須用 `.adj`。

實際結果：`ruff format`：26 files already formatted；`ruff check --fix` 與檢查：All checks passed；`mypy src`：Success: no issues found in 12 source files；`pytest -q`：**237 passed，2 warnings，53.42s**。覆蓋率 **91.93%**；`xfail` **0**。未解決：無阻擋品質關卡的問題；隨機語料擴充建議尚未實作。
</task_result>
</task>
