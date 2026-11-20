"""Summarize one orchestrator run: per-step prompts/outputs/timings and token usage per session."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

TPE = timezone(timedelta(hours=8))


def ts(ms: int | None) -> str:
    if not ms:
        return "-"
    return datetime.fromtimestamp(ms / 1000, TPE).strftime("%H:%M:%S")


def main() -> None:
    run = Path(sys.argv[1])
    steps_dir = run / "steps"
    steps_dir.mkdir(exist_ok=True)
    out: list[str] = [f"# Run summary: {run.name}", ""]
    timing = (run / "timing.txt").read_text() if (run / "timing.txt").exists() else ""
    out += ["```", timing.strip(), "```", ""]

    # Steps = tool calls of the orchestrator, in order (task calls are subagent delegations).
    n = 0
    rows: list[str] = []
    for line in (run / "events.jsonl").read_text().splitlines():
        try:
            e: dict[str, Any] = json.loads(line)
        except ValueError:
            continue
        if e.get("type") != "tool_use":
            continue
        part = e.get("part", {})
        state = part.get("state", {})
        tool = part.get("tool")
        t = state.get("time", {})
        start, end = t.get("start"), t.get("end")
        dur = f"{(end - start) / 1000:.1f}s" if start and end else "-"
        inp = state.get("input", {})
        if tool == "task":
            n += 1
            agent = inp.get("subagent_type", "?")
            f = steps_dir / f"{n:02d}-{agent}.md"
            f.write_text(
                f"# Step {n}: {agent}\n\nstart {ts(start)} end {ts(end)} duration {dur}\n\n"
                f"## Prompt (from orchestrator)\n\n{inp.get('prompt', '')}\n\n"
                f"## Output\n\n{state.get('output') or state.get('error') or ''}\n"
            )
            verdict = "-"
            o = str(state.get("output") or "")
            for v in ("VERDICT: PASS", "VERDICT: FAIL"):
                if v in o:
                    verdict = v.split(": ")[1]
            rows.append(f"| {n} | {agent} | {ts(start)} | {ts(end)} | {dur} | {verdict} | {f.name} |")
    out += ["## Subagent steps (orchestrator task-tool calls)", "",
            "| # | agent | start (TPE) | end (TPE) | duration | verdict | log |", "|---|---|---|---|---|---|---|"]
    out += rows + [""]

    # Token usage per session.
    out += ["## Token usage per session (from `opencode export`)", "",
            "| session | agent | model | input | output | reasoning | cache read | cache write | cost |",
            "|---|---|---|---|---|---|---|---|---|"]
    tot = {"input": 0, "output": 0, "reasoning": 0, "read": 0, "write": 0}
    cost = 0.0
    per_agent: dict[str, dict[str, int]] = {}
    for p in sorted((run / "sessions").glob("*.json")):
        try:
            info = json.loads(p.read_text())["info"]
        except (ValueError, KeyError):
            continue
        tk = info.get("tokens", {})
        cache = tk.get("cache", {})
        model = info.get("model", {})
        agent = info.get("agent", "?")
        vals = {"input": tk.get("input", 0), "output": tk.get("output", 0), "reasoning": tk.get("reasoning", 0),
                "read": cache.get("read", 0), "write": cache.get("write", 0)}
        for k, v in vals.items():
            tot[k] += v
            per_agent.setdefault(f"{agent} ({model.get('providerID')}/{model.get('id')})", dict.fromkeys(tot, 0))[k] += v
        cost += float(info.get("cost", 0) or 0)
        out.append(f"| {info['id']} | {agent} | {model.get('providerID')}/{model.get('id')} | {vals['input']} | "
                   f"{vals['output']} | {vals['reasoning']} | {vals['read']} | {vals['write']} | {info.get('cost', 0)} |")
    out += ["", "## Per agent", "", "| agent (model) | input | output | reasoning | cache read | cache write |",
            "|---|---|---|---|---|---|"]
    for a, v in per_agent.items():
        out.append(f"| {a} | {v['input']} | {v['output']} | {v['reasoning']} | {v['read']} | {v['write']} |")
    out += ["", f"**Total**: input {tot['input']}, output {tot['output']}, reasoning {tot['reasoning']}, "
            f"cache read {tot['read']}, cache write {tot['write']}, reported cost ${cost:.4f}", ""]
    print("\n".join(out))


if __name__ == "__main__":
    main()
