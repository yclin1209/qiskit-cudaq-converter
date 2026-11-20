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
# 停滯監看：harness/watch.py 以 opencode.db 中本次 run 所有（含子代理）session 的最後活動時間判斷；
# 停滯被砍掉時自動續跑一次（RESUME_NOTE 告知 orchestrator 從未完成的輪次接續），第二次停滯就停止交給人。
PREV=""
for attempt in 1 2; do
  [ -n "$PREV" ] && export RESUME_NOTE=" 【續跑】上一次 run（$PREV）因模型串流停滯被 harness 中止。先讀 docs/plan.md、$PREV/loop-log.md（若存在）與現有 src/ tests/，從尚未完成的那一輪接續（已有合格的 docs/plan.md 就不要重新規劃）；輪次合計（含上一次）仍以 8 輪為上限。"
  bash harness/run_orchestrator.sh >> runs/harness-stdout.txt 2>&1 & H=$!; sleep 15
  R=$(cat runs/current-run.txt)
  python3 harness/watch.py "$D" "$D/$R" & WP=$!
  wait $H; kill $WP 2>/dev/null; wait $WP 2>/dev/null
  echo "$(date -Is) drive: run ended ($R) $(tail -2 $R/timing.txt | tr '\n' ' ')" >> $L
  if [ -f "$R/STALL_KILLED" ]; then
    echo "$(date -Is) drive: stall kill in attempt $attempt: $(cat $R/STALL_KILLED)" >> $L
    [ $attempt = 2 ] && { echo "$(date -Is) drive: second stall; STOP for human" >> $L; echo "STOPPED_AFTER_SECOND_STALL" > runs/final-check/status.txt; }
    PREV=$R; continue
  fi
  break
done
{ echo "== pytest"; .venv/bin/python -m pytest -q 2>&1 | tail -30; echo "== ruff check"; .venv/bin/ruff check src tests scripts 2>&1 | tail -5
  echo "== ruff format --check"; .venv/bin/ruff format --check src tests scripts 2>&1 | tail -5; echo "== mypy"; .venv/bin/mypy src 2>&1 | tail -5; } > runs/final-check/gates.txt
echo "$(date -Is) drive: ALL DONE" >> $L
