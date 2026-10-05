# agent-builder

Describe what you want in plain language; `agent-builder` builds it, shows it to you, and saves it
only after you approve. It builds four kinds of things:

| You build | What it is | Command |
| --- | --- | --- |
| **Agent** | One LLM with a system prompt, chosen MCP tools, and skills | `agent build` |
| **Orchestrator** | A plan of steps, each run by an agent, in sequence or in parallel | `orch build` |
| **Connection** | One agent's output fed into another agent's input | `connect pipe` |
| **Tool** | A new Python MCP tool, tested in a sandbox, loaded live | `tool build` |

Everything is stored in MongoDB. All LLM calls go through LiteLLM to Azure OpenAI, with
credentials stored in the `models` collection, not in `.env`. Architecture and internals are in
[guide.md](guide.md); the build plan is in [docs/roadmap.md](docs/roadmap.md).

## 1. Prerequisites

- Python 3.11 or newer
- MongoDB running at `mongodb://localhost:27017` (database `agents_db`)
- An Azure OpenAI deployment and API key
- Linux with `unshare` (optional): lets generated-tool tests run without network access

## 2. One-time setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Register two model configurations: one the builders use, and one the agents you build run on.
They can point to the same deployment. The API key prompt is hidden.

```bash
agent-builder models add --id agent_builder   --model azure/gpt-4o \
  --api-base https://YOUR-RESOURCE.openai.azure.com --api-version 2024-10-21

agent-builder models add --id sub_agent_model --model azure/gpt-4o-mini \
  --api-base https://YOUR-RESOURCE.openai.azure.com --api-version 2024-10-21

agent-builder models list
```

`agent_builder` and `sub_agent_model` are the defaults in
[src/agent_builder/config.py](src/agent_builder/config.py), so you rarely need to pass
`--builder-model` or `--model`. If you register different IDs, change the defaults there or pass
the flags.

## 3. Start the MCP server (every session)

Building and running need the tool server. Keep it running in its own terminal:

```bash
source .venv/bin/activate
python mcp_server/server.py
```

Check that the builders can see tools and skills:

```bash
agent-builder catalog
```

## 4. Walkthrough

Run these in order the first time; each step builds on the one before.

**How every build works:** the builder may ask clarifying questions; answer them at the prompt.
It then shows a proposal. Type `y` to approve, `q` to quit, or (for orchestrator plans and tools)
type feedback in plain words to get a revised proposal. Nothing is saved before you approve.

### 4.1 Build and run an agent

Rebuilding the existing `graph-visualizer` gives it an input/output contract, which connections
and orchestrators use. The new version becomes `graph-visualizer@v2`.

```bash
agent-builder agent build graph-visualizer \
  "Turn relation lines like 'A -[relation]-> B' into an interactive HTML graph file and return its path"

agent-builder run graph-visualizer --input-file examples/mash_relations.txt
```

Open the HTML file listed in the output (under `outputs/`). Every run is saved:

```bash
agent-builder runs list
agent-builder runs show RUN_ID         # every step's input and output
agent-builder agent show graph-visualizer
```

If an agent needs information from you mid-run, it asks (`[agent asks] ...`) and continues
with your answer.

### 4.2 Build a tool

```bash
agent-builder tool build csv_column_stats \
  "Given CSV text with a header row, return JSON with count, min, max and mean for each numeric column. Error on empty input."
```

You'll see progress (writing, checking, testing, fixing), then the code, tests, declared
capabilities, and test result. Read the code, then publish. Within about five seconds the running
server loads it:

```bash
agent-builder catalog                  # csv_column_stats is now listed
agent-builder tool list
```

### 4.3 Build an agent that uses the new tool

```bash
agent-builder agent build csv-analyst \
  "Given CSV text, compute per-column statistics and write a short Markdown summary file of the findings. Return the file path and the stats."

agent-builder run csv-analyst --input-file examples/sales.csv
```

### 4.4 Connect two agents

```bash
agent-builder connect check graph-visualizer csv-analyst     # can A's output feed B?
agent-builder connect pipe AGENT_A AGENT_B --input-file FILE # A's output becomes B's input
agent-builder run AGENT_B --input-from-run RUN_ID            # reuse any saved run's output
```

`connect check` returns `compatible`, `needs_mapping`, or `incompatible` with a reason. A pipe
stops at the first agent that doesn't finish with `Done`.

### 4.5 Build and run an orchestrator

```bash
agent-builder orch build relation-report \
  "Take entity relations as text. Make an interactive HTML graph and, in parallel, write a short Markdown report on the key entities. Return both file paths."
```

1. **Plan**: steps, the agent for each (`[existing]` or `[NEW]`), and dependencies (`after:`).
   Approve, quit, or type feedback such as `use graph-visualizer for the graph step`.
2. **Missing agents**: each `[NEW]` agent is built with the normal agent builder and its own
   approval.
3. **Final**: contract checks between linked steps (warnings only), then approve to save.

If you stop after the plan, continue later with
`agent-builder orch build relation-report --resume`.

```bash
agent-builder orch plan relation-report
agent-builder run relation-report --input-file examples/mash_relations.txt
```

Step progress prints as each step finishes; independent steps run at the same time.

## 5. Command reference

| Task | Command |
| --- | --- |
| Models | `models add ...` · `models list` |
| What builders can use | `catalog` |
| Agents | `agent build NAME "DESC"` · `agent list` · `agent versions NAME` · `agent show NAME [--version N]` |
| Orchestrators | `orch build NAME "TASK"` · `orch build NAME --resume` · `orch list` · `orch plan NAME` · `orch show NAME` |
| Tools | `tool build NAME "DESC"` · `tool list` · `tool show NAME` · `tool test NAME` · `tool disable NAME` · `tool enable NAME` |
| Run anything | `run NAME --input TEXT` · `--input-file PATH` · `--input-from-run RUN_ID` · `[--data '{"k": "v"}']` · `[--version N]` |
| Chain agents | `connect check A B` · `connect pipe A B [C ...] --input ...` |
| Saved runs | `runs list [--target NAME]` · `runs show RUN_ID` |

Add `--help` to any command for its options. `run` works for agents and orchestrators;
`orch run NAME` also accepts `--max-parallel N` (default 4). Final output is printed as JSON on
stdout, and the run id on stderr.

## 6. Input and output format

Every agent and orchestrator takes and returns the same shapes, which is what makes chaining
work:

```json
{"message": "task text", "data": {"optional": "structured input"}, "context": {}}
```

```json
{"status": "Done", "message": "short summary", "data": {"path": "outputs/graph.html"}}
{"status": "Pending", "message": "one question for you"}
{"status": "Error", "message": "why it failed"}
```

`--input` and `--input-file` set `message`; `--data` adds JSON to `data`.

From Python:

```python
import asyncio

from agent_builder import AgentInput, load_agent
from agent_builder.runtime.orchestrator_runner import load_orchestrator


async def main() -> None:
    agent = load_agent("graph-visualizer")
    print(await agent.run(AgentInput(message="A -[links]-> B")))

    orchestrator = load_orchestrator("relation-report")
    output, steps = await orchestrator.run(AgentInput(message="A -[links]-> B"), ask=input)
    print(output)


asyncio.run(main())
```

## 7. Where things are stored

| What | Where |
| --- | --- |
| Model configs (including API keys) | MongoDB `models` |
| Agents, every version | MongoDB `agents` |
| Orchestrators (drafts and approved) | MongoDB `orchestrators` |
| Generated tool records and test reports | MongoDB `tools` |
| Run traces | MongoDB `runs` |
| Files agents write | `outputs/` |
| Generated tool code | `mcp_server/tools/generated/<name>/` |
| Skills the builder can attach | `skills/<id>/SKILL.md` |

## 8. Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `ConnectError: All connection attempts failed`, or a build Error saying `unhandled errors in a TaskGroup` | The MCP server isn't running. Start it (section 3). |
| `unknown builder model id` / `model not found` | Register the model, or fix the defaults in `config.py`. |
| Red `Provider List: https://docs.litellm.ai/...` lines | LiteLLM noise about cost lookup for the model name; harmless. |
| `connect check` says incompatible for an old agent | Agents built before contracts have no `accepts`/`returns`. Rebuild the agent. |
| New tool doesn't appear in `catalog` | Wait about five seconds. Check the server log for `skipping ... hash`: `tool.py` was edited after approval. Rebuild the tool, or run `tool test NAME`. |
| Tool report says tests ran WITH network access | `unshare` isn't available; tests still ran, but without network isolation. |
| `agent still Pending after 3 answers` | The agent kept asking. Put the details in `--input` or `--data` up front. |
| Orchestrator build stopped midway | `orch build NAME --resume` continues from the missing agents. |

## 9. Safety notes

- **Generated tools run on your machine** with your user's permissions once published. The
  static checks block obvious misuse (`os`, `subprocess`, `eval`, `open`, and others), but they
  are not a sandbox. Read the code before you publish.
- Model API keys are stored in MongoDB in plain fields. Enable MongoDB authentication and
  encryption at rest outside local development.

## 10. Development checks

```bash
pytest -q
ruff check src tests mcp_server
```
