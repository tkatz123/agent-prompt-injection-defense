"""Utility benchmark: run each legitimate task on a fresh inbox and score it.

Run from the repo root:
    python -m scripts.run_utility --ids t01 t23 t31 t42 t48 --label trial
    python -m scripts.run_utility                      # all 50, label "baseline"
    python -m scripts.run_utility --defenses spotlight gate   # label "spotlight+gate"

Results go to runs/utility/<label>.jsonl, one line per task, written as each task finishes.
run_all() takes a list of defense names (see agent/hooks.py) so the same runner scores every configuration.
"""

import argparse
import json
import os
import time
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from agent.agent import run_agent
from agent.hooks import build_hooks, config_label, parse_defenses
from agent.inbox import Inbox
from agent.scoring import check_task

TASKS_PATH = "data/tasks.json"
INBOX_PATH = "data/inbox.json"
RUNS_DIR = Path("runs/utility")


def load_tasks(ids: list[str] | None) -> list[dict]:
    """Load all tasks, or only the requested ids. Unknown ids raise instead of being skipped."""

    tasks = json.load(open(TASKS_PATH))

    if not ids:
        return tasks

    known = {task["id"] for task in tasks}
    unknown = [task_id for task_id in ids if task_id not in known]

    if unknown:
        raise ValueError(f"Unknown task ids: {unknown}")

    return [task for task in tasks if task["id"] in ids]


def run_all(client, tasks: list[dict], defenses = (), label: str = "baseline") -> list[dict]:
    """Run every task on a fresh inbox, score it, and write each record as it finishes."""

    RUNS_DIR.mkdir(parents = True, exist_ok = True)
    out_path = RUNS_DIR / f"{label}.jsonl"

    records = []

    with open(out_path, "w") as f:

        for i, task in enumerate(tasks, start = 1):

            #Fresh inbox every task, so one task's sends never leak into the next
            inbox = Inbox.load(INBOX_PATH)

            #Built per task: gating and the monitor need this task's request
            before_tool, after_tool, system_prompt, usage = build_hooks(defenses, client, inbox, task["prompt"])

            start = time.time()

            try:
                result = run_agent(client, inbox, task["prompt"], before_tool = before_tool,
                                   after_tool = after_tool, system_prompt = system_prompt)
                passed, failures = check_task(task, result, inbox)

            except Exception as e:
                #An API error fails this task without killing the batch
                result = {"answer": None, "trace": [], "steps": 0, "hit_cap": False, "tokens": 0}
                passed, failures = False, [f"error: {e}"]

            record = {
                "id": task["id"],
                "defenses": config_label(defenses),
                "category": task["category"],
                "prompt": task["prompt"],
                "passed": passed,
                "failures": failures,
                "answer": result["answer"],
                "trace": result["trace"],
                "sent": [email.model_dump(mode = "json") for email in inbox.sent],
                "steps": result["steps"],
                "hit_cap": result["hit_cap"],
                "tokens": result["tokens"],
                "defense_tokens": usage["defense_tokens"],
                "seconds": round(time.time() - start, 1),
            }

            #Write and flush now, so a crash later keeps everything finished so far
            f.write(json.dumps(record) + "\n")
            f.flush()

            records.append(record)

            print(f"[{i}/{len(tasks)}] {task['id']} {'PASS' if passed else 'FAIL'} ({record['tokens']} tokens)")

            for reason in failures:
                print(f"       - {reason}")

    print(f"\nSaved {len(records)} records to {out_path}")

    return records


def print_summary(records: list[dict], label: str) -> None:
    """Overall utility, utility by category, every failure with its reasons, and cost."""

    total = len(records)
    passed = sum(record["passed"] for record in records)

    print(f"\n=== {label} utility: {passed}/{total} ({100 * passed / total:.1f}%) ===")

    by_category = Counter(record["category"] for record in records)
    passed_by_category = Counter(record["category"] for record in records if record["passed"])

    print("\nBy category:")
    for category, count in by_category.items():
        print(f"  {category:<8} {passed_by_category[category]}/{count}")

    failed = [record for record in records if not record["passed"]]

    if failed:
        print("\nFailures:")
        for record in failed:
            print(f"  {record['id']}: {record['prompt']}")
            for reason in record["failures"]:
                print(f"       - {reason}")
            print(f"       answer: {(record['answer'] or '')[:200]}")

    blocked = sum(1 for record in records for step in record["trace"] if step["allowed"] is False)
    print(f"\nTool calls blocked by a defense: {blocked}")

    total_tokens = sum(record["tokens"] for record in records)
    defense_tokens = sum(record.get("defense_tokens", 0) for record in records)
    print(f"Defense tokens (monitor calls): {defense_tokens}")
    print(f"\nTokens: {total_tokens} total, {total_tokens / total:.0f} per task")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description = "Run the legitimate-task utility benchmark.")
    parser.add_argument("--ids", nargs = "*", default = None, help = "Task ids to run (default: all)")
    parser.add_argument("--defenses", nargs = "*", default = [], help = "Defenses to enable (default: none)")
    parser.add_argument("--label", default = None, help = "Output file name (default: baseline, or the defense names)")
    args = parser.parse_args()

    defenses = parse_defenses(args.defenses)
    label = args.label or (config_label(defenses) if defenses else "baseline")

    load_dotenv(".env")
    client = OpenAI(api_key = os.environ["OPENAI_API_KEY"])

    tasks = load_tasks(args.ids)
    records = run_all(client, tasks, defenses = defenses, label = label)
    print_summary(records, label)
