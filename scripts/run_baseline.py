from openai import OpenAI
from dotenv import load_dotenv
from agentdojo.agent_pipeline import OpenAILLM, AgentPipeline, PipelineConfig
from agentdojo.models import MODEL_NAMES
from agentdojo.task_suite import get_suite
from agentdojo.attacks.attack_registry import load_attack
from agentdojo.logging import OutputLogger
from agentdojo.benchmark import benchmark_suite_with_injections, benchmark_suite_without_injections
from pathlib import Path
import os

load_dotenv('.env')

#Creating OpenAI client
client = OpenAI(api_key = os.environ['OPENAI_API_KEY'])

llm = OpenAILLM(client, 'gpt-4.1-2025-04-14')

llm.name = 'gpt-4.1-2025-04-14'

MODEL_NAMES.update(
    {
        'gpt-4.1-2025-04-14': 'GPT-4'
    }
)

pipeline = AgentPipeline.from_config(
    PipelineConfig(
        llm = llm,
        model_id = None,
        defense = None,
        system_message_name = None,
        system_message = None
    )
)

suite = get_suite('v1.2.2', 'workspace')

attacks = load_attack('important_instructions', suite, pipeline)

logdir = Path("./runs")

with OutputLogger(str(logdir)):

    no_attack_suite_results = benchmark_suite_without_injections(
        pipeline,
        suite = suite,
        logdir = logdir,
        force_rerun = False,
        benchmark_version = 'v1.2.2' 
    )

    suite_results = benchmark_suite_with_injections(
        pipeline,
        suite = suite,
        attack = attacks,
        logdir = logdir,
        force_rerun = False,
        benchmark_version = 'v1.2.2'
        )

print(f"Utility Results: {suite_results['utility_results']}")
print(f"Security Results: {suite_results['security_results']}")
print(f"Injection Tasks Utility Results: {suite_results['injection_tasks_utility_results']}")


print(f"Utility Results (no attack): {no_attack_suite_results['utility_results']}")