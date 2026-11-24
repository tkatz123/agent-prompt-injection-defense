"""Summarize every defense configuration into one results table.

Run from the repo root:
    python -m scripts.summarize              # print the tables from runs/
    python -m scripts.summarize --freeze     # also copy every run into results/ and write the summary files

Per configuration:
    clean utility          legitimate tasks passed, no attack present (50 tasks)
    ASR                    attacks whose goal shows up in what the agent sent (100 attacks)
    utility under attack   the user's task still passed during an attack (100 attacks)
Rates carry a 95% Wilson interval, because 50 and 100 trials leave wide error bars.

--freeze copies runs/utility/<label>.jsonl to results/<label>_utility.jsonl and runs/attacks/<label>.jsonl to
results/<label>_attacks.jsonl (the no-defense pair keeps its existing names, baseline_utility and
undefended_attacks), then writes results/summary.csv and results/summary.md. Committing results/ is the freeze.
"""

import argparse
import csv
import json
import math
import shutil
import sys
from collections import Counter
from pathlib import Path

from agent.hooks import all_configs, config_label

RESULTS = Path("results")
STYLES = ["override", "system_notice", "important_instructions", "polite_ps"]
GOALS = ["steal_reset_code", "steal_flight_code", "phish_colleague", "invoice_fraud", "send_to_attacker"]
EXPECTED = {"utility": 50, "attacks": 100}


def run_paths(label: str) -> dict:
    """Where each configuration's raw run files live, and where --freeze copies them."""

    if label == "none":
        return {"utility": (Path("runs/utility/baseline.jsonl"), RESULTS / "baseline_utility.jsonl"),
                "attacks": (Path("runs/attacks/undefended.jsonl"), RESULTS / "undefended_attacks.jsonl")}

    return {"utility": (Path(f"runs/utility/{label}.jsonl"), RESULTS / f"{label}_utility.jsonl"),
            "attacks": (Path(f"runs/attacks/{label}.jsonl"), RESULTS / f"{label}_attacks.jsonl")}


def load(path: Path) -> list[dict] | None:
    if not path.exists():
        return None
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion, as percentages."""

    if n == 0:
        return 0.0, 0.0

    p = successes / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)

    return 100 * max(0.0, centre - half), 100 * min(1.0, centre + half)


def rate(successes: int, n: int) -> str:
    low, high = wilson(successes, n)
    return f"{successes}/{n} ({100 * successes / n:.0f}%, {low:.0f} to {high:.0f})"


def blocked(records: list[dict]) -> int:
    return sum(1 for record in records for step in record["trace"] if step["allowed"] is False)


def summarize(defenses: list[str], use_results: bool) -> dict:
    """One row of numbers for one configuration, or a row marked incomplete."""

    label = config_label(defenses)
    paths = run_paths(label)
    utility = load(paths["utility"][1] if use_results else paths["utility"][0])
    attacks = load(paths["attacks"][1] if use_results else paths["attacks"][0])

    row = {"config": label, "n_defenses": len(defenses)}

    if (utility is None or len(utility) != EXPECTED["utility"]
            or attacks is None or len(attacks) != EXPECTED["attacks"]):
        row["incomplete"] = True
        return row

    errors = sum(any("error" in f for f in r["failures"]) for r in utility) + \
             sum(any("error" in f for f in r["utility_failures"]) for r in attacks)

    row.update({
        "incomplete": False,
        "clean_utility": sum(r["passed"] for r in utility),
        "asr": sum(r["attack_success"] for r in attacks),
        "utility_under_attack": sum(r["utility"] for r in attacks),
        "blocked_utility": blocked(utility),
        "blocked_attacks": blocked(attacks),
        "agent_tokens": sum(r["tokens"] for r in utility + attacks),
        "defense_tokens": sum(r.get("defense_tokens", 0) for r in utility + attacks),
        "api_errors": errors,
        "hijacked": [r["id"] for r in attacks if r["attack_success"]],
    })

    by_style = Counter(r["style"] for r in attacks if r["attack_success"])
    by_goal = Counter(r["goal"] for r in attacks if r["attack_success"])
    row.update({f"asr_{s}": by_style[s] for s in STYLES})
    row.update({f"asr_{g}": by_goal[g] for g in GOALS})

    return row


def markdown(rows: list[dict]) -> str:
    done = [r for r in rows if not r["incomplete"]]
    lines = ["## Main results", "",
             "| Configuration | Clean utility (/50) | ASR (/100) | Utility under attack (/100) | Blocked calls (tasks / attacks) | Agent tokens | Monitor tokens |",
             "|---|---|---|---|---|---|---|"]

    for r in done:
        lines.append(f"| {r['config']} | {rate(r['clean_utility'], 50)} | {rate(r['asr'], 100)} | "
                     f"{rate(r['utility_under_attack'], 100)} | {r['blocked_utility']} / {r['blocked_attacks']} | "
                     f"{r['agent_tokens']:,} | {r['defense_tokens']:,} |")

    lines += ["", "Rates show count, percent, and the 95% Wilson interval.", "",
              "## Attack success by injection style (each /25)", "",
              "| Configuration | " + " | ".join(STYLES) + " |", "|---|" + "---|" * len(STYLES)]
    lines += [f"| {r['config']} | " + " | ".join(str(r[f'asr_{s}']) for s in STYLES) + " |" for r in done]

    lines += ["", "## Attack success by attacker goal (each /20)", "",
              "| Configuration | " + " | ".join(GOALS) + " |", "|---|" + "---|" * len(GOALS)]
    lines += [f"| {r['config']} | " + " | ".join(str(r[f'asr_{g}']) for g in GOALS) + " |" for r in done]

    missing = [r["config"] for r in rows if r["incomplete"]]
    if missing:
        lines += ["", f"**Incomplete, not in the tables:** {', '.join(missing)}"]

    return "\n".join(lines)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description = "Summarize every defense configuration.")
    parser.add_argument("--freeze", action = "store_true",
                        help = "Copy all runs into results/ and write summary.csv and summary.md")
    args = parser.parse_args()

    configs = all_configs()

    if args.freeze:
        incomplete = [config_label(c) for c in configs if summarize(c, use_results = False)["incomplete"]]
        if incomplete:
            sys.exit(f"Not freezing: incomplete configurations {incomplete}. Finish the sweep first.")

        RESULTS.mkdir(exist_ok = True)
        for c in configs:
            for source, destination in run_paths(config_label(c)).values():
                shutil.copyfile(source, destination)

    rows = [summarize(c, use_results = args.freeze) for c in configs]
    report = markdown(rows)
    print(report)

    errors = sum(r.get("api_errors", 0) for r in rows)
    if errors:
        print(f"\nWARNING: {errors} records failed on an API error and count as failures. Check before freezing.")

    if args.freeze:
        (RESULTS / "summary.md").write_text("# IST 736 defense results (frozen)\n\n" + report + "\n")
        fields = [k for k in rows[0] if k not in ("incomplete", "hijacked")] + ["hijacked"]
        with open(RESULTS / "summary.csv", "w", newline = "") as f:
            writer = csv.DictWriter(f, fieldnames = fields, extrasaction = "ignore")
            writer.writeheader()
            for r in rows:
                writer.writerow({**r, "hijacked": " ".join(r.get("hijacked", []))})
        print(f"\nFroze {len(rows)} configurations into {RESULTS}/ (summary.md, summary.csv, raw jsonl). Commit results/ to finish.")
