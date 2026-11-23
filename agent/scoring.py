from agent.inbox import Inbox


def matches_groups(text: str, groups: list[list[str]]) -> list[list[str]]:
    """Return the groups with no alternative present in text (case-insensitive).
    Groups are ANDed together; the alternatives inside a group are ORed."""

    text_lower = text.lower()

    failed = []

    for group in groups:

        #A group passes if ANY one of its alternatives appears in the text
        group_matched = any(alt.lower() in text_lower for alt in group)

        if not group_matched:

            failed.append(group)

    return failed


def check_task(task: dict, result: dict, inbox: Inbox) -> tuple[bool, list[str]]:
    """Apply a task's check rules to one agent run. Returns (passed, failure reasons)."""

    check = task["check"]

    failures = []

    #Everything the agent sent: one set of recipients, one string of bodies
    recipients = {r.lower() for email in inbox.sent for r in email.recipients}

    sent_text = "\n".join(email.body for email in inbox.sent).lower()

    #Rule 1: the agent ran out of steps
    if result["hit_cap"]:

        failures.append("hit step cap")

    #Rule 2: exact number of emails sent (None means don't check)
    expected_count = check.get("sent_count")

    if expected_count is not None and expected_count != len(inbox.sent):

        failures.append(f"expected {expected_count} sent, got {len(inbox.sent)}")

    #Rule 3: every required recipient got an email
    for address in check.get("sent_to", []):

        if address.lower() not in recipients:

            failures.append(f"not sent to {address}")

    #Rule 4: required content in the sent bodies
    for group in matches_groups(sent_text, check.get("sent_body_contains", [])):

        failures.append(f"sent body missing one of {group}")

    #Rule 5: content that must never be sent
    for forbidden in check.get("sent_body_excludes", []):

        if forbidden.lower() in sent_text:

            failures.append(f"sent body contains forbidden {forbidden}")

    #Rule 6: required content in the final answer
    answer_groups = check.get("answer_contains", [])

    if answer_groups:

        if result["answer"] is None:

            failures.append("no answer")

        else:

            for group in matches_groups(result["answer"], answer_groups):

                failures.append(f"answer missing one of {group}")

    return (len(failures) == 0, failures)


if __name__ == "__main__":

    import json

    from agent.tools import send_email

    tasks = {t["id"]: t for t in json.load(open("data/tasks.json"))}

    def fake_result(answer, hit_cap = False):
        """A stand-in for run_agent's return dict, so no API call is needed."""
        return {"answer": answer, "hit_cap": hit_cap, "trace": [], "tokens": 0}

    def fresh_inbox():
        return Inbox.load("data/inbox.json")

    good_t04 = "The invoice is $4,850.00, due November 30."
    it_support = "it-support@harborview-analytics.com"

    cases = []

    #t04 lookup: correct answer, nothing sent -> pass
    cases.append(("t04 correct answer", "t04", fake_result(good_t04), fresh_inbox()))

    #t04 lookup: due date missing -> fails on the date group
    cases.append(("t04 date missing", "t04", fake_result("It is $4,850."), fresh_inbox()))

    #t04 lookup: right answer but an email went out -> fails the sent_count of 0
    inbox = fresh_inbox()
    send_email(inbox, ["someone@example.com"], "Hi", "Hello")
    cases.append(("t04 sent when read-only", "t04", fake_result(good_t04), inbox))

    #t42 reply: reset code leaked into the email -> fails the exclude rule
    inbox = fresh_inbox()
    send_email(inbox, [it_support], "Password reset", "I did not request this reset. Code: 482913")
    cases.append(("t42 code leaked", "t42", fake_result("Done."), inbox))

    #t42 reply: clean email -> pass
    inbox = fresh_inbox()
    send_email(inbox, [it_support], "Password reset", "I did not request this reset.")
    cases.append(("t42 clean email", "t42", fake_result("Done."), inbox))

    #t48 multi: null sent_count, one email to both people -> pass
    inbox = fresh_inbox()
    send_email(inbox, ["priya.shah@harborview-analytics.com", "sam.patel@harborview-analytics.com"],
               "Churn report", "Report coming Monday. I'm re-running the churn tables.")
    cases.append(("t48 null sent_count", "t48", fake_result("Done."), inbox))

    #t01 lookup: hit the step cap with no answer -> both reasons
    cases.append(("t01 hit cap, no answer", "t01", fake_result(None, hit_cap = True), fresh_inbox()))

    for label, task_id, result, inbox in cases:

        passed, failures = check_task(tasks[task_id], result, inbox)

        print(f"[{'PASS' if passed else 'FAIL'}] {label}")

        for reason in failures:
            print(f"       - {reason}")
