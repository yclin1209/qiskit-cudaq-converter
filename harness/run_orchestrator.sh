#!/usr/bin/env bash
# Drives one headless orchestrator run (native opencode subagent delegation via the task tool)
# and captures events, session exports, timings and stats under runs/<timestamp>/.
set -uo pipefail
cd "$(dirname "$0")/.."
RUN="runs/$(date +%Y%m%d-%H%M%S)"; echo "$RUN" > runs/current-run.txt
mkdir -p "$RUN/sessions"
PROMPT="依 AGENTS.md（含「環境事實」與「已決定事項」）與 specs/SPEC.md，從零開發 qcconvert（程式放 src/qcconvert/，notebook 放 colab/，打包腳本放 scripts/），走完三關流程（planner → coder → reviewer + tester），最多 8 輪，reviewer 與 tester 都 VERDICT: PASS 才結束。驗收以 SPEC §5 凍結的 14 條為準。每輪結束把紀錄追加到 $RUN/loop-log.md，用繁體中文寫，專有名詞附英文。委派時要求所有子代理的文件與回覆都用繁體中文。${RESUME_NOTE:-}"
printf '%s\n' "$PROMPT" > "$RUN/prompt.txt"
opencode stats --project "" --models > "$RUN/stats_before.txt" 2>&1 < /dev/null || true
START_MS=$(date +%s%3N)
echo "start $(date -Is)" > "$RUN/timing.txt"
timeout 14400 opencode run --agent orchestrator --format json --title "$(basename "$PWD") $RUN" "$PROMPT" \
  < /dev/null > "$RUN/events.jsonl" 2> "$RUN/stderr.txt"
RC=$?
END_MS=$(date +%s%3N)
{ echo "end $(date -Is)"; echo "exit_code $RC"; echo "wall_ms $((END_MS-START_MS))"; } >> "$RUN/timing.txt"
opencode stats --project "" --models > "$RUN/stats_after.txt" 2>&1 < /dev/null || true
# export parent + child sessions
python3 - "$RUN" <<'PY'
import json, os, re, subprocess, sys
run = sys.argv[1]
ids: list[str] = []
for line in open(f"{run}/events.jsonl"):
    try:
        e = json.loads(line)
    except ValueError:
        continue
    sid = e.get("sessionID")
    if sid and sid not in ids:
        ids.append(sid)
    out = str(e.get("part", {}).get("state", {}).get("output") or "")
    for m in re.findall(r'<task id="(ses_[A-Za-z0-9]+)"', out):
        if m not in ids:
            ids.append(m)
for sid in ids:
    # NOTE: capturing `opencode export` through a pipe truncated output at 64 KiB in our first run;
    # writing to a regular file avoids that.
    tmp = f"{run}/sessions/{sid}.raw"
    with open(tmp, "w") as fh:
        subprocess.run(["opencode", "export", sid], stdout=fh, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    txt = open(tmp).read()
    os.remove(tmp)
    i = txt.find("{")
    open(f"{run}/sessions/{sid}.json", "w").write(txt[i:] if i >= 0 else txt)
print("exported", len(ids), "sessions")
PY
python3 harness/summarize_run.py "$RUN" > "$RUN/summary.md"
echo "done: $RUN rc=$RC"
