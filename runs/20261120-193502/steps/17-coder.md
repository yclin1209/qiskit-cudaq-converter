# Step 17: coder

start 23:59:51 end 00:23:55 duration 1444.8s

## Prompt (from orchestrator)

你是 coder。專案 /workspace/qiskit-cudaq-converter（讀 AGENTS.md、specs/SPEC.md、docs/plan.md）。第 4 輪 reviewer FAIL，請修正。回覆與文件用繁體中文（專有名詞附英文）。

問題（reviewer 第 4 輪；tester 已在 tests/test_regressions.py:489-520 以 xfail(strict=True) 重現）：
1. src/qcconvert/runner.py:41-48 — compare 依參數名排序綁定 args 到 Qiskit 電路，但 kernel 的 args 依其函式簽章順序傳入；kernel(theta: float, alpha: float) 經 cudaq_to_qiskit 後 compare(r.to_qiskit(), k, args=(0.3, 1.9)) fidelity 錯誤。修法：args 的語意定為「kernel 簽章順序」；從使用者 kernel 取得參數名順序（如 kernel 物件的 arguments／簽章資訊，或 AST 原始碼；kernel 為 None 時用 qiskit_to_cudaq 產生的簽章順序），再依名稱（含清理後名稱對應、ParameterVector 展開）綁定 Qiskit 參數。同時 IR／cudaq_to_qiskit 宜保留原始參數順序。在 README 與 docstring 說明 args 順序。
2. src/qcconvert/runner.py:81 — 有測量時狀態向量比較改用 qiskit_to_cudaq(clean) 重新產生的 kernel，不是使用者的 kernel，會誤判（a=h;measure vs kernel b=h;z;measure → statevector_equal=True）。修法：對使用者 kernel 取得「去除末端測量」的狀態（例如 cudaq.get_state 對含 mz 的 kernel 是否可行請實測；或用 kernel 物件 → IR（cudaq_io OpenQASM 2 路徑）去除測量後重建 kernel）；做不到時 statevector_equal=None、fidelity=None 並在報告標明只比較分佈。CLI --check 與 widget 須相容 None（只依 TVD 判定）。
修好後移除那兩個 xfail，並補測試：非字母序參數反向 compare、ParameterVector＋純量混合順序、錯誤 kernel 加測量不得為 True。
3. 效能：tester 某次全套 pytest 耗時 430 秒（他人同時跑時為 47 秒），請確認單獨跑全套耗時並回報；若有明顯慢的測試（pytest --durations=10），在不減少 §5 要求數量的前提下優化。

規則：暫存檔只寫 tmp_path；專案根與 tests/ 不留 scratch/probe/debug 檔；不可改 specs/、AGENTS.md、harness/、.opencode/；不可 git commit/push；每次寫檔約 150 行以內。
完成前跑四項 gates 直到全綠：
.venv/bin/python -m pytest -q ; .venv/bin/ruff check src tests scripts ; .venv/bin/ruff format --check src tests scripts ; .venv/bin/mypy src
回覆 12 行內：修正（檔案:行號）、gates 最後一行、覆蓋率、耗時、最慢 3 個測試、xfail 是否歸零。

## Output

<task id="ses_e06507e75ffeWqATK7dqElSYnC" state="completed">
<task_result>
已修正第 4 輪問題：

- `src/qcconvert/runner.py:17,34,44`：`compare` 的 `args` 依 kernel 簽章順序綁定，支援清理後參數名稱及 `ParameterVector`。
- `src/qcconvert/runner.py:88`：末端測量改從**使用者 kernel** 重建測量前演化；無法重建時只比較分佈，不再以重新產生的 kernel 宣稱狀態等價。
- `src/qcconvert/widgets.py:103`、`README.md:11`：標示僅比較分佈的情況，並說明 `args` 順序。
- `tests/test_regressions.py:489` 起：移除兩個 `xfail`，新增混合參數順序及含測量的回歸測試。

品質關卡（gates）：format `26 files left unchanged`；check `All checks passed!`；mypy `Success: no issues found in 12 source files`；pytest `293 passed, 2 warnings in 57.14s`。覆蓋率 **92.32%**；`xfail` **0**。

最慢三項：隨機語料（random corpus）27.51 秒、CLI／打包 2.65 秒、notebook 2.50 秒。單獨全套未重現 430 秒耗時；尚未確認當時的資源競爭原因。
</task_result>
</task>
