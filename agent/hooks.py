"""Assemble the defense hooks for one agent run.

A configuration is a list of defense names, e.g. ["spotlight", "gate"]. build_hooks() turns it
into the before_tool / after_tool / system_prompt that run_agent() takes. Hooks are built fresh
for every task, because gating and the monitor need the user's request and the gate needs the inbox.

The defenses themselves live in agent/defenses.py. This file only wires them together.

Order is fixed, whatever order the names are given in:
    after_tool:  classifier first (it has to see the raw email text), then spotlighting
    before_tool: gating first (free), then the monitor (one API call); the first block wins
"""

from functools import lru_cache
from itertools import combinations
from types import SimpleNamespace

from agent.agent import allow_all, pass_through, build_system_prompt

DEFENSES = ["spotlight", "classifier", "gate", "monitor"]

CLASSIFIER_MODEL = "protectai/deberta-v3-base-prompt-injection-v2"


def parse_defenses(names) -> list[str]:
    """Validate defense names and return them in canonical order, without duplicates."""

    unknown = [name for name in names if name not in DEFENSES]

    if unknown:
        raise ValueError(f"Unknown defenses: {unknown}. Choose from {DEFENSES}")

    return [name for name in DEFENSES if name in names]


def config_label(names) -> str:
    """File-safe name for a configuration, e.g. 'spotlight+gate'. No defenses is 'none'."""

    return "+".join(parse_defenses(names)) or "none"


def all_configs() -> list[list[str]]:
    """Every subset of the four defenses: 16 configurations, starting with no defenses."""

    return [list(combo) for size in range(len(DEFENSES) + 1) for combo in combinations(DEFENSES, size)]


@lru_cache(maxsize = 1)
def get_detector():
    """Load the injection classifier once per process. Downloads the model on first use."""

    from transformers import pipeline

    return pipeline("text-classification", model = CLASSIFIER_MODEL, truncation = True, max_length = 512)


def counting_client(client, usage: dict):
    """Wrap an OpenAI client so every chat completion it makes adds its tokens to usage['defense_tokens'].
    The monitor's API calls happen outside run_agent, so without this their cost would be invisible."""

    def create(**kwargs):
        response = client.chat.completions.create(**kwargs)
        usage["defense_tokens"] += response.usage.total_tokens
        return response

    return SimpleNamespace(chat = SimpleNamespace(completions = SimpleNamespace(create = create)))


def build_hooks(names, client, inbox, user_task: str):
    """Return (before_tool, after_tool, system_prompt, usage) for this configuration and task.
    usage['defense_tokens'] counts tokens spent by defenses themselves (the monitor), read after the run."""

    names = parse_defenses(names)
    system_prompt = build_system_prompt(inbox)
    usage = {"defense_tokens": 0}

    if not names:
        return allow_all, pass_through, system_prompt, usage

    #Imported here so undefended runs work even before defenses.py exists
    from agent import defenses

    after_steps = []
    before_steps = []

    if "classifier" in names:
        detector = get_detector()
        after_steps.append(lambda name, result: defenses.redact_injections(name, result, detector))

    if "spotlight" in names:
        after_steps.append(defenses.spotlight)
        system_prompt = system_prompt + " " + defenses.SPOTLIGHT_PROMPT

    if "gate" in names:
        #Computed once per task, from the inbox as the run starts
        known = defenses.known_addresses(inbox, user_task)
        before_steps.append(lambda name, args: defenses.gate(name, args, known))

    if "monitor" in names:
        monitor_client = counting_client(client, usage)
        before_steps.append(lambda name, args: defenses.monitor(name, args, user_task, monitor_client))

    def before_tool(name: str, args: dict) -> tuple[bool, str]:
        for check in before_steps:
            allowed, reason = check(name, args)
            if not allowed:
                return False, reason
        return True, ""

    def after_tool(name: str, result: str) -> str:
        for transform in after_steps:
            result = transform(name, result)
        return result

    return before_tool, after_tool, system_prompt, usage
