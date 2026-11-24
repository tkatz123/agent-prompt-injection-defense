"""Run every defense combination through both benchmarks, a few configurations at a time.

Run from the repo root:
    python -m scripts.run_configs --dry-run        # show what would run, run nothing
    python -m scripts.run_configs --workers 4      # run everything not yet finished

Each configuration runs the utility benchmark (50 tasks) and then the attack benchmark (100 attacks)
as its own process, with output in runs/logs/<label>.log. A benchmark whose results file already has
every line is skipped, so an interrupted sweep resumes by rerunning the same command.

The no-defense configuration is not rerun: its results are runs/utility/baseline.jsonl and
runs/attacks/undefended.jsonl, produced by the same frozen agent before any defense existed.
"""

import argparse
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from agent.hooks import all_configs, config_label

EXPECTED = {"utility": 50, "attacks": 100}
LOG_DIR = Path("runs/logs")


def is_complete(kind: str, label: str) -> bool:
    """True if runs/<kind>/<label>.jsonl exists and holds a record for every task or attack."""

    path = Path("runs") / kind / f"{label}.jsonl"

    if not path.exists():
        return False

    with open(path) as f:
        return sum(1 for line in f if line.strip()) == EXPECTED[kind]


def run_config(defenses: list[str]) -> tuple[str, bool, float]:
    """Run whichever of the two benchmarks this configuration still needs. Returns (label, ok, minutes)."""

    label = config_label(defenses)
    LOG_DIR.mkdir(parents = True, exist_ok = True)
    start = time.time()
    ok = True

    with open(LOG_DIR / f"{label}.log", "a") as log:

        for kind, module in [("utility", "scripts.run_utility"), ("attacks", "scripts.run_attacks")]:

            if is_complete(kind, label):
                continue

            command = [sys.executable, "-m", module, "--defenses", *defenses]
            log.write(f"\n$ {' '.join(command)}\n")
            log.flush()

            result = subprocess.run(command, stdout = log, stderr = subprocess.STDOUT)

            if result.returncode != 0 or not is_complete(kind, label):
                ok = False
                break

    return label, ok, (time.time() - start) / 60


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description = "Run every defense combination through both benchmarks.")
    parser.add_argument("--workers", type = int, default = 4, help = "Configurations to run at the same time")
    parser.add_argument("--dry-run", action = "store_true", help = "List what would run and stop")
    args = parser.parse_args()

    configs = [c for c in all_configs() if c]
    pending = [c for c in configs
               if not (is_complete("utility", config_label(c)) and is_complete("attacks", config_label(c)))]

    print(f"{len(configs)} defended configurations, {len(configs) - len(pending)} already complete, "
          f"{len(pending)} to run with {args.workers} workers.")

    for c in pending:
        needs = [kind for kind in EXPECTED if not is_complete(kind, config_label(c))]
        print(f"  {config_label(c):<36} needs {', '.join(needs)}")

    if args.dry_run or not pending:
        sys.exit(0)

    #Load the classifier once before starting, so parallel workers don't all download it at the same time
    if any("classifier" in c for c in pending):
        from agent.hooks import get_detector
        get_detector()

    failed = []

    with ThreadPoolExecutor(max_workers = args.workers) as pool:

        futures = [pool.submit(run_config, c) for c in pending]

        for future in as_completed(futures):
            label, ok, minutes = future.result()
            print(f"{'done  ' if ok else 'FAILED'} {label:<36} {minutes:.1f} min")
            if not ok:
                failed.append(label)

    if failed:
        print(f"\n{len(failed)} configurations did not finish; see runs/logs/. Rerun this command to resume.")
    else:
        print("\nAll configurations complete.")
