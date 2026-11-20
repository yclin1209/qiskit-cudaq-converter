# 開發過程（process）

本文記錄 qcconvert（Qiskit ⇄ CUDA-Q 即時電路轉換器）的多代理開發過程與結果。數字皆來自 `runs/20261120-193502/postcheck.md`、`loop-log.md`、`timing.txt`、`summary.md` 與本機 `git log`，沒有另行推估費用。時間皆為 Asia/Taipei（UTC+8）。

## 1. 目標（goal）

在本機以 opencode 多代理迴圈（multi-agent loop）開發一套可在 Colab 方便使用的雙向轉換器：Qiskit 電路（物件或原始碼）轉成可執行的 CUDA-Q `@cudaq.kernel`，也能從 CUDA-Q kernel／原始碼轉回 Qiskit。需求凍結於 `specs/SPEC.md`（14 條驗收條件），計畫見 `docs/plan.md`。交付物包含 `qcconvert` 套件、等價測試（狀態向量 fidelity 與抽樣 TVD）、ipywidgets 雙欄即時編輯器、cell magic、`colab/qcconvert_demo.ipynb`，以及 `dist/qcconvert_colab.zip`。開發期間程式碼只做本機 git 提交，不推送到遠端；本文對應的提交起，才把過程與結果放到 GitHub 的 private repo。

## 2. 多代理設定（multi-agent setup）

迴圈由 `harness/drive.sh` 驅動，透過 OmniRoute 呼叫模型（opencode provider 名稱為 `omniroute`）。本機 `runs/versions.txt` 紀錄：opencode 1.19.5、omniroute 3.8.52。

實際跑完主要迴圈（`runs/20261120-193502`）時的角色，依提交 `4afd9e1` 與 `.opencode/agent/*.md`、`opencode.json`：

| 角色 | 模型 |
|---|---|
| 規劃者（planner） | `cx/gpt-6-sol` |
| 實作者（coder） | `cx/gpt-6-sol` |
| 測試者（tester） | `cx/gpt-6-sol` |
| 審查者（reviewer） | `cc/claude-opus-5-5` |
| 總控（orchestrator） | `cc/claude-opus-5-5` |
| 小模型（small_model，標題等） | `cc/claude-haiku-5-5` |

流程是 planner 寫計畫 → coder 實作 → 同輪 reviewer 與 tester 分別裁決；兩邊都 `VERDICT: PASS` 才結束，最多 8 輪。金鑰只在執行時從 `~/.omniroute` 讀入環境變數，不寫進 repo。

## 3. 第一次迴圈：planner 停滯後重開

在主要迴圈之前，有兩次未完成的啟動：

- `runs/ABORTED-20261120-175517-old-roles`：2026-11-20 17:55:18–17:56:58，exit 143，牆鐘 100,364 ms。`summary.md` 沒有子代理步驟，只匯出總控 session 一小段（input 313、output 109）。
- `runs/ABORTED-20261120-175733-planner-stall`：2026-11-20 17:57:34–19:33:21，exit `killed-manually`，目錄內有空的 `STALL_KILLED`。當時角色仍是提交 `d453b95` 的配置（規劃／審查用 Claude，實作／測試用 OpenAI），規劃者為 `cc/claude-opus-5-5`。`runs/driver.log` 19:33:21 記載：手動停止此次 run，原因是 planner `cc/claude-opus-5-5` 發生 `stream content stall` 共 4 次，沒有產出程式碼。

接著在 19:34:51 提交 `4afd9e1`：規劃者改為 `cx/gpt-6-sol`，並加入防串流停滯規則與 `harness/watch.py`。該監看以 `opencode.db` 的 session 活動為準，並統計 `opencode.log` 裡的 `stream content stall`／`Idle timeout`；`harness/drive.sh` 在停滯被殺掉時會自動續跑一次，第二次停滯就停下來交給人。隨即重開主要迴圈。

## 4. 主要迴圈：`runs/20261120-193502`

| 項目 | 值（來源：`timing.txt`／`postcheck.md` §6） |
|---|---|
| 開始 | 2026-11-20 19:35:03 |
| 結束 | 2026-11-21 02:39:55 |
| 牆鐘 | 25,491,992 ms（7 小時 4 分 52 秒，約 7 小時 5 分） |
| 結束方式 | harness `timeout`，exit 124 |
| 裁決 | 沒有同輪 reviewer + tester 皆 PASS |

第 6 輪審查者在 02:38:58 出現 Idle timeout，harness 於 02:39:55 結束，審查被中斷，測試者未跑。此 run 目錄沒有 `STALL_KILLED`，`watch.py` 沒有因停滯殺掉迴圈。

### 各輪裁決（`loop-log.md`、`postcheck.md` §6）

| 輪 | reviewer | tester | tester 實跑 gates |
|---|---|---|---|
| 1 | FAIL（§5 第 3、6 條） | FAIL（§5 第 3、5、6、8 條） | 206 passed／4 xfailed，覆蓋率 91.60% |
| 2 | FAIL（§5 第 3、11 條） | FAIL（§5 第 3、11 條） | 239 passed／10 xfailed，覆蓋率 91.93% |
| 3 | PASS（聲稱 14 條全過） | FAIL（§5 第 11 條：反向參數名衝突） | 274 passed／4 xfailed，覆蓋率 92.59% |
| 4 | FAIL（阻擋：`compare` 參數綁定與測量狀態向量） | PASS（但以 2 個 strict xfail 重現 reviewer 問題） | 289 passed／2 xfailed，覆蓋率 92.70% |
| 5 | FAIL（§5 第 6 條：多 qubit 中途測量 IndexError） | FAIL（§5 第 6 條，另 5 個 strict xfail） | 293 passed／5 xfailed，覆蓋率 92.44% |
| 6 | 被殺掉（無裁決） | 未跑 | coder 完成並聲稱 300 passed、覆蓋率 92.30%；隨後 reviewer 被逾時中斷 |

`summary.md` 記錄已完成的子代理步驟共 20 筆（planner × 1、coder × 10、reviewer × 5 完成、tester × 5）。第 6 輪 reviewer session 未寫入 `steps/`、也未匯出到 `sessions/`。

### 提供者停滯（stall）

`postcheck.md` 依 `opencode.log` 統計，本 run 時窗（19:35–02:40）內屬於本 run session 的提供者錯誤共 **13 次**，其中 `stream content stall` 3 次、`[STREAM] Idle timeout` 10 次，**HTTP 429 為 0 次**。多數是 session 內部重試後仍跑完；真正結束迴圈的是 harness 牆鐘逾時。明細見 `postcheck.md` §6 表格。

### Token 與費用

OmniRoute 未把帳務回寫進 opencode，`opencode stats` 的 Total Cost 為 **$0.00**，因此**沒有可報告的實際花費**。較精確的數字是 `summary.md` 對 20 個已匯出 session 的加總（**不含**被中斷的第 6 輪 reviewer）：

| 來源 | input | output | reasoning | cache read | cache write | 報價 |
|---|---|---|---|---|---|---|
| session export（20 個 session） | 874,772 | 214,714 | 14,902 | 17,837,210 | 0 | $0.0000 |
| `stats_after` − `stats_before`（全域差值，含未匯出 session） | 約 +894.4K（973.3K−78.9K） | 約 +221.2K（286.5K−65.3K） | — | 約 +18.0M（19.4M−1.4M） | 0 | $0.00 |

依角色（session export）：

| 角色（模型） | input | output | reasoning | cache read |
|---|---|---|---|---|
| coder（`cx/gpt-6-sol`） | 345,660 | 60,307 | 7,559 | 7,967,232 |
| tester（`cx/gpt-6-sol`） | 251,478 | 23,505 | 6,491 | 4,347,264 |
| reviewer（`cc/claude-opus-5-5`） | 214,402 | 95,237 | 0 | 4,050,694 |
| planner（`cx/gpt-6-sol`） | 21,872 | 9,782 | 852 | 114,176 |
| orchestrator（`cc/claude-opus-5-5`） | 41,360 | 25,883 | 0 | 1,357,844 |

## 5. 迴圈結束後的驗收與修正

### 5.1 事後驗收（postcheck）

2026-11-21 02:53–02:58 補做只讀檢查，並重跑 gates、無頭執行 notebook、打包 zip。當時提交為 `2d794f4`（`round 6 coder output + final gates (loop timed out before verdict)`，03:00:05）。結果：pytest **300 passed**、覆蓋率 **92.30%**（當時門檻 90%），ruff 與 mypy 通過；14 條驗收條件在「已寫測試是否通過」意義上皆通過，notebook 與 zip 隔離匯入也通過。但因第 6 輪沒有審查／測試裁決，且審查補看發現缺陷，**不能聲稱 loop 已正式驗收通過**。完整對照見 `runs/20261120-193502/postcheck.md`。

### 5.2 修正提交 `8b677f4`（2026-11-21 03:18:49）

針對 postcheck 的 5 項發現，各自先寫會失敗的回歸測試、確認在舊程式上失敗，再修正（新測試 19 個，集中在 `tests/test_postcheck_fixes.py`）：

1. 中途測量加上多個古典暫存器（ClassicalRegister）時，Qiskit counts 鍵帶空白、與 CUDA-Q 連續字串對不上，TVD 虛報 1.0；並先 transpile 再交給 Aer，避免自訂受控閘造成 `unknown instruction`。
2. 中途測量硬依賴 `qiskit-aer`，但 Colab 安裝與套件依賴未列入；改為缺套件時明確報錯，並寫入 `pyproject.toml` 與安裝 cell。
3. `import qcconvert` 不再急載入 ipywidgets；`show()` 與 cell magic 改為呼叫時才匯入。
4. 測量擷取支援頂層 `mz/mx/my(q[i])` 與 `r = mz(q[i])`；其他寫法丟出含行號的 `UnsupportedFeatureError`。
5. `h/x/y/z/swap` 的 `.adj`：CUDA-Q 0.17 本身無法編譯這些寫法，改為測試轉換器清楚拒絕並提示改寫成自反閘本身。

修正後：pytest **319 passed**、覆蓋率 **93.23%**；ruff／mypy 通過；notebook 無頭執行通過；zip 重新打包為 24,024 bytes。隔離測試中，帶兩個 creg 的 3 qubit 中途測量電路 TVD = 0.0218（≤ 0.05）。

### 5.3 覆蓋率提交 `581ae36`（2026-11-21 03:57:27）

把門檻提高到「行 + 分支（line + branch）100%」（`pyproject.toml`：`branch = true`、`--cov-fail-under=100`），新增 66 個行為測試（319 → **385 passed**），`# pragma: no cover` 為 0。起點（含分支）為 91.17%（62 行未執行、50 個分支只走一邊）；終點為行 100%、分支 100%（922 行、352 個分支，0 遺漏）。

順手修正 3 個 bug：

1. 參數運算式含 `sin` 等函式時，產生的 CUDA-Q kernel 編譯失敗；改寫成 `np.*`，不支援的 `abs/sign/conj` 則明確拒絕。
2. 雙欄編輯器在 debounce 期間切換方向會丟掉剛輸入的程式碼；改為先用原方向完成待處理的轉換再切換。
3. Qiskit 原始碼產生器遇到非 `pi` 屬性會產出無法執行的程式；改為丟 `ConversionError`。

並刪除或重構不可達程式碼。驗證：385 passed（100.00%，59.8 秒），ruff／mypy 通過，notebook 無頭執行通過，`dist/qcconvert_colab.zip` 24,949 bytes、14 個檔案；隔離匯入後 Bell 與 `rx(sin(t))`（t = 0.4）的 fidelity 均為 1.0。

## 6. 本機提交一覽

| 提交 | 時間（UTC+8） | 說明 |
|---|---|---|
| `41ec7c3` | 2026-11-20 17:13:58 | 初始化：SPEC、AGENTS、代理設定與 harness |
| `d453b95` | 2026-11-20 17:57:17 | 角色調整：Claude 規劃／審查，OpenAI 實作／測試 |
| `4afd9e1` | 2026-11-20 19:34:51 | planner 改用 `gpt-6-sol`；加入防停滯規則與 `watch.py` |
| `2d794f4` | 2026-11-21 03:00:05 | 第 6 輪 coder 產出 + 最終 gates（迴圈逾時，尚無裁決） |
| `8b677f4` | 2026-11-21 03:18:49 | 修正 postcheck 5 項發現 |
| `581ae36` | 2026-11-21 03:57:27 | 覆蓋率門檻改為行＋分支 100%；修正 3 個 bug |

## 7. 過程紀錄檔案

- 主要迴圈：`runs/20261120-193502/loop-log.md`、`postcheck.md`、`timing.txt`、`summary.md`，以及各子代理步驟 `steps/`。
- 最終 gates 輸出：`runs/final-check/gates.txt`。
- 第一次停滯與更早的中止：`runs/ABORTED-20261120-175733-planner-stall/`、`runs/ABORTED-20261120-175517-old-roles/`（含 `timing.txt`；原始 `events.jsonl` 與 `sessions/` 不納入版本控制）。
- Colab 打包：`dist/qcconvert_colab.zip`。
