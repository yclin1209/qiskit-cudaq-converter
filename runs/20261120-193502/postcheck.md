# 事後驗收報告（postcheck）：runs/20261120-193502

> 檢查時間：2026-11-21 02:53–02:58（Asia/Taipei，UTC+8）。只讀檢查原始碼（未改 `src/`）；另實際重跑 gates、無頭執行 notebook、打包 `dist/qcconvert_colab.zip`，並在 gates 全過後做**本機**提交（未 push）。
> Loop 於 2026-11-21 02:39:55（Asia/Taipei）因 harness `timeout` 結束（exit 124），第 6 輪審查者（reviewer）被中斷，**沒有同輪 reviewer + tester 皆 PASS 的裁決**。本報告補做驗證，不代替已被殺掉的審查。

## 1. 四項品質關卡（gates）重跑結果

皆使用 repo 內 `.venv`（Python 3.13.5、qiskit 2.6.2、cudaq 0.17.0）。無 xfail／skip。

| 關卡 | 指令 | 結果 | 耗時 |
|---|---|---|---|
| pytest | `.venv/bin/python -m pytest -q` | **300 passed**，2 則套件警告；覆蓋率（coverage）**92.30%**（門檻 90%；`TOTAL 857 / miss 66`） | pytest 自己計時 47.72 秒；牆鐘（wall）50.896 秒；exit 0 |
| ruff check | `.venv/bin/ruff check src tests scripts` | All checks passed! | 0.011 秒；exit 0 |
| ruff format | `.venv/bin/ruff format --check src tests scripts` | 26 files already formatted | 0.009 秒；exit 0 |
| mypy | `.venv/bin/mypy src` | Success: no issues found in 12 source files | 0.202 秒；exit 0 |

pytest 開始於 2026-11-21 02:54:04（Asia/Taipei）。個別檔案覆蓋率低於 90% 的有 `cudaq_ast.py` 87%、`runner.py` 88%、`widgets.py` 87%，但 SPEC 只要求整體 ≥ 90%，已達標。

## 2. 凍結驗收條件（SPEC.md §5，共 14 條）對照

目前測試中**沒有** `pytest.mark.xfail`／`skip`（第 5 輪的 5 個 strict xfail 已在第 6 輪 coder 移除）。下列「測試結果」皆包含在上述 300 passed 之內，並對第 13、14 條另做獨立實跑。

| # | 條件摘要 | 對應測試／檔案 | 有測試？ | 通過？ | xfail/skip | 判定 |
|---|---|---|---|---|---|---|
| 1 | 四項 gates 全過，覆蓋率 ≥ 90% | 本報告 §1 | 是（關卡本身） | 是 | 無 | **通過** |
| 2 | §3.3 每個支援閘各有 Qiskit→CUDA-Q 等價測試，能受控者另測受控（控制位元處於 \|+⟩） | `tests/test_gate_mapping.py`（`test_gate_matrix`，含 id/h/x/y/z/s/sdg/t/tdg/sx/sxdg/rx/ry/rz/p/u1/u/u3/u2/r/cx/cy/cz/ch/swap/crx/cry/crz/cp/cu1/ccx/cswap/mcx/rzz/rxx/ryy，各普通／受控）；`test_gate_mapping_extra.py` 再補單／多位元閘 | 是 | 是 | 無 | **通過** |
| 3 | 每個 CUDA-Q 閘名稱（含 `.ctrl`、`.adj`）各有 CUDA-Q 原始碼→Qiskit 等價測試 | `tests/test_cudaq_ast.py`：`test_gate_matrix`（h/x/y/z/s/sdg/t/tdg/rx/ry/rz/r1/u3/swap）、`test_control`、`test_adj`（s/t/rx/ry/rz/r1/u3）、別名 `cx/cy/cz/ch/cs/ct/crx/cry/crz/cr1`；`sdg.ctrl`／`tdg.ctrl`／`sdg.adj`／`tdg.adj` 有拒絕測試 | 是（主要閘有） | 已測項目通過 | 無 | **通過**（殘缺：`h/x/y/z/swap` 的 `.adj` 沒有獨立等價測試，見 §6） |
| 4 | 固定 seed 至少 200 個隨機電路全部等價；其中至少 50 個 round trip 仍等價 | `tests/test_gate_mapping_extra.py`：`test_random_corpus`（seed 4831，200 個、前 50 個再轉回） | 是 | 是 | 無 | **通過** |
| 5 | `Parameter`、`ParameterVector`、參數運算式各至少 1 個；至少 3 組數值帶入後等價 | `test_parameters`（`theta + v[0]` 運算式與向量，3 組數值）；另有 `test_regressions.py` 參數簽章／命名衝突測試 | 是 | 是 | 無 | **通過** |
| 6 | 位元順序；GHZ、部分 qubit 測量、多 creg 分佈等價。中途測量（mid-circuit measurement）依 §3.5 只比分佈 | 位元順序 `test_bit_order`（只在 qubit 0 做 `x` → `'001'`）；GHZ `test_ghz_distribution`；部分測量＋多 qreg/creg `test_measurements_and_warnings`、`test_partial_multiple_cregs_distribution`；中途測量 `test_mid_measurement` 與 `test_regressions.py` 553 行起（跨 qubit、重複測量、reset、覆寫同一 clbit、CLI／widget） | 是 | 所列測試皆過 | 無 | **通過**（殘缺：中途測量＋多 creg 未覆蓋，且實測 TVD=1.0，見 §6 發現 1） |
| 7 | 多 `QuantumRegister` 兩個方向都能轉換且等價 | 前向：`test_measurements_and_warnings`；反向名稱：`test_reverse_register_names`；反向等價：`test_loop_registers_and_parameters` | 是 | 是 | 無 | **通過** |
| 8 | §3.3／§3.4 每一類不支援建構丟出 `UnsupportedFeatureError`，訊息含建構名稱；CUDA-Q 錯誤含行號 | `tests/test_errors.py`（if_test、c_if、while_loop、for_loop、switch、initialize、StatePreparation、delay、pulse）；`tests/test_cudaq_errors.py`（If／While／其他 kernel／exp_pauli／cudaq.control 等，斷言行號） | 是 | 是 | 無 | **通過** |
| 9 | Qiskit 原始碼：`qc` 優先、最後一個電路、找不到、語法錯誤（含行號） | `test_source_selection`；執行錯誤行號另見 `test_errors_and_decomposition` | 是 | 是 | 無 | **通過** |
| 10 | kernel 物件→Qiskit（經 OpenQASM 2）至少 5 個，含有參數（`synthesize`） | `tests/test_kernel_object.py`：`test_object` 參數化 h／x／swap／r1／rx（`theta`）；另有受控 r1 警告測試 | 是（5+1） | 是 | 無 | **通過** |
| 11 | `ConverterApp`：兩方向即時轉換、錯誤顯示、方向切換、執行按鈕（`qpp-cpu`）以程式觸發並斷言輸出 | `tests/test_widgets.py`（`test_live_direction_and_errors`、`test_run_button`）；回歸：`test_widget_round_trip_status`、`test_widget_reverse_run_button`、`test_mid_measurement_widget` | 是 | 是 | 無 | **通過** |
| 12 | 兩個 cell magic，命名空間出現 kernel／`QuantumCircuit` 且結果等價 | `tests/test_magics.py`：`test_cell_magics`（`InteractiveShell.instance()`）；另 `test_magic_reverse_printed_code_executable` | 是 | 是 | 無 | **通過** |
| 13 | Notebook 以 `nbclient` 無頭執行（`QCCONVERT_SKIP_INSTALL=1`、`QCCONVERT_TARGET=qpp-cpu`，逾時 600 秒），由 `tests/test_notebook.py` 執行 | `tests/test_notebook.py`（已在 300 passed 內）；本報告另獨立實跑，見 §3 | 是 | 是 | 無 | **通過** |
| 14 | `scripts/build_dist.py` → `dist/qcconvert_colab.zip`；測試檢查 zip；解壓後 `sys.path` 能 `import qcconvert` 並轉換 Bell | `tests/test_build_dist.py`：`test_archive`（寫入 `tmp_path`）；本報告另寫入真正的 `dist/`，並加測參數化電路，見 §4 | 是 | 是 | 無 | **通過** |

**總評**：14 條在「已寫測試是否通過」意義上皆可算通過，且 gates 全綠。但因第 6 輪沒有審查／測試裁決，加上 §6 發現的中途測量缺陷，**不能聲稱 loop 已正式驗收通過（accepted）**。

## 3. Notebook 無頭（headless）執行

環境變數：`QCCONVERT_SKIP_INSTALL=1`、`QCCONVERT_TARGET=qpp-cpu`。以 `nbclient.NotebookClient(..., timeout=600)` 執行 `colab/qcconvert_demo.ipynb`。

- 結果：`notebook_ok=True`，全部 cell 無錯誤。
- 耗時：約 2.003 秒（牆鐘 2.264 秒），2026-11-21 02:55:45（Asia/Taipei）。
- 斷言：輸出含 `qpp-cpu`、`跳過安裝`、`fidelity`、`雙欄編輯器`。
- 重點輸出：GPU 檢查印「沒有可用 GPU，改用 CPU」；安裝 cell 印「跳過安裝（skip installation）」；環境為 cudaq 0.17.0、qiskit 2.6.2、target `qpp-cpu`；Bell／GHZ／參數化電路有轉換碼與 `compare`；`%%qiskit2cudaq --run` 印出 `target: qpp-cpu; fidelity: 0.9999999999999996; TVD: 0.008750`；`%%cudaq2qiskit` 產生可執行 Qiskit 碼；`qcconvert.show()` 印「雙欄編輯器已預填 Bell 範例」；無 GPU，跳過 21-qubit 加速比較。

## 4. Zip 打包與隔離匯入

- 指令：`.venv/bin/python scripts/build_dist.py dist`（0.044 秒）。
- 路徑：`/workspace/qiskit-cudaq-converter/dist/qcconvert_colab.zip`（22163 bytes）。
- 內容（14 個項目，無 `.venv`／快取／測試）：

```
qcconvert/__init__.py
qcconvert/__main__.py
qcconvert/api.py
qcconvert/cudaq_ast.py
qcconvert/cudaq_io.py
qcconvert/equivalence.py
qcconvert/errors.py
qcconvert/ir.py
qcconvert/magics.py
qcconvert/qiskit_io.py
qcconvert/runner.py
qcconvert/widgets.py
qcconvert_demo.ipynb
README_colab.md
```

- 隔離測試：解壓到暫存目錄 `/tmp/qcconvert_zipcheck_*`，從 `sys.path` 移除 repo 的 `src/`，只加入解壓目錄後 `import qcconvert`（實際載入路徑為該暫存目錄下的套件）。`QCCONVERT_TARGET=qpp-cpu`，shots=4000、seed=1234：
  - Bell（`h(0); cx(0,1)`）：fidelity ≈ 1.0（0.9999999999999996），`statevector_equal=True`，TVD ≈ 0.00875；counts Qiskit `{'00': 1966, '11': 2034}`、CUDA-Q `{'00': 2001, '11': 1999}`。
  - 參數化 `ry(theta)`、`theta=0.3`（綁定電路與 `args=(0.3,)` 兩種呼叫）：fidelity ≈ 1.0，`statevector_equal=True`，TVD = 0.004。
- 結論：`ZIP_IMPORT_OK`。

## 5. 第 6 輪差分與獨立審查（不修改程式）

上一筆 git 提交仍是 `4afd9e1`（只含 SPEC／harness／代理設定），因此工作區相對於該提交幾乎是整份實作。第 6 輪 coder（01:27:08–02:13:51，Asia/Taipei）實際改動的檔案與 mtime 為：

- `tests/test_regressions.py`（01:43）
- `src/qcconvert/runner.py`（01:43）
- `src/qcconvert/__main__.py`、`src/qcconvert/widgets.py`（02:12）

Coder 聲稱：以 `cudaq.run` 取得逐次（per-shot）中途測量、拿掉 5 個 xfail、補回歸測試、gates 300 passed／92.30%。與本報告重跑一致。以下是被中斷的 reviewer 應會標出的明顯問題（**只列發現，未修復**）：

1. **中途測量 + 多個古典暫存器（ClassicalRegister）時 TVD 虛報為 1.0**（阻擋級）。`runner.py:198-206` 用 `AerSimulator().run(...).result().get_counts()` 當 Qiskit 參考，多 creg 的鍵會帶空白（例如 `'0 1'`）；同檔 `runner.py:72-76` 的 `_mid_counts` 卻組出連續位元字串（例如 `'01'`）。本機以雙 creg、中途測量電路實測：`qiskit_counts={'0 1': 136, '1 0': 120}`、`cudaq_counts={'01': 137, '10': 119}`，**TVD = 1.0**（分佈其實接近）。現有多 creg 測試都是末端測量，沒蓋到這條路徑。違反 §5 第 6 條「多 creg 的分佈等價」在中途測量情境下的精神。
2. **中途測量硬依賴 `qiskit_aer`，但 Colab 安裝與套件依賴未列入**。`runner.py:199` 無條件 `from qiskit_aer import AerSimulator`，沒有「有安裝才用」的退路。`pyproject.toml` 依賴只有 `qiskit`、`cudaq`、`numpy`；notebook 安裝 cell 與 `colab/README_colab.md` 只裝 `cudaq qiskit ipywidgets`。在未預裝 Aer 的 Colab 上，對中途測量按「在 CUDA-Q 執行並對照」會 `ImportError`。SPEC §4 寫的是「`Statevector.sample_counts` 或 `qiskit_aer`（有安裝時）」。
3. **`_mid_counts` 只改寫敘述句裡的裸 `mz(...)`**（`runner.py:39-50`）。產生的前向程式碼確實是 `mz(q[0])`，故現有測試能過；但已賦值的測量、`cudaq.mz`、`mx`／`my` 會走到「測量數與 Qiskit 電路不一致」。
4. **`import qcconvert` 必依賴 ipywidgets**。`src/qcconvert/__init__.py:9` Eager import `from .widgets import show`，核心轉換 API 無法在沒有 ipywidgets 的環境匯入。Colab 若依序跑安裝 cell 則沒問題；`pyproject.toml` 未宣告此依賴。
5. **§5 第 3 條覆蓋缺口（非阻擋）**：`tests/test_cudaq_ast.py` 沒有 `h.adj`／`x.adj`／`y.adj`／`z.adj`／`swap.adj` 的等價測試（`sdg`／`tdg` 修飾語已正確拒絕）。

其餘第 6 輪相關改動看起來對症：CLI（`__main__.py:36-39`）與 widget 執行按鈕（`widgets.py:106-110`）把比較錯誤收成 exit 2／狀態列、不漏 traceback；中途測量報告會設 `distribution_only`；產生的 kernel 用陳述句 `mz(...)`，與擷取邏輯相符。

## 6. 時長、輪次、token／費用、停滯（stall）

### 迴圈時長與結束方式

| 項目 | 值 |
|---|---|
| 開始 | 2026-11-20 19:35:03（Asia/Taipei） |
| 結束 | 2026-11-21 02:39:55（Asia/Taipei） |
| 牆鐘 | 25491992 ms（7 小時 4 分 52 秒） |
| exit | 124（harness `timeout`） |
| 裁決 | 無同輪 reviewer+tester PASS |

### 輪次

| 輪 | reviewer | tester | 備註（摘自 loop-log／summary） |
|---|---|---|---|
| 1 | FAIL（§5 #3、#6） | FAIL（§5 #3、#5、#6、#8）；206 passed／4 xfailed，cov 91.60% | |
| 2 | FAIL（§5 #3、#11） | FAIL（§5 #3、#11）；239 passed／10 xfailed，cov 91.93% | |
| 3 | **PASS**（聲稱 14 條全過） | FAIL（§5 #11 反向參數名衝突）；274 passed／4 xfailed，cov 92.59% | |
| 4 | FAIL（阻擋：compare 參數綁定與測量狀態向量） | **PASS**（但以 2 個 strict xfail 重現 reviewer 問題）；289 passed／2 xfailed，cov 92.70% | |
| 5 | FAIL（§5 #6 多 qubit 中途測量 IndexError） | FAIL（§5 #6，另 5 個 strict xfail）；293 passed／5 xfailed，cov 92.44% | |
| 6 | **被殺掉（無裁決）** | 未跑 | coder 完成並聲稱 300 passed、cov 92.30%；接著的 reviewer 在 02:38:58 出現 Idle timeout，harness 於 02:39:55 結束 |

Subagent 步驟共 20 筆（planner×1、coder×10、reviewer×5 完成 + 第 6 輪 reviewer 未寫入 steps、tester×5）。第 6 輪 reviewer session 為 `ses_e05d5b069ffetSr9oTk1Fslrej`，未輸出到 `sessions/`（未完成 export）。

### Token 與費用

`opencode stats` 的 Total Cost 為 **$0.00**（OmniRoute 未把帳務回寫進 opencode）。本 run 較精確的數字是 `summary.md` 對 20 個已匯出 session 的加總（不含被中斷的第 6 輪 reviewer）：

| 來源 | input | output | reasoning | cache read | cache write | 報價 |
|---|---|---|---|---|---|---|
| session export（20 個 session） | 874,772 | 214,714 | 14,902 | 17,837,210 | 0 | $0.0000 |
| `stats_after` − `stats_before`（全域差值，含未匯出 session） | 約 +894.4K（973.3K−78.9K） | 約 +221.2K（286.5K−65.3K） | — | 約 +18.0M（19.4M−1.4M） | 0 | $0.00 |

依角色（session export）：

| 角色（模型） | input | output | reasoning | cache read |
|---|---|---|---|---|
| coder（cx/gpt-6-sol） | 345,660 | 60,307 | 7,559 | 7,967,232 |
| tester（cx/gpt-6-sol） | 251,478 | 23,505 | 6,491 | 4,347,264 |
| reviewer（cc/claude-opus-5-5） | 214,402 | 95,237 | 0 | 4,050,694 |
| planner（cx/gpt-6-sol） | 21,872 | 9,782 | 852 | 114,176 |
| orchestrator（cc/claude-opus-5-5） | 41,360 | 25,883 | 0 | 1,357,844 |

### 停滯次數

此 run 目錄**沒有** `STALL_KILLED`；監看（watch.py）**沒有**因停滯殺掉迴圈。`opencode.log` 在本 run 時窗（19:35–02:40，Asia/Taipei）內，屬於本 run session 的提供者錯誤共 **13 次**（**0 次 HTTP 429**）：

- `stream content stall`：**3**
- `[STREAM] Idle timeout`：**10**

明細（時間皆為 Asia/Taipei）：

| 時間 | 類型 | session／角色 |
|---|---|---|
| 11-20 20:47:04 | stream stall（300000ms） | reviewer `ses_e07143318…`（約第 2 輪，後來仍完成 FAIL） |
| 11-20 21:27:34、21:40:24 | idle timeout（600000ms） | coder `ses_e06e832b6…`（第 3 輪 coder，後來完成） |
| 11-20 22:03:52 | stream stall | reviewer `ses_e06ccbe38…`（第 3 輪，後來 PASS） |
| 11-20 22:51:20 | idle timeout | coder `ses_e069dc805…`（第 4 輪 coder） |
| 11-20 23:06:53、23:21:37 | idle timeout | reviewer `ses_e068de8fe…`（第 4 輪，後來 FAIL） |
| 11-20 23:40:38 | idle timeout | tester `ses_e06721c38…`（第 4 輪 tester PASS） |
| 11-21 00:11:28 | idle timeout | coder `ses_e06507e75…`（第 5 輪 coder） |
| 11-21 01:09:10 | stream stall | tester `ses_e06290ed7…`（第 5 輪 tester） |
| 11-21 01:24:57 | idle timeout | 同上 tester |
| 11-21 02:12:13 | idle timeout | coder `ses_e060093ce…`（第 6 輪 coder，後來完成） |
| 11-21 02:38:58 | idle timeout | reviewer `ses_e05d5b069…`（第 6 輪，隨即 harness 逾時） |

這些多數是 session 內部重試後仍跑完；真正結束迴圈的是 harness 牆鐘逾時，不是 stall watcher。

## 7. 本機提交

Gates 全過後，將目前工作樹做本機 `git add -A`（尊重 `.gitignore`：不含 `.venv/`、快取、`.coverage`、`runs/*/sessions/`；`dist/` 未在 gitignore，zip 一併納入）並提交，**沒有 push**。訊息：

`round 6 coder output + final gates (loop timed out before verdict)`

提交雜湊（hash）見提交當時的 `git log -1`（本檔寫入後一併納入該提交）。

## 8. 支援與不支援範圍（摘自 README／SPEC）

**支援**

- 兩個方向的電路層級轉換：Qiskit `QuantumCircuit` 或原始碼 ⇄ CUDA-Q `@cudaq.kernel` 原始碼／kernel 物件。
- 閘：`h/x/y/z/s/t/sx` 及其反閘、旋轉與相位閘、`u`／`u3`／`u1`／`u2`／`r`、受控閘、`swap`／`ccx`／`cswap`／`mcx`、`rxx`／`ryy`／`rzz`、測量與重置；常數迴圈、浮點參數、基本算術表示式、多量子暫存器。
- 等價比較：狀態向量 fidelity（`qpp-cpu` ≥ 1−1e-6，GPU fp32 ≥ 1−1e-4）、取樣 TVD ≤ 0.05；有 GPU 用 `nvidia`，否則 `qpp-cpu`，可用 `QCCONVERT_TARGET` 覆寫。
- UX：雙欄編輯器、cell magic、CLI、Colab notebook。

**不支援／已知限制**

- Qiskit：經典條件控制（`if_test`、`c_if`、迴圈、`switch`）、`delay`、脈衝（pulse）、`initialize`／`StatePreparation`（`decompose_unknown=False` 時）。
- CUDA-Q 原始碼只接受指定 AST 子集；不支援依測量結果分支、`while`、呼叫其他 kernel、`exp_pauli`、`cudaq.control`。實測 `sdg.ctrl`／`tdg.ctrl`／`sdg.adj`／`tdg.adj` 無法編譯，AST 會拒絕。
- 範圍外：`observe`、Hamiltonian、雜訊模型、C++（`nvq++`）、OpenQASM 3 輸入、真實硬體、多 GPU（`mgpu`）。
- Kernel 物件經 OpenQASM 2 回轉時，`r1` 可能變成 `rz`，受控相對相位不保證等價；請優先走原始碼 AST。全域相位在前向轉換會略過並警告。
- Qiskit 原始碼輸入**會執行輸入的程式碼**；CUDA-Q 原始碼只做靜態解析。CLI `--to qiskit --check` 不執行不可信原始碼，回傳 2。
- 中途測量只比較分佈；若無法從 kernel 原始碼重建測量前演化，狀態向量指標為 `None`。

## 9. Colab 使用步驟（依 notebook／`README_colab.md` 實作）

1. 在 Colab 選 **Runtime → Change runtime type → T4 GPU**（CPU 也可，會用 `qpp-cpu`）。若先在 CPU runtime 安裝、之後才切 GPU，須重新安裝 CUDA-Q（安裝時依 CUDA 版本選 cu12／cu13）。
2. 在本機執行 `python scripts/build_dist.py`，把 `dist/qcconvert_colab.zip` 上傳到 Colab 的 `/content/`（或開 notebook 後在安裝 cell 依提示用 `google.colab.files.upload()`）。
3. 開啟 zip 內（或 repo 的）`qcconvert_demo.ipynb`，先跑 GPU 檢查與**安裝 cell**（`pip install cudaq qiskit ipywidgets`，解壓 zip 並加入 `sys.path`，在 Colab 啟用 widget manager）。本機／CI 可設 `QCCONVERT_SKIP_INSTALL=1` 跳過安裝。
4. 依序跑範例：API（Bell／GHZ／參數化電路與 `compare`）、`%load_ext qcconvert` 後用 `%%qiskit2cudaq --run` 或 `%%cudaq2qiskit`，以及 `qcconvert.show()` 雙欄編輯器。有 GPU 時可跑選用的 21-qubit GHZ 耗時比較。

注意：安裝 cell 目前**沒有**安裝 `qiskit-aer`；遇到中途測量並按執行對照時，可能因 §6 發現 2 而出錯。

## 10. 修正紀錄（2026-11-21，Asia/Taipei，UTC+8）

針對 §5 的 5 項發現，各自**先寫會失敗的回歸測試（regression test）**、確認在舊程式上失敗，再修正。新測試集中在 `tests/test_postcheck_fixes.py`（19 個）。`.venv` 原本就已安裝 `qiskit-aer` 0.18.4 與 `ipywidgets` 8.1.9，未另外安裝任何套件。

| # | 發現 | 修正（檔案:行） | 回歸測試 |
|---|---|---|---|
| 1 | 中途測量 + 多 creg 時 Aer 的鍵帶空白（`'0 1'`），與 `_mid_counts` 的 `'01'` 對不上，TVD 虛報 1.0 | 新增 `_normalize_qiskit_counts`（`runner.py:145`）：依 `circuit.cregs` 與 `find_bit` 把各 creg 片段放回全域 clbit 索引，輸出最高位在左的連續字串（Qiskit 順序），兩邊格式一致。另發現由 CUDA-Q 原始碼轉回的電路含自訂受控閘，Aer 會報 `unknown instruction`，故 `_aer_counts`（`runner.py:167-180`）先 `transpile(..., optimization_level=0)` | `test_mid_measurement_multiple_cregs_distribution`、`test_mid_measurement_uneven_cregs_bit_order`（2+1 位元 creg，確定性結果 `'010'`）、`test_normalize_qiskit_counts_helper` |
| 2 | 硬依賴 `qiskit_aer`，Colab 未安裝 | `_aer_counts` 缺 Aer 時丟出 `ConversionError`，訊息提示 `pip install qiskit-aer`（`runner.py:169-175`）；`pyproject.toml:5` 依賴加入 `qiskit-aer`；notebook 安裝 cell 改為 `pip install cudaq qiskit qiskit-aer ipywidgets`；`colab/README_colab.md:5`、`README.md` 新增「安裝（installation）」一節 | `test_mid_measurement_without_aer_gives_clear_error`（`sys.modules['qiskit_aer']=None`，非中途測量電路仍可比較）、`test_install_instructions_list_qiskit_aer` |
| 3 | `import qcconvert` 必須有 ipywidgets | `__init__.py:15-30`：`show()`、`load_ipython_extension()` 改為呼叫時才匯入 `widgets`／`magics`；缺 ipywidgets 時 `show()` 丟出提示安裝的 `ImportError`。`pyproject.toml:8-9` 新增選用依賴 `colab = ["ipywidgets", "ipython"]` | `test_import_without_ipywidgets`（子行程封鎖 ipywidgets，`qiskit_to_cudaq` 可用且未載入 `qcconvert.widgets`）、`test_lazy_show_and_extension_still_work` |
| 4 | `_mid_counts` 只認裸敘述 `mz(...)` | 抽出 `_capture_measurements`（`runner.py:44-109`）：擷取頂層 `mz/mx/my(q[i])` 敘述與 `r = mz(q[i])` 賦值（改寫成暫存變數再指回 `r`）；其他任何測量寫法（`cudaq.mz`、整個暫存器 `mz(q)`、迴圈內測量、tuple 賦值）丟出含 kernel 原始碼行號的 `UnsupportedFeatureError`（`runner.py:91-97`）。註：`cudaq.mz` 在 CUDA-Q 0.17 kernel 內本身無法編譯；實測 `mx` 等同 H 後 Z 測量且不轉回，與 Qiskit 端 `h + measure` 一致 | `test_mid_capture_assigned_measurement`、`test_mid_capture_mx_my[mx/my]`、`test_mid_capture_unsupported_forms`（4 種） |
| 5 | `h/x/y/z/swap` 的 `.adj` 沒有等價測試 | 實測 CUDA-Q 0.17 **無法編譯**這些寫法（`h/x/y/z.adj`：`'quake.h' op may not be adjoint`；`swap.adj`：`unknown function call`），所以無法做等價測試。改為測試「CUDA-Q 確實編譯失敗」且轉換器拒絕時訊息含行號與「自反閘，請直接寫 `h(...)`」提示（`cudaq_ast.py:198-201`）；README 支援範圍同步註明 | `test_self_inverse_adj[h/x/y/z/swap]` |

### 修正後驗證

| 項目 | 結果 |
|---|---|
| pytest | **319 passed**（原 300 + 新 19），覆蓋率（coverage）**93.23%** |
| ruff check／ruff format --check／mypy | All checks passed／27 files already formatted／Success（12 source files） |
| Notebook 無頭執行（`QCCONVERT_SKIP_INSTALL=1 QCCONVERT_TARGET=qpp-cpu`，`tests/test_notebook.py`） | 1 passed |
| `dist/qcconvert_colab.zip` | 重新打包，24,024 bytes，14 個檔案（`qcconvert/*.py` 12 個、`qcconvert_demo.ipynb`、`README_colab.md`） |
| 隔離目錄匯入（解壓到 `mktemp -d`，`PYTHONPATH` 指向該目錄） | `qcconvert` 從暫存目錄載入；3 qubit、creg `a`(1)+`b`(2) 的中途測量電路：Qiskit `{'000': 970, '011': 990, '100': 1010, '111': 1030}`、CUDA-Q `{'000': 1016, '011': 1031, '100': 953, '111': 1000}`，**TVD = 0.0218**（≤ 0.05），`distribution_only=True`、`statevector_equal=None`（中途測量依設計只比分佈） |

仍未解決：中途測量的 Qiskit 參考仍需 `qiskit-aer`（沒有純 `Statevector` 的退路）；`cudaq_ast` 仍不接受 `r = mz(...)` 賦值形式的 CUDA-Q 原始碼轉 Qiskit（只有 `compare` 的擷取支援）；本次修正未經 loop 的 reviewer／tester 複審。
