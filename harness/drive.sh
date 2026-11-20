#!/usr/bin/env bash
# 用法：bash harness/drive.sh   （smoke test 模型 → 一次 orchestrator run（停滯監看）→ final gates）
# 金鑰只從 ~/.omniroute 讀進環境變數，不寫進 repo。
export OMNIROUTE_API_KEY=$(cat ~/.omniroute/client-keys/opencode.key)
D=$(cd "$(dirname "$0")/.." && pwd); cd $D; L=runs/driver.log; mkdir -p runs/final-check
{ echo "date $(date -Is)"; echo "opencode $(opencode --version </dev/null)"; echo "omniroute $(cat /workspace/omniroute/VERSION)"; } > runs/versions.txt
for m in $(grep -h "^model:" .opencode/agent/*.md | sed 's#model: omniroute/##' | sort -u) cc/claude-haiku-5-5; do
  r=$(timeout 120 opencode run -m omniroute/$m 'Reply with exactly: OK' </dev/null 2>&1 | tail -1)
  echo "$(date -Is) smoke $m: $r" >> $L; case "$r" in *OK*) ;; *) echo "$(date -Is) smoke failed; stop" >> $L; exit 1;; esac
done
echo "$(date -Is) drive: launching (cap 8)" >> $L
bash harness/run_orchestrator.sh >> runs/harness-stdout.txt 2>&1 & H=$!; sleep 20
bash harness/watch.sh $D & WP=$!
wait $H; kill $WP 2>/dev/null
R=$(ls -td runs/2026* | head -1); echo "$(date -Is) drive: run ended ($R) $(tail -2 $R/timing.txt | tr '\n' ' ')" >> $L
{ echo "== pytest"; .venv/bin/python -m pytest -q 2>&1 | tail -30; echo "== ruff check"; .venv/bin/ruff check src tests scripts 2>&1 | tail -5
  echo "== ruff format --check"; .venv/bin/ruff format --check src tests scripts 2>&1 | tail -5; echo "== mypy"; .venv/bin/mypy src 2>&1 | tail -5; } > runs/final-check/gates.txt
echo "$(date -Is) drive: ALL DONE" >> $L
