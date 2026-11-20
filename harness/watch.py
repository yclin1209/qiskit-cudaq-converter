#!/usr/bin/env python3
"""Stall watcher for one orchestrator run.

usage: watch.py <project_dir> <run_dir>

Activity = newest part/message update in opencode.db across the run's root session and ALL
descendant (subagent) sessions. The old file-mtime watcher missed a 50-minute planner stall because
subagent progress never reaches events.jsonl. Also counts provider stall errors
("stream content stall" / "Idle timeout") for these sessions in opencode.log.

Kill (and touch <run>/STALL_KILLED with the reason) when:
  * no DB activity for IDLE_LIMIT awake seconds (default 900), or
  * >= STALL_LIMIT provider stall errors in one session (default 3; each costs 5-10 min).
Box suspension (wall-clock gap > 180s between ticks) is not counted as idle.
"""
import os, re, signal, sqlite3, subprocess, sys, time

proj, run = sys.argv[1], sys.argv[2]
IDLE_LIMIT = int(os.environ.get("IDLE_LIMIT", "900"))
STALL_LIMIT = int(os.environ.get("STALL_LIMIT", "3"))
DB = os.path.expanduser("~/.local/share/opencode/opencode.db")
LOG = os.path.expanduser("~/.local/share/opencode/log/opencode.log")
DRV = os.path.join(proj, "runs/driver.log")
title = f"{os.path.basename(proj)} {os.path.relpath(run, proj)}"
STALL_RE = re.compile(r'session\.id=(ses_\w+).*(stream content stall|Idle timeout)')


def log(msg: str) -> None:
    with open(DRV, "a") as f:
        f.write(time.strftime("%Y-%m-%dT%H:%M:%S%z") + " watch: " + msg + "\n")


def q(sql: str, args=()):
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=10)
    try:
        return c.execute(sql, args).fetchall()
    finally:
        c.close()


def sessions():
    root = q("select id from session where title=? order by time_created desc limit 1", (title,))
    if not root:
        return []
    ids, frontier = [root[0][0]], [root[0][0]]
    while frontier:
        nxt = [r[0] for r in q(f"select id from session where parent_id in ({','.join('?'*len(frontier))})", frontier)]
        frontier = [i for i in nxt if i not in ids]
        ids += frontier
    return ids


def last_activity(ids):
    ph = ",".join("?" * len(ids))
    a = q(f"select max(time_updated) from part where session_id in ({ph})", ids)[0][0] or 0
    b = q(f"select max(time_updated) from message where session_id in ({ph})", ids)[0][0] or 0
    return max(a, b) / 1000.0


def orch_pid():
    out = subprocess.run(["pgrep", "-f", f"^opencode run --agent orchestrator .*{title}"],
                         capture_output=True, text=True).stdout.split()
    return int(out[0]) if out else None


log_pos = os.path.getsize(LOG) if os.path.exists(LOG) else 0
stalls: dict[str, int] = {}
prev = time.time(); idle = 0.0; n = 0; seen_root = False
log(f"start (title={title!r}, idle limit {IDLE_LIMIT}s, stall limit {STALL_LIMIT}/session)")
while True:
    time.sleep(30)
    now = time.time(); gap = now - prev; prev = now; n += 1
    pid = orch_pid()
    if pid is None:
        log("orchestrator exited"); break
    try:
        ids = sessions()
    except sqlite3.Error as e:
        log(f"db error {e}"); continue
    if not ids:
        if n > 10: log("no root session found after 5 min")
        continue
    seen_root = True
    with open(LOG, errors="replace") as f:
        f.seek(log_pos); chunk = f.read(); log_pos = f.tell()
    for m in STALL_RE.finditer(chunk):
        if m.group(1) in ids:
            stalls[m.group(1)] = stalls.get(m.group(1), 0) + 1
            log(f"provider stall #{stalls[m.group(1)]} in {m.group(1)}: {m.group(2)}")
    if gap > 180:
        log(f"box suspend detected (gap {int(gap)}s); not counted"); continue
    act_age = now - last_activity(ids)
    idle = act_age if act_age > 60 else 0.0
    if n % 10 == 0:
        log(f"monitor: {len(ids)} sessions, last activity {int(act_age)}s ago, stalls={sum(stalls.values())}")
    reason = None
    if idle >= IDLE_LIMIT:
        reason = f"no DB activity for {int(idle)}s"
    elif stalls and max(stalls.values()) >= STALL_LIMIT:
        reason = f"{max(stalls.values())} provider stalls in {max(stalls, key=stalls.get)}"
    if reason:
        log(f"STALL: {reason}; killing orchestrator {pid}")
        open(os.path.join(run, "STALL_KILLED"), "w").write(reason + "\n")
        os.kill(pid, signal.SIGTERM); time.sleep(10)
        if orch_pid(): os.kill(pid, signal.SIGKILL)
        break
