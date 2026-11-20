# qcconvert — Qiskit ⇄ CUDA-Q 即時電路轉換

支援 Qiskit `QuantumCircuit` 或原始碼與 CUDA-Q kernel／原始碼之間的電路層級（circuit-level）轉換；可比較狀態向量保真度（fidelity）與抽樣總變異距離（TVD）。提供雙欄編輯器（widget）、cell magic、命令列（CLI）及 Colab notebook。Qiskit 原始碼輸入**會執行輸入的程式碼**，僅使用可信任內容；CUDA-Q 原始碼以 AST 靜態解析。

## 支援範圍與限制

- 支援 `h/x/y/z/s/t/sx` 及其反閘、旋轉閘、相位閘、`u`、`r`、受控閘、`swap/ccx/mcx`、`rxx/ryy/rzz`、測量與重置；常數迴圈、浮點參數、基本算術表示式及多量子暫存器。
- CUDA-Q 原始碼只支援指定的 AST 子集；不支援條件式測量分支、`while`、其他 kernel 呼叫、`exp_pauli`、`cudaq.control`。Qiskit 不支援古典條件控制、`delay`、脈衝（pulse），亦不支援 OpenQASM 3、雜訊模型、Hamiltonian／`observe`、C++ 或真實硬體。
- CUDA-Q 0.17 支援獨立的 `sdg`／`tdg` 與 `s.adj`／`t.adj`；但實測 `sdg.ctrl`、`tdg.ctrl`、`sdg.adj`、`tdg.adj` 無法編譯，AST 會明確拒絕。AST 亦辨識常用單控制閘別名（alias）。
- CUDA-Q kernel 物件經 OpenQASM 2 回轉時，`r1` 可能變成 `rz`，導致受控情境相對相位不保證等價；請優先使用 CUDA-Q 原始碼 AST 路徑。全域相位（global phase）在前向轉換會略過並警告。CLI `--to qiskit --check` 不執行不可信的原始碼，回傳 2。
- `compare(qc, kernel, args=...)` 的 `args` 按 kernel 函式簽章順序傳入；`ParameterVector` 每組佔一個列表。末端測量若無法從 kernel 原始碼重建測量前的演化，狀態向量指標為 `None`，只比較抽樣分佈（sampling distribution）。

## Colab（3 步驟）

1. 選擇 T4 GPU runtime（CPU 亦可使用 `qpp-cpu`），執行 `python scripts/build_dist.py` 建立 `dist/qcconvert_colab.zip`。
2. 上傳 zip 至 `/content/` 並開啟 `colab/qcconvert_demo.ipynb`，執行安裝儲存格。從 CPU 換 GPU 後須重新安裝 CUDA-Q。
3. 依序執行範例，使用 `%load_ext qcconvert`、`%%qiskit2cudaq --run` 或 `qcconvert.show()`。

## 本機開發與測試（gates）

Python 3.11+；環境備妥後使用：

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests scripts
.venv/bin/ruff format --check src tests scripts
.venv/bin/mypy src
```

命令列範例：`python -m qcconvert input.py --to cudaq -o output.py --check`。`--check` 的結果碼：等價 0、不等價 1、轉換／檢查錯誤 2。
