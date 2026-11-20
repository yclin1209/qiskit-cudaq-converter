# Step 1: planner

start 19:35:25 end 19:38:53 duration 208.8s

## Prompt (from orchestrator)

你是 planner。請閱讀 /workspace/qiskit-cudaq-converter/specs/SPEC.md 與 AGENTS.md（含「已實測的環境事實」與「已決定事項」），為從零開發的 qcconvert 套件撰寫實作計畫，覆寫 docs/plan.md（目前只有章節骨架，請保留章節標題 0～7 並填入內容）。

要求：
- 全部用繁體中文，專有名詞附英文；程式碼／檔名／識別字維持英文。
- 可讀 .venv 內 cudaq／qiskit 套件原始碼查 API（例如 cudaq 的 u3、r1、ctrl/adj、translate、synthesize 的行為），不可讀專案目錄以外其他路徑。不要在專案根目錄或 tests/ 留下暫存檔。
- 內容需涵蓋：
  1. 模組拆分：src/qcconvert/ 下 ir.py、errors.py、qiskit_io.py、cudaq_io.py、api.py、equivalence.py、runner.py、widgets.py、magics.py、__main__.py、__init__.py 的職責與公開 API 簽章（依 SPEC §2、§3.1，名稱固定）。
  2. 閘對照表：§3.3 每個閘 → CUDA-Q 寫法 → 全域相位注意（特別是 sx/sxdg 受控時的相位、u/u3 相位約定、p→r1、rzz/rxx/ryy 分解、translate 把 r1→rz）。
  3. 位元順序（環境事實 3）與等價比較方法（fidelity、TVD、seed）。
  4. 實作批次：批次 A＝IR＋errors＋qiskit_io＋cudaq_io（IR→CUDA-Q 原始碼、load_kernel）＋equivalence＋runner＋api 的 Qiskit→CUDA-Q；批次 B＝CUDA-Q 原始碼 AST→IR、kernel 物件→IR（OpenQASM 2）、round trip；批次 C＝widgets、magics、CLI、colab/qcconvert_demo.ipynb、colab/README_colab.md、scripts/build_dist.py、README.md、pyproject.toml（ruff/mypy strict/pytest addopts 含 --cov=qcconvert --cov-fail-under=90）。每批都要 gates 全綠。注意：批次 A 時 coverage 門檻可能因尚未實作的模組而不足，請規劃處理方式（例如批次 A 就建 pyproject，但未實作模組先不建立）。
  5. 測試清單：逐條對應 SPEC §5 的 1～14，列出測試檔名與內容；隨機語料固定 seed，全套測試 8 核 CPU 10 分鐘內完成（可考慮 pytest-xdist 是否已安裝，若無則控制測試量）。
  6. 假設（需測試驗證）。
  7. 待確認：SPEC 不清楚之處，依 AGENTS.md 已決定事項與保守預設處理。
- 計畫要精簡可執行，約 200～300 行內；分多次寫檔，每次寫入約 150 行以內（先寫前半，再用 edit 補後半）。
- 回覆：精簡繁體中文摘要（20 行內），列出關鍵決策與待確認項目。

## Output

<task id="ses_e0742976fffeGkhD2zPAFUc45T" state="completed">
<task_result>
已覆寫 `docs/plan.md`，保留 0～7 節標題，且只撰寫計畫、未修改程式碼。計畫列明模組職責與公開 API（`docs/plan.md:10`）、逐閘對照與受控相位風險（`docs/plan.md:32`），以及位元順序、保真度（fidelity）與總變異距離（TVD）的比較方式（`docs/plan.md:61`）。

實作分 A／B／C 批，每批都須通過四項品質關卡（gates）；測試清單逐條對應 SPEC §5 的 14 項驗收條件（`docs/plan.md:67`）。未確定的 API 行為另列為「假設，需測試驗證」；待確認項目包括受控 `r1` 的相位還原，以及 CLI 反向檢查的安全參考方式（`docs/plan.md:90`）。本次未執行測試，不宣稱關卡已通過。
</task_result>
</task>
