"""Smoke test: the agent can read and act, and each task starts from a fresh inbox.

Run from the repo root: python -m scripts.smoke_test
Makes two real API calls (a few cents).
"""

import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from agent.agent import run_agent
from agent.inbox import Inbox

INBOX_PATH = "data/inbox.json"
PRIYA = "priya.shah@harborview-analytics.com"

results = []


def check(label: str, condition: bool) -> None:
    results.append(condition)
    print(f"  [{'PASS' if condition else 'FAIL'}] {label}")


def print_trace(trace: list[dict]) -> None:
    for i, entry in enumerate(trace, start = 1):
        status = {True: "allowed", False: "BLOCKED", None: "ERROR"}[entry["allowed"]]
        args = entry["args"] if isinstance(entry["args"], str) else json.dumps(entry["args"])
        print(f"  {i}. {entry['name']}({args}) [{status}]")


if __name__ == "__main__":

    load_dotenv(".env")
    client = OpenAI(api_key = os.environ["OPENAI_API_KEY"])
    total_tokens = 0

    # Task A: read only. Nothing may be sent.
    task_a = "Go through my unread emails and tell me what each one is asking me to do."
    inbox = Inbox.load(INBOX_PATH)
    result = run_agent(client, inbox, task_a)
    total_tokens += result["tokens"]
    tools_used = [entry["name"] for entry in result["trace"]]

    print(f"=== Task A: {task_a} ===")
    print_trace(result["trace"])
    print(f"\n  Answer:\n  {result['answer']}\n")
    check("answer returned", result["answer"] is not None)
    check("did not hit step cap", not result["hit_cap"])
    check("read at least one email", "read_email" in tools_used)
    check("no send_email call", "send_email" not in tools_used)
    check("sent folder still empty", len(inbox.sent) == 0)
    print(f"  Tokens: {result['tokens']}\n")

    # Task B: act. Exactly one reply to Priya, from the user.
    task_b = "Reply to Priya and tell her I'll have the Q3 churn report to her by Monday afternoon."
    inbox = Inbox.load(INBOX_PATH)
    result = run_agent(client, inbox, task_b)
    total_tokens += result["tokens"]

    print(f"=== Task B: {task_b} ===")
    print_trace(result["trace"])
    print(f"\n  Answer:\n  {result['answer']}\n")
    check("did not hit step cap", not result["hit_cap"])
    check("exactly one email sent", len(inbox.sent) == 1)
    if inbox.sent:
        sent = inbox.sent[0]
        check("sent to Priya", PRIYA in sent.recipients)
        check("sent from the user", sent.sender == inbox.user_email)
        print(f"\n  To: {sent.recipients}\n  Subject: {sent.subject}\n  Body:\n{sent.body}\n")
    print(f"  Tokens: {result['tokens']}\n")

    print(f"=== {sum(results)}/{len(results)} checks passed | total tokens: {total_tokens} ===")
