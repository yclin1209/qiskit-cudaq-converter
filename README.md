# qcconvert：Qiskit ⇄ CUDA-Q 即時程式碼轉換器

> 開發中。需求見 `specs/SPEC.md`，專案規則見 `AGENTS.md`。本 repo 只在本機，不推送（push）到任何遠端。

## 開發流程（多代理 multi-agent loop）
- `bash harness/drive.sh`：smoke test 模型 → orchestrator（planner → coder → reviewer + tester，最多 8 輪）→ final gates。
- 模型（2026-11-20 MATT 調整）：規劃與審查用 Claude——orchestrator／planner／reviewer `cc/claude-opus-5-5`；實作與測試用 OpenAI——coder／tester `cx/gpt-6-sol`；小任務（標題等）`cc/claude-haiku-5-5`。
- 金鑰只在執行時從 `~/.omniroute` 讀入環境變數，不存進 repo。
