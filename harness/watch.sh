#!/usr/bin/env bash
# usage: watch_pic.sh <expdir> ; check every 60s, log every 5 min.
# Idle = seconds since newest file in THIS run dir / src / tests (not the box-global opencode.db-wal,
# which other agents' opencode sessions keep fresh). Box suspension is detected by wall-clock gaps
# (>180s between 60s ticks); suspended time is not counted, but after a resume the stream is often dead,
# so the idle limit drops from 25 min to 10 min.
cd "$1"; L=runs/driver.log; LIMIT=1500; prev=$(date +%s); n=0; awake_idle=0
while true; do
  sleep 60; now=$(date +%s); gap=$((now-prev)); prev=$now; n=$((n+1))
  P=$(pgrep -f "opencode run --agent orchestrator.*$(basename $1) " | head -1)
  [ -z "$P" ] && { echo "$(date -Is) watch: opencode exited" >> $L; break; }
  R=$(ls -td runs/2026* | head -1)
  if [ $gap -gt 180 ]; then echo "$(date -Is) watch: box suspend detected (gap ${gap}s); idle limit -> 600s" >> $L; LIMIT=600; awake_idle=0; continue; fi
  NEWEST=$(find $R src tests scripts colab docs -type f -not -path '*__pycache__*' -printf '%T@\n' 2>/dev/null | sort -n | tail -1 | cut -d. -f1)
  if [ $(( now - ${NEWEST:-0} )) -ge 60 ]; then awake_idle=$((awake_idle+gap)); else awake_idle=0; LIMIT=1500; fi
  N429=$(grep -c '429\|usage limit' $R/stderr.txt 2>/dev/null)
  [ $((n%5)) = 0 ] && echo "$(date -Is) monitor: $(wc -l < $R/events.jsonl) events, awake idle ${awake_idle}s (limit $LIMIT), 429s=$N429" >> $L
  if [ $awake_idle -ge $LIMIT ]; then echo "$(date -Is) watch: STALL (${awake_idle}s awake idle, 429s=$N429); killing $P" >> $L; touch $R/STALL_KILLED; kill $P; break; fi
done
