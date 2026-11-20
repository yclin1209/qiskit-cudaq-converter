# SPEC：qcconvert（Qiskit ⇄ CUDA-Q 即時程式碼轉換器）

> 唯一需求依據。驗收條件（§5）與問題清單已凍結（frozen）：實作中發現的新問題記在 `docs/plan.md` 的「待確認」，不可自行擴大或縮小範圍。版本基準：cudaq 0.17.0、qiskit 2.6.2（box `.venv`）。

## 1. 目標
1. 把 Qiskit 電路（`QuantumCircuit` 物件或 Qiskit 原始碼）轉成可執行的 CUDA-Q `@cudaq.kernel` Python 原始碼與 kernel 物件。
2. 把 CUDA-Q kernel（原始碼或 kernel 物件）轉回 Qiskit 原始碼與 `QuantumCircuit`。
3. 用狀態向量（statevector）與取樣分佈（sampling distribution）證明轉換前後等價（equivalence）。
4. 在 Google Colab 提供「即時」體驗：雙欄編輯器（two-pane editor）、cell magic、一鍵在 CUDA-Q 執行並和 Qiskit 結果對照。

## 2. 模組（建議，可在 plan 中調整檔名，但公開 API 名稱固定）
| 模組 | 職責 |
|---|---|
| `qcconvert/ir.py` | 中立中間表示（IR）：`Circuit(num_qubits, num_clbits, ops, params, qreg_names, creg_names)`、`Op(name, targets, controls, params, clbits)`。參數以符號名稱字串或浮點數表示，運算式（expression）以 Python 運算式字串保存。 |
| `qcconvert/qiskit_io.py` | `QuantumCircuit` ⇄ IR；IR → Qiskit 原始碼字串。 |
| `qcconvert/cudaq_io.py` | IR → CUDA-Q 原始碼字串；載入原始碼成 kernel；CUDA-Q 原始碼（AST）→ IR；kernel 物件 → IR（經 OpenQASM 2）。 |
| `qcconvert/api.py` | 公開 API（§3.1）。 |
| `qcconvert/equivalence.py` | 狀態向量與分佈比較、位元順序轉換。 |
| `qcconvert/runner.py` | 選擇 target、執行、產生對照結果。 |
| `qcconvert/widgets.py` | ipywidgets 雙欄編輯器。 |
| `qcconvert/magics.py` | IPython cell magic 與 `load_ipython_extension`。 |
| `qcconvert/__main__.py` | CLI。 |
| `qcconvert/errors.py` | `UnsupportedFeatureError(ConversionError)`、`ConversionError(Exception)`，訊息含建構名稱與（有的話）原始碼行號。 |

## 3. 功能需求

### 3.1 公開 API（從 `qcconvert` 直接匯入）
- `qiskit_to_cudaq(src: QuantumCircuit | str, *, kernel_name: str = "kernel", decompose_unknown: bool = True) -> ConversionResult`
- `cudaq_to_qiskit(src: str | object, *, args: Sequence[float] = (), circuit_name: str = "qc") -> ConversionResult`（`object` 指 cudaq kernel 物件）
- `ConversionResult`：dataclass，欄位 `code: str`（產生的原始碼）、`circuit: Circuit`（IR）、`warnings: list[str]`；方法 `to_kernel()`（Qiskit→CUDA-Q 時回傳可執行 kernel）與 `to_qiskit()`（回傳 `QuantumCircuit`）。
- `load_kernel(code: str, name: str) -> object`：把原始碼寫到暫存 `.py` 檔後以 `importlib` 載入（AGENTS.md 環境事實 2），同一份原始碼重複載入不可洩漏大量暫存檔（例如以內容雜湊命名、放在 `tempfile.gettempdir()/qcconvert_kernels/`）。
- `compare(qc: QuantumCircuit, kernel: object | None = None, *, args=(), shots: int = 4000, seed: int | None = 1234) -> CompareReport`：`fidelity`、`statevector_equal: bool`、`qiskit_counts`、`cudaq_counts`（皆轉成 Qiskit 位元順序）、`tvd`、`target`、耗時。

### 3.2 Qiskit 原始碼輸入
- 在新的 dict 命名空間 `exec`；挑選規則：名為 `qc` 的 `QuantumCircuit`，否則最後一個被指派的 `QuantumCircuit`；沒有就丟 `ConversionError("找不到 QuantumCircuit …")`。
- 語法錯誤或執行錯誤要轉成 `ConversionError`，訊息含行號與原始錯誤。
- 文件與 notebook 要明說「會執行輸入的程式碼」。

### 3.3 閘支援（兩個方向都要支援，矩陣必須完全相同，含全域相位 global phase）
- 單位元：`id`（略過）、`h x y z s sdg t tdg`、`sx sxdg`（CUDA-Q 沒有 `sx`，需以含正確全域相位的組合實作，例如 `r1`/`rx` 組合或 `u3` 加相位修正，必須在受控（controlled）情況下也正確）、`rx ry rz`、`p`（→ `r1`）、`u`/`u3`（與 CUDA-Q `u3` 的相位約定要用測試核對）、`u1`、`u2`、`r`（可分解）。
- 雙／多位元：`cx cy cz ch swap crx cry crz cp cu1 ccx cswap mcx`，以及任何「受控版本」的上述單位元閘（`gate.control(n)`）→ CUDA-Q `.ctrl(controls…, target)`。
- `rzz rxx ryy`：分解成基本閘（全域相位一致）。
- `barrier`：略過並加入 warning；`measure`：見 §3.5；`reset`：→ `reset`。
- Qiskit `GlobalPhase`／`circuit.global_phase`：轉到 CUDA-Q 時無法表示，略過並加入 warning；等價比較時以「忽略全域相位」比較（§4）。
- 其他閘：`decompose_unknown=True` 時用 `transpile(..., basis_gates=[支援集合])` 分解，並在 warning 記錄；`False` 時丟 `UnsupportedFeatureError`。
- 不支援（一律 `UnsupportedFeatureError`，訊息需含建構名稱）：經典條件控制（`if_test`、`c_if`、`while_loop`、`for_loop`、`switch`）、`initialize`／`StatePreparation`（`decompose_unknown=False` 時）、`delay`、脈衝（pulse）、多個 `QuantumCircuit` 互相組合的參數綁定以外的動態功能。

### 3.4 CUDA-Q 原始碼輸入（AST 子集，不執行程式）
- 一個（或指定名稱的）`@cudaq.kernel` 函式；參數只能是 `float`（或 `list[float]`，以 `theta[i]` 常數索引使用）。
- `q = cudaq.qvector(N)`（N 為整數常數）、`cudaq.qubit()`；可多個暫存器，依宣告順序串接成 qubit 索引。
- 閘呼叫：§3.3 的 CUDA-Q 名稱、`r1`、`u3`、`.ctrl(...)`（單一或 list 控制）、`.adj(...)`、`mz/mx/my`（整個暫存器或單一 qubit）、`reset`。
- `for i in range(常數)` 迴圈與常數算術索引（例如 `q[i+1]`）要展開；參數運算式（`2*theta`、`np.pi/2`、`math.pi`）要保留為運算式。
- 其他（`if` 依測量結果、`while`、呼叫其他 kernel、`exp_pauli`、`cudaq.control`）→ `UnsupportedFeatureError`，訊息含行號。
- kernel 物件輸入：`cudaq.synthesize`（有參數時）→ `cudaq.translate(format="openqasm2")` → `qiskit.qasm2.loads` → IR；要處理 translate 把 `r1` 變 `rz` 的全域相位（受控時才影響，必要時標 warning）。

### 3.5 測量與暫存器
- Qiskit `measure` 全部在電路最後時：CUDA-Q 產生 `mz`；Qiskit 端保留 creg 對應。
- 中途測量（mid-circuit measurement）後還有閘作用在同一 qubit：轉換可以產生，但 `compare` 只比較分佈，不比較狀態向量（要在報告裡標明）。
- 沒有測量的電路：`compare` 取樣時視為全部 qubit 在最後測量。
- 多個 `QuantumRegister`：CUDA-Q 端用一個 `qvector` 並在產生的原始碼加註解標明原暫存器範圍；反向用 `QuantumRegister` 名稱還原（能還原時）。

### 3.6 參數
- Qiskit `Parameter` → kernel 的 `float` 參數（名稱需清理成合法識別字，且不與 `cudaq`、`q`、內建名稱衝突）；`ParameterVector` → `list[float]`；參數運算式轉成 Python 運算式。
- 反向：kernel 的 `float` 參數 → `Parameter`；`compare` 可用 `args` 帶入數值。

### 3.7 執行（runner）
- `pick_target()`：`cudaq.num_available_gpus() > 0` 時用 `nvidia`（可選 `fp64`），否則 `qpp-cpu`；可用環境變數 `QCCONVERT_TARGET` 覆寫；回傳實際使用的 target 名稱。
- 取樣結果統一轉成 Qiskit 位元順序（qubit 0 在最右）並排序。
- Qiskit 參考結果用 `qiskit.quantum_info.Statevector`；取樣用 `Statevector.sample_counts` 或 `qiskit_aer`（有安裝時），都要可用固定 seed。

### 3.8 即時 UX
- `qcconvert.widgets.ConverterApp()`：左欄 `Textarea`（輸入）、右欄 `Textarea`（輸出，唯讀）、方向切換（`ToggleButtons`：Qiskit → CUDA-Q／CUDA-Q → Qiskit）、狀態列（成功／錯誤訊息，含行號，不顯示 traceback）、「在 CUDA-Q 執行並對照」按鈕、`Output` 區顯示 target、counts 對照表、fidelity、TVD。
- 輸入改變時自動轉換（observe `value`），可用 debounce（預設 0.3 秒，參數可設 0 方便測試）；切換方向時把右欄內容搬到左欄再轉換。
- 不依賴瀏覽器即可測試：測試可直接設定 `app.input.value = "..."` 並同步讀 `app.output.value`（debounce=0）。
- `qcconvert.show()`：顯示 `ConverterApp`，並預填一個 Bell／GHZ 範例。
- Magics：`%load_ext qcconvert` 後提供 `%%qiskit2cudaq [--run] [--name NAME]`（顯示產生的 CUDA-Q 程式碼；`--run` 時執行並顯示對照；把 kernel 放進使用者命名空間）與 `%%cudaq2qiskit [--name NAME]`（顯示 Qiskit 程式碼並把 `QuantumCircuit` 放進命名空間）。

### 3.9 CLI
- `python -m qcconvert INPUT.py --to cudaq|qiskit [-o OUT.py] [--check]`；`--check` 時執行等價比較並以 exit code 表示結果（0 等價、1 不等價、2 轉換錯誤）。

## 4. 等價判定
- 狀態向量：把雙方狀態向量轉成同一位元順序後，`fidelity = |<a|b>|^2 ≥ 1 - 1e-6`（`qpp-cpu` 為 fp64）；GPU fp32 時門檻放寬為 `1 - 1e-4`。比較忽略全域相位，但受控閘的「相對相位」要正確（§3.3）。
- 取樣：總變異距離（TVD）≤ 0.05（4000 shots，固定 seed）。
- 參考實作的位元順序事實見 AGENTS.md 環境事實 3，必須有專門測試鎖住（例如只在 qubit 0 做 `x`，雙方 counts 都是 `'0…01'`）。

## 5. 驗收條件（凍結，共 14 條）
1. 四項 gates 全過（AGENTS.md），覆蓋率 ≥ 90%。
2. §3.3 每個支援的閘各有一個 Qiskit→CUDA-Q 等價測試，並各有一個「放進受控（控制位元處於 |+>）」的等價測試（能受控的閘）。
3. 每個 CUDA-Q 閘名稱（含 `.ctrl`、`.adj`）各有一個 CUDA-Q 原始碼→Qiskit 等價測試。
4. 隨機電路語料（corpus）：固定 seed 產生至少 200 個隨機電路（1–5 qubits、深度 1–20、從支援閘集合抽樣、含參數），Qiskit→CUDA-Q 全部等價；其中至少 50 個再轉回 Qiskit（round trip）仍等價。
5. 參數化電路：`Parameter`、`ParameterVector`、參數運算式各至少 1 個測試，至少 3 組數值帶入後等價。
6. 測量／位元順序：§4 位元順序測試；GHZ、只在部分 qubit 測量、多 creg 的分佈等價測試。
7. 多 `QuantumRegister` 電路兩個方向都能轉換且等價。
8. 不支援的建構（§3.3、§3.4 列出的每一類）各有測試，斷言丟出 `UnsupportedFeatureError` 且訊息含建構名稱；CUDA-Q 原始碼錯誤訊息含行號。
9. Qiskit 原始碼輸入：`qc` 優先、最後一個電路、找不到電路、語法錯誤（含行號）四種情況。
10. kernel 物件→Qiskit（經 OpenQASM 2）至少 5 個測試，含有參數 kernel（`synthesize`）。
11. `ConverterApp`：兩個方向的即時轉換、錯誤顯示、方向切換、執行按鈕（`qpp-cpu`）在測試中以程式觸發並斷言輸出內容。
12. Magics：用 `IPython.testing` 或 `InteractiveShell.instance()` 執行兩個 cell magic，斷言命名空間內出現 kernel／`QuantumCircuit` 且結果等價。
13. Notebook `colab/qcconvert_demo.ipynb`：在 box 以 `nbclient` 無頭（headless）執行（環境變數 `QCCONVERT_SKIP_INSTALL=1` 跳過安裝 cell，`QCCONVERT_TARGET=qpp-cpu`），全部 cell 無錯誤；由 `tests/test_notebook.py` 執行（逾時 600 秒）。
14. `scripts/build_dist.py` 產生 `dist/qcconvert_colab.zip`（內含 `qcconvert/` 套件原始碼、`qcconvert_demo.ipynb`、`README_colab.md`，不含 `.venv`、快取、測試），測試在 `tmp_path` 執行並檢查 zip 內容；解壓後把該目錄加入 `sys.path` 能 `import qcconvert` 並轉換一個 Bell 電路。

## 6. Colab notebook 內容（`colab/qcconvert_demo.ipynb`，說明文字繁體中文）
1. 說明：建議 Runtime → Change runtime type → T4 GPU；CPU runtime 也可跑（`qpp-cpu`）。若先在 CPU runtime 安裝、之後才切換 GPU，要重新安裝 cudaq（安裝時偵測 CUDA 版本決定 cu12／cu13 套件）。
2. GPU 檢查 cell：`nvidia-smi`（失敗不報錯，只印提示）。
3. 安裝 cell（`QCCONVERT_SKIP_INSTALL=1` 時跳過）：`pip install cudaq qiskit ipywidgets`；若 `/content/qcconvert_colab.zip` 存在就解壓並加入 `sys.path`；否則提示用 `google.colab.files.upload()` 上傳（在 Colab 以外不呼叫）。在 Colab 啟用 `google.colab.output.enable_custom_widget_manager()`（有的話）。
4. 環境資訊：cudaq/qiskit 版本、`pick_target()` 結果。
5. API 範例：Bell、GHZ、參數化電路 → CUDA-Q 原始碼 → `compare` 結果。
6. `%load_ext qcconvert`、`%%qiskit2cudaq --run` 與 `%%cudaq2qiskit` 範例。
7. `qcconvert.show()` 雙欄編輯器。
8. （選用）GPU 加速對照：有 GPU 時 20+ qubits 的 GHZ 在 `nvidia` 與 `qpp-cpu` 的耗時比較；沒有 GPU 時跳過。
9. 結尾附「Open in Colab」徽章（badge）說明：目前不放 GitHub，日後有 repo 再補連結。

## 7. 文件
- `README.md`（繁體中文）：功能、支援與不支援清單、Colab 3–4 步驟、本機開發與 gates、已知限制。
- `colab/README_colab.md`：給 Colab 使用者的簡短步驟（打包時一起放進 zip）。

## 8. 不在範圍內
- `observe`、Hamiltonian、雜訊模型、C++（`nvq++`）、OpenQASM 3 輸入、真實硬體 provider、多 GPU（`mgpu`）。
