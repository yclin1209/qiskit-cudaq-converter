# 專案規則（AGENTS.md）

> 所有 agent 每次啟動都會讀這份文件。內容以繁體中文為主，專有名詞附英文。

## 專案目標
開發 `qcconvert`：Qiskit 與 CUDA-Q 之間的即時程式碼轉換器（real-time code converter），並能在 Google Colab 一鍵執行 CUDA-Q（有 GPU 用 `nvidia` target，沒有就用 `qpp-cpu`）。詳細需求見 `specs/SPEC.md`，那是唯一的需求依據；驗收條件已凍結（frozen），不可自行增刪。

## 語言與技術限制
- Python 3.11+；程式放 `src/qcconvert/`（套件名 `qcconvert`）。`.venv` 已透過 `.pth` 把 `src/` 加入 import path。
- 執行期依賴只允許：`qiskit`（目標 2.x，相容 1.x 以上的 API 為佳）、`cudaq`、`numpy`、`ipywidgets`、`IPython`。開發／測試用 `pytest`、`pytest-cov`、`ruff`、`mypy`、`nbclient`、`nbformat`、`ipykernel`、`qiskit-aer`（選用）。新增依賴要先寫進 `docs/plan.md` 由人核准。
- 文件、計畫、測試說明、notebook 說明文字用繁體中文，專有名詞附英文；程式碼、指令、檔名、識別字維持英文。
- `.venv` 已安裝好所有依賴（cudaq 0.17.0、qiskit 2.6.2、qiskit-aer 0.18.4 等），沒有網路安裝權限，也不需要。

## 已實測的環境事實（box，CPU，cudaq 0.17.0 / qiskit 2.6.2）
1. 預設 target 為 `qpp-cpu`；本機沒有 GPU，`nvidia` target 不可用。
2. `@cudaq.kernel` 需要能用 `inspect` 取回原始碼：`exec()` 字串定義的 kernel 會失敗（`could not retrieve source`）。產生的 kernel 原始碼必須先寫成暫存 `.py` 檔再用 `importlib` 載入（Jupyter cell 內直接定義則可以）。
3. `cudaq.get_state(kernel)` 的振幅索引與 Qiskit `Statevector` 一樣是 little-endian（qubit 0 為最低位元）；但 `cudaq.sample` 的位元字串（bitstring）是 qubit 0 在最左邊，與 Qiskit counts key（qubit 0 在最右邊）相反。轉換與比較時要明確處理，並以測試證明。
4. `cudaq.translate(kernel, format="openqasm2")` 可用，但有參數的 kernel 要先 `cudaq.synthesize(kernel, *args)`；輸出會把 `ccx`、`swap` 拆成基本閘，`r1` 會變成 `rz`（差一個全域相位 global phase）。
5. `cudaq.sample`／`observe` 會發出 FutureWarning（API 未來會改），測試不可依賴警告文字。

## 絕對不能做的事
- 不可宣稱沒有實際跑過的結果；回報數字必須來自實際指令輸出。
- 不可修改 `specs/`、`AGENTS.md`、`harness/`、`.opencode/`（只有人能改）；不可 `git push`、`git commit`、刪除他人檔案。
- 不可讀取或搜尋專案目錄以外的任何路徑（`.venv` 內的套件原始碼除外，查 API 用）。
- 不可把任何金鑰、token、帳號資訊寫進專案。

## 品質關卡（Gates）
四項全過才算完成，指令固定如下：
```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests scripts
.venv/bin/ruff format --check src tests scripts
.venv/bin/mypy src
```
- 格式檢查只檢查 `src tests scripts`，不要用 `.`（ruff 會連 Markdown／notebook 一起檢查，曾讓實驗卡死）。
- mypy 設定放在 `pyproject.toml`：`strict = true`，但對 `cudaq`、`qiskit*`、`ipywidgets`、`IPython` 允許 `ignore_missing_imports`；產生 kernel 的模組可對 cudaq 呼叫局部 `# type: ignore[...]`（要寫原因）。
- 覆蓋率（coverage）：`src/qcconvert` 行覆蓋率 ≥ 90%（`pytest --cov=qcconvert --cov-fail-under=90` 寫進 `pyproject.toml` 的 addopts）。
- 全套測試在本機 8 核 CPU 上要在 10 分鐘內跑完。

## 測試規則
- 暫存檔一律寫在 pytest 的 `tmp_path`，不可寫進專案目錄。
- 隨機電路一律用固定亂數種子（seed），結果必須可重現（deterministic）。
- 每個斷言（assertion）要有意義，不可只檢查「沒有丟例外」。

## 紀錄
- 每輪結束 orchestrator 在本次 run 目錄的 `loop-log.md` 追加一行：輪次、各 VERDICT、gates 摘要。
- 驗收以 `sessions/*.json` 與 `runs/final-check/gates.txt` 為準，不以 orchestrator 自己寫的 loop-log 為準。
- 版本由 harness 寫入 `runs/versions.txt`，子代理不需要（也沒有權限）執行 `opencode --version`。

## 已決定事項（由 MATT 決定）
1. 轉換的單位是「電路層級」（circuit-level），不處理變分演算法（VQE/QAOA）的古典最佳化迴圈、`observe`／Hamiltonian、雜訊模型（noise model）。
2. Qiskit 原始碼輸入的處理方式：在獨立命名空間（namespace）執行使用者程式碼，再取出 `QuantumCircuit`（見 SPEC §3.2）。這是使用者自己的程式碼，在自己的 Colab 執行，文件需說明「會執行輸入的程式碼」。
3. CUDA-Q 原始碼輸入用 AST 靜態解析（不執行），支援 SPEC §3.4 的子集；超出子集給出清楚錯誤。
4. 不需要發佈到 PyPI／GitHub；Colab 以上傳 zip 方式安裝（見 SPEC §6）。
