# OrcAI

This project is a demonstration and benchmarking of using an LLM AI with dynamic role generation to orchestrate multiple agentic AIs to solve large-scale complex software development projects (in contrast to having a collaboration of multiple static roles or just having a single role AI using the agent tools).


## Setup

1.  **Create a virtual environment:** `python -m venv .venv`

2.  **Activate the virtual environment:** `source .venv/bin/activate`

3.  **Install `uv`:** `pip install uv`

4.  **Install dependencies:** `uv pip install -r requirements.txt`

5.  **Set up environment variables:** `cp env.example .env` and complete

6.  **Setup infrastructure:** `python setup.py -v`


## Run

`source .venv/bin/activate`

The `main.py` script supports three different usage patterns:

1. Default: `python main.py --prompt "Your task here"`

2. Custom with model: `python main.py --prompt "Get all the local folder listings of all associate workers" --model=gpt-4o`

3. Programmatic
```python
from main import main
custom_prompt = "Clone the repository and write the contents to Notion"
log_file = main(custom_prompt=custom_prompt, model="gpt-5")
print(f"Workflow completed. Log: {log_file}")
```

### Command Line Options

- `--prompt`: Prompt to send to the agents (required)
- `--clean`: Clean all environments before running
- `--agents`: Choose agent initialization mode: 'solo', 'pair', 'team', 'company', 'orchestrator', 'orchestrator-(small|medium|large)-(minimal|balanced|extensive)' (default: 'team')
- `--model`: LLM model to use (defaults to 'gpt-5')

### Examples

```bash
# Use default model (gpt-5)
python main.py --prompt "Deploy the application to AWS"

# Specify a different model
python main.py --prompt "Analyze code" --model=gpt-5-nano

# Combined with other options
python main.py --prompt "Update docs" --model=gpt-5-nano --clean --agents=solo
```

Logs are stored in the `../OrcAgent_runs/` directory.


## Test

- Agent Environment Integration Tests: `pytest agent_environment/`

- Tools Integration Tests: `pytest tools/`

- Agents Integration Tests: `pytest agents/`

- E2E Tests: `pytest test_e2e.py -v`

- Benchmark Tests: `pytest benchmarking/`

## Benchmark

The project includes a comprehensive benchmark system for evaluating agent performance across different complexity levels (small, medium, large, enterprise).

```bash
python benchmark.py --list-scenarios
python benchmark.py --agents=orchestrator
python benchmark.py --complexity small --agents=solo
python benchmark.py --scenario solo-electrician-website --agents=team
python benchmark.py --scenario solo-electrician-website --agents=solo --model=o3-mini
```

Results are saved to `benchmarking/results/` with individual scenario reports, execution logs, and summary statistics per agent mode.


## Teardown

The AWS resources should be torn down to avoid accumulating AWS costs.

`python teardown.py -v`
