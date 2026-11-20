# qcconvert：Qiskit ⇄ CUDA-Q 即時程式碼轉換器

> 開發中。需求見 `specs/SPEC.md`，專案規則見 `AGENTS.md`。本 repo 只在本機，不推送（push）到任何遠端。

## 開發流程（多代理 multi-agent loop）
- `bash harness/drive.sh`：smoke test 模型 → orchestrator（planner → coder → reviewer + tester，最多 8 輪）→ final gates。
- 模型（2026-11-20 MATT 第二次調整）：規劃、實作、測試用 OpenAI——planner／coder／tester `cx/gpt-6-sol`；審查與總控用 Claude——reviewer／orchestrator `cc/claude-opus-5-5`；小任務（標題等）`cc/claude-haiku-5-5`。第一次調整的 run（planner 用 opus）在第 1 輪規劃階段因 Claude 串流停滯（stream content stall）中止，紀錄保留在 `runs/ABORTED-20261120-175733-planner-stall/`。
- 金鑰只在執行時從 `~/.omniroute` 讀入環境變數，不存進 repo。
