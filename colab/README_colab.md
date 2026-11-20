# 在 Colab 使用 qcconvert

1. 在 Colab 選擇 Runtime → Change runtime type → T4 GPU（CPU 亦可，使用 `qpp-cpu`）。
2. 在本機執行 `python scripts/build_dist.py`，把 `dist/qcconvert_colab.zip` 上傳到 Colab 的 `/content/`。
3. 開啟 `qcconvert_demo.ipynb`，依序執行所有儲存格；安裝儲存格會執行 `pip install cudaq qiskit qiskit-aer ipywidgets`（`qiskit-aer` 用於中途測量（mid-circuit measurement）的 Qiskit 參考分佈；`ipywidgets` 用於雙欄編輯器）。
4. 使用雙欄編輯器（widget）或 cell magic 轉換；Qiskit 原始碼輸入**會執行輸入的程式碼**，只貼入可信任程式碼。

如果先在 CPU runtime 安裝才切到 GPU，請重新安裝 CUDA-Q（安裝時會根據 CUDA 版本選 cu12／cu13）。沒有 GPU 可照常使用 CPU。未上傳 zip 時 notebook 會提示在 Colab 上傳。
