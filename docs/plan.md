# 實作計畫（plan）— qcconvert

> 由 planner 填寫。唯一需求依據為 `specs/SPEC.md`；遵守 `AGENTS.md`。

## 0. 版本紀錄

- 起點：從零開發；依據 `specs/SPEC.md`（§5 驗收凍結）及 `AGENTS.md` 已決定事項；基準為 Python 3.11+、cudaq 0.17.0、qiskit 2.6.2。
- 本版只規劃，不聲稱已通過測試；A／B／C 完成時各記錄四項品質關卡（gates）實際結果。不新增依賴、不更動凍結文件。

## 1. 模組拆分（Modules）

- `src/qcconvert/ir.py`：`Circuit(num_qubits, num_clbits, ops, params, qreg_names, creg_names)`、`Op(name, targets, controls, params, clbits)`；記錄暫存器大小、映射、測量順序及全域相位警告所需資訊。參數為數值／符號名稱／運算式字串；驗證索引、控制與目標互斥及順序。IR 是兩個方向唯一的共通邊界。
- `src/qcconvert/errors.py`：`ConversionError(Exception)`、`UnsupportedFeatureError(ConversionError)`；訊息包含建構名稱，來源有行號時帶行號，包裝 Qiskit 原始碼的語法／執行錯誤。
- `src/qcconvert/qiskit_io.py`：`QuantumCircuit` ⇄ IR、IR → Qiskit 原始碼；原始碼以隔離命名空間 `exec`，先選 `qc`，否則選最後指派的電路，找不到則報錯；不把程式碼當作安全沙箱。針對未知閘只在允許時分解，保護明列不支援建構；恢復可恢復的暫存器名稱與 classical bit 映射。
- `src/qcconvert/cudaq_io.py`：IR → CUDA-Q 原始碼（合法識別字／參數表／qvector／測量）、`load_kernel(code: str, name: str) -> object`；AST 靜態解析原始碼 → IR（不執行）、kernel 物件 → `synthesize`（需要參數時）→ `translate(format="openqasm2")` → `qiskit.qasm2.loads` → IR。載入時先將 `.py` 放進系統暫存區的 `qcconvert_kernels/`，依內容雜湊快取／受控清理，再以 `importlib` 載入；不得用純 `exec` 建立 kernel。
- `src/qcconvert/equivalence.py`：量子態保真度（fidelity）、取樣總變異距離（TVD）、測量鍵位元重排、測量時序判定及 `CompareReport` 資料模型；不把相位差錯判為不同。
- `src/qcconvert/runner.py`：`pick_target()` 先尊重 `QCCONVERT_TARGET`，否則 GPU → `nvidia`（可選 `fp64`），CPU → `qpp-cpu`；取得實際 target、計時、比較 Qiskit／CUDA-Q 的 statevector 與 counts，串接 `compare`。
- `src/qcconvert/api.py`：`ConversionResult(code: str, circuit: Circuit, warnings: list[str])` 與轉換工作流程；`to_kernel()` 僅對 Qiskit → CUDA-Q 產物可用，`to_qiskit()` 回傳 `QuantumCircuit`；適當錯誤而非默默使用錯誤方向。
- `src/qcconvert/widgets.py`：`ConverterApp(debounce: float = 0.3)` 雙欄編輯器、方向切換、狀態列與執行對照；`debounce=0` 同步更新供無瀏覽器測試；錯誤不顯示 traceback。
- `src/qcconvert/magics.py`：`load_ipython_extension(ipython)` 註冊 `%%qiskit2cudaq [--run] [--name NAME]`、`%%cudaq2qiskit [--name NAME]`；顯示產碼並將結果放入使用者命名空間。
- `src/qcconvert/__main__.py`：`python -m qcconvert INPUT.py --to cudaq|qiskit [-o OUT.py] [--check]`；比對結果碼 0／1／2 對應等價／不等價／轉換失敗。
- `src/qcconvert/__init__.py`：僅匯出固定公開介面與 `show()`；`show()` 預填 Bell／GHZ 範例並顯示編輯器。
- 固定公開簽章：`qiskit_to_cudaq(src: QuantumCircuit | str, *, kernel_name: str = "kernel", decompose_unknown: bool = True) -> ConversionResult`。
- 固定公開簽章：`cudaq_to_qiskit(src: str | object, *, args: Sequence[float] = (), circuit_name: str = "qc") -> ConversionResult`。
- 固定公開簽章：`load_kernel(code: str, name: str) -> object`；`compare(qc: QuantumCircuit, kernel: object | None = None, *, args=(), shots: int = 4000, seed: int | None = 1234) -> CompareReport`。
- `CompareReport` 至少包含 `fidelity`、`statevector_equal`、兩份已正規化 counts、`tvd`、`target` 與耗時；中途測量情境另標示僅比較分佈。

## 2. 閘對照表（Qiskit → CUDA-Q → 全域相位注意事項）

| Qiskit 名稱 | CUDA-Q 寫法／分解方向 | 全域相位注意事項 |
|---|---|---|
| `id` | 略過 | 單獨／受控皆須保持恆等矩陣。 |
| `h`、`x`、`y`、`z` | `h`、`x`、`y`、`z` | 原樣；受控矩陣照測。 |
| `s`、`sdg` | `s`、`s.adj` 或等價分解 | 逆閘實際 API 寫法需驗證。 |
| `t`、`tdg` | `t`、`t.adj` 或等價分解 | 逆閘實際 API 寫法需驗證。 |
| `sx`、`sxdg` | `h; s; h`、`h; sdg; h` | 不能只用 `rx(±π/2)`：少了 `±π/4` 相位；每一個成分均受控才保留相對相位。 |
| `rx`、`ry`、`rz` | `rx`、`ry`、`rz` | 角度及控制版本均須核對矩陣。 |
| `p`、`u1` | `r1(angle, target)` | `r1` 與 `rz` 差全域相位，受控時變相對相位；不可直接替換。 |
| `u`、`u3` | `u3(theta, phi, lam, target)` 或精確相位分解 | Qiskit／CUDA-Q 的 `u3` 相位約定：假設，需測試驗證；受控 `u` 尤須驗證。 |
| `u2` | `u3(π/2, phi, lam, target)` 或精確分解 | 繼承 `u3` 的相位驗證。 |
| `r` | 依 Qiskit 矩陣精確分解為支援閘 | 受控時不能丟掉分解的全域相位。 |
| `cx`、`cy`、`cz`、`ch` | `x.ctrl`、`y.ctrl`、`z.ctrl`、`h.ctrl` | 控制位元置於 `|+⟩` 驗證相對相位。 |
| `swap` | `swap(a, b)` 或三個 `x.ctrl` | 應精確保留矩陣，包含受控版。 |
| `crx`、`cry`、`crz` | `rx.ctrl`、`ry.ctrl`、`rz.ctrl` | 不額外丟棄控制分支相位。 |
| `cp`、`cu1` | `r1.ctrl(angle, control, target)` | 不能改為 `rz.ctrl`，否則改變相對相位。 |
| `ccx`、`mcx` | `x.ctrl(controls…, target)` | 多重控制順序與索引須核對。 |
| `cswap` | `swap.ctrl(control, a, b)` 或受控分解 | 假設，需測試驗證：CUDA-Q `swap.ctrl` 支援形式。 |
| 單位元閘的 `gate.control(n)` | 對等操作 `.ctrl(controls…, target)`；分解時每步都受控 | `sx`、`u`、`r`、`p` 不可把相位當成不重要的全域相位。 |
| `rzz` | `x.ctrl(a,b); rz(theta,b); x.ctrl(a,b)` | 精確等價；受控版所有成分都需受控。 |
| `rxx` | 兩線 `h` 變換基底；`rzz`；兩線 `h` 還原 | 精確等價；控制位元可為多個。 |
| `ryy` | 兩線以 `rx` 轉換基底；`rzz`；反向還原 | 正反轉角與受控相位須測。 |
| `barrier` | 略過，加 warning | 不作演化；不支援把它當成控制閘。 |
| `measure` | `mz`（AST 另解析 `mx`、`my`） | 非酉運算；counts 位元順序與 classical 映射另處理。 |
| `reset` | `reset` | 非酉運算；不適用受控閘的保真度斷言。 |
| `GlobalPhase`／`circuit.global_phase` | 略過，加 warning | 無法在 CUDA-Q 原始碼表達；僅忽略整體相位，不忽略控制分支相位。 |
| 未知閘 | `decompose_unknown=True` 時以支援基底 `transpile` 分解並 warning；否則報錯 | 分解要保留可控制時的相位；明列不支援建構不可用此分支繞過。 |

- 反方向 AST 辨認上述 CUDA-Q 名稱、`r1`、`u3`、`.ctrl(...)`、`.adj(...)`、`mz/mx/my`、`reset`；不是宣稱所有 API 拼法均已實測。`translate` 已知把 `r1` 轉 `rz`：物件反向路徑記 warning，受控語境若無法證明保留相對相位則報錯／標示不可保證，不得宣稱等價。
- `if_test`、`c_if`、`while_loop`、`for_loop`、`switch`、`delay`、pulse 與其他動態功能一律拒絕；`initialize`／`StatePreparation` 在 `decompose_unknown=False` 時拒絕，其餘遵守未知閘分解規則。

## 3. 位元順序與等價比較方法

- 已實測環境事實：`cudaq.get_state` 與 Qiskit `Statevector` 均為 little-endian（qubit 0 最低位），振幅直接同索引比較；`cudaq.sample` 的鍵由左到右為 qubit 0、1…，Qiskit counts key 的 qubit 0 在最右，須先轉置 qubit 對應並映射到 classical bit，再排序比較；不可只為多 creg 電路直接反轉完整含空格字串。
- 對含末端測量的電路，先取得不含末端測量的同一演化電路比較狀態；中途測量後同一 qubit 有閘時只比 counts，報告標明 `statevector_equal` 不適用；沒有測量時視為所有 qubit 末端測量。部分測量／多 creg 維持 Qiskit classical bit 順序與未測量 bit 語意。
- `fidelity = |⟨qiskit|cudaq⟩|²`：CPU ≥ `1 - 1e-6`，GPU fp32 ≥ `1 - 1e-4`，忽略整體相位；受控時用控制 `|+⟩` 比較以暴露相對相位錯誤。`TVD = 0.5 × Σ|P(k)-Q(k)|` ≤ 0.05，預設 4000 shots。
- Qiskit `Statevector.sample_counts` 或選用 `qiskit_aer`，與 CUDA-Q 取樣採固定 seed（預設 1234）；CUDA-Q seed 設定方式及跨後端重現性屬假設，需測試驗證；不以 FutureWarning 文字斷言。於 1～5 qubits、固定亂數種子的語料控制執行成本。
## 4. 實作批次與順序
- 共同先決：批次 A 即建立 `pyproject.toml` 的測試／靜態檢查設定（批次 C 再完成交付設定），`pytest` 的 `addopts` 包含 `--cov=qcconvert --cov-fail-under=90`（2026-11-21 起提高為行＋分支 100%：`[tool.coverage.run] branch = true`、`--cov-fail-under=100`，見文末更新紀錄）；mypy `strict = true`，僅對 `cudaq`、`qiskit*`、`ipywidgets`、`IPython` 允許 `ignore_missing_imports`；必要的局部型別忽略須說明原因。不新增依賴。
- A：依序建立 IR、錯誤型別、Qiskit 輸入／輸出、CUDA-Q 原始碼產生與檔案型 `load_kernel`、等價比較／執行器、API Qiskit → CUDA-Q；建立受控相位、測量、參數、位元順序等測試。尚未實作的 B／C 模組不先建空檔或佔位函式，避免覆蓋率分母膨脹；`__init__.py` 暫只匯出已完成部分。每批實際執行四項 gates 與覆蓋率，未全綠不得進下批。
- B：AST 白名單解析一個或指定的 kernel；僅接受 `float`／`list[float]` 常數索引參數、多個 `qvector(N)`／`qubit()` 依序編號；展開固定 `range` 與常數算術索引，保留 `2*theta`、`np.pi/2`、`math.pi` 等參數運算式；解析 `.ctrl/.adj` 與測量。kernel 物件走 synthesize → OpenQASM 2 → IR；確認分解、`r1`／受控相位及 round trip。補齊 `cudaq_to_qiskit`／`to_qiskit()`，再跑 gates。
- C：widgets／magics／CLI、`colab/qcconvert_demo.ipynb`、`colab/README_colab.md`、`scripts/build_dist.py`、`README.md`，最後審核 `pyproject.toml`；zip 放 `qcconvert/`、notebook、Colab 說明，排除 `.venv`、快取與測試。Colab 說明 T4 GPU／CPU 可用、切換 runtime 後重新安裝、上傳 zip；notebook GPU 檢查失敗不報錯，安裝 cell 可用 `QCCONVERT_SKIP_INSTALL=1` 跳過，非 Colab 不呼叫上傳 API；顯示版本／target、Bell／GHZ／參數電路、兩個 magics、`show()` 與可選 GPU 比較；無 GitHub 連結時徽章僅說明日後補上。明示 Qiskit 原始碼「會執行輸入的程式碼」。再跑 gates、覆蓋率及無頭 notebook。
- 每批固定執行 `.venv/bin/python -m pytest -q`、`.venv/bin/ruff check src tests scripts`、`.venv/bin/ruff format --check src tests scripts`、`.venv/bin/mypy src`；只用既有 `.venv`。測試產生檔、打包輸出、notebook 工作目錄用 `tmp_path`；正式 `load_kernel` 依 SPEC 使用系統暫存區並去重／清理，專案根／`tests/` 不留探測檔。
## 5. 測試清單（逐條對應 SPEC §5 1～14）
1. `tests/test_gates.py`（設定檢查）及 gates 指令：四項固定命令全綠，coverage ≥ 90%，全套 8 核 CPU 10 分鐘內；依實際命令輸出驗證而非僅檢查設定。
2. `tests/test_gate_mapping.py`：§3.3 各支援閘逐個 Qiskit → CUDA-Q 等價；能受控者各增 `|+⟩` 控制案例，特別查 `sx/sxdg`、`p`、`u`；非酉閘採分佈斷言，`barrier`／全域相位檢查 warnings。
3. `tests/test_cudaq_ast.py`：每個 CUDA-Q 閘名稱、`.ctrl`（單／多控制）、`.adj`、`r1/u3`、`mz/mx/my/reset` 原始碼 → Qiskit 等價；查多暫存器與固定迴圈展開、參數運算式。
4. `tests/test_corpus.py`：固定 seed 至少 200 個 1～5 qubits、深度 1～20、含參數的支援閘隨機電路，逐個前向等價；至少 50 個 round trip 等價；優先 statevector 以控制成本，不縮減樣本。
5. `tests/test_parameters.py`：`Parameter`、`ParameterVector`、運算式各至少一例，每例至少三組數值；檢查識別字、參數次序與矩陣等價。
6. `tests/test_measurements.py`：只對 qubit 0 做 `x`，counts 正規化得 `'0…01'`；GHZ、部分 qubit 測量、多 creg、無測量末端取樣、中途測量後同 qubit 有閘時僅比 counts 且報告標註。
7. `tests/test_registers.py`：多個 `QuantumRegister` 雙向轉換、名稱／範圍在可恢復時還原及等價。
8. `tests/test_errors.py`：逐類覆蓋 Qiskit `if_test/c_if/while_loop/for_loop/switch`、`initialize/StatePreparation`（`decompose_unknown=False`）、`delay`、pulse、其他動態建構，以及 CUDA-Q AST 測量條件 `if`、`while`、其他 kernel 呼叫、`exp_pauli`、`cudaq.control`、非法參數／索引；斷言 `UnsupportedFeatureError`、建構名稱及 CUDA-Q 行號；未知閘兩種分解選項也測。
9. `tests/test_qiskit_source.py`：`qc` 優先、最後指派、找不到、語法錯誤含行號；另測執行期錯誤包裝與獨立 namespace。
10. `tests/test_kernel_object.py`：至少五個 kernel 物件 → OpenQASM 2 → Qiskit 等價案例（含需 `synthesize` 的參數 kernel）、`ccx/swap` 展開與 `r1`→`rz` warning／相位風險。
11. `tests/test_widgets.py`：`ConverterApp(debounce=0)` 雙向同步、錯誤含行號無 traceback、方向切換移動文字、程式觸發按鈕；斷言 `qpp-cpu` 與 counts／fidelity／TVD 顯示。
12. `tests/test_magics.py`：用 `IPython.testing` 或 `InteractiveShell.instance()` 執行兩個 cell magic，檢查命名空間 kernel／`QuantumCircuit`、產碼與等價，包括 `--run`。
13. `tests/test_notebook.py`：`nbclient` 以 `QCCONVERT_SKIP_INSTALL=1`、`QCCONVERT_TARGET=qpp-cpu` 無頭執行 notebook，timeout 600 秒；每個 cell 無錯且有關鍵輸出。
14. `tests/test_build_dist.py`：於 `tmp_path` 執行打包並檢查 `dist/qcconvert_colab.zip` 成員、排除 `.venv`／快取／測試；解壓至 `tmp_path` 加入 `sys.path`，匯入並轉換 Bell 電路、檢查有效產碼。
- 斷言需檢查值／相位／錯誤內容／目標與鍵順序，不以「未丟例外」替代；固定 seed，避免不必要的 4000 shots × 200 筆；先確認既有環境是否有 `pytest-xdist`，若無則不加依賴、控制測試量並量測總耗時。
## 6. 假設（需測試驗證）
- 假設，需測試驗證：CUDA-Q `u3` 和 Qiskit `u/u3` 矩陣的全域相位／參數順序；`h;s;h` 對 `sx`、`h;sdg;h` 對 `sxdg` 的受控矩陣；`r` 的分解精確相位。
- 假設，需測試驗證：CUDA-Q `.ctrl` 對 `swap`、`u3`、`.adj`、多控制及 `list` 控制參數的語法；CUDA-Q `mz/mx/my` 整個暫存器的順序與 reset 的翻譯行為。
- 假設，需測試驗證：`cudaq.set_random_seed`（或同等 API）的作用範圍、GPU/CPU 的 seed 重現程度及 `cudaq.sample` 部分測量／多暫存器鍵格式；中途測量的 Qiskit 取樣能力（必要時使用已安裝的 `qiskit_aer`）。
- 假設，需測試驗證：`qiskit.qasm2.loads` 對 `r1`→`rz` round trip 在未受控情境僅差整體相位；受控時若 translate 已失去相位資訊，不得自訂未證實的補償規則。
- 假設，需測試驗證：Qiskit `transpile` 對自訂閘與受控操作在指定支援基底時保留相對相位；`ParameterVector` 與表達式轉 Python 後仍具原語意。
- 假設，需測試驗證：`load_kernel` 內容雜湊／`importlib` 快取重複載入後不因移除暫存檔破壞 `inspect`；必要時保持執行期檔案可讀並限制容量。
## 7. 待確認
- SPEC 未明確規定：受控 `r1` 在 kernel 物件經 OpenQASM 2 丟失相對相位時如何還原；保守 warning 並拒絕宣稱等價（若無法重建），不把 `rz` 當受控 `r1` 等價替換；待人確認補救策略。
- SPEC 未明確規定：中途測量後同 qubit 有閘的 Qiskit counts 參考與未測量 classical bit 填值；先明確映射且只比 counts，若 `Statevector` 不支援則採允許的 `qiskit_aer`，測試驗證。
- SPEC 未明確規定：`compare` 未給 `args` 的符號電路、GPU 覆寫但裝置不可用、`--check` 遇不可比較時的表示；保守回報 `ConversionError`／CLI 2，不虛報等價。
- SPEC 未明確規定：CLI `--to qiskit --check` 的 CUDA-Q 原始碼參考如何安全執行；遵守「CUDA-Q 原始碼 AST 不執行」已決定事項，保守拒絕檢查並回傳 2，待人確認安全參考途徑。
- SPEC 未明確規定：參數向量命名衝突清理、Qiskit 原始碼「最後指派」判準及 AST 同檔多 kernel 預設選擇；按 §3.2／§3.4 字面實作，歧義報含行號錯誤，不默默猜測。新問題只登錄本節，不更改凍結驗收範圍。

## 更新紀錄：覆蓋率門檻（2026-11-21）
- 門檻由行覆蓋率 ≥ 90% 提高為行＋分支（line + branch）覆蓋率 100%，由 `pyproject.toml` 強制（`branch = true`、`--cov-fail-under=100`）。SPEC §5 的 ≥ 90% 仍成立（100% 為更嚴格的子集）。
- 補測以真實輸入斷言可觀察結果（錯誤型別、訊息中的建構名稱與行號、輸出），僅在真正的邊界（缺少選用依賴、CUDA-Q 模擬器回傳）使用 monkeypatch。
- 無法觸及的防禦式程式碼優先刪除或重構；`# pragma: no cover` 為最後手段，須附中文理由。目前 0 個 pragma。
- 單一測試檔執行請加 `--no-cov`。
