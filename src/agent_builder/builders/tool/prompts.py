from ...core.schemas import BuildToolRequest
from .checks import BLOCKED_MODULES, BLOCKED_NAMES, PURE_MODULES

TOOL_SYSTEM_PROMPT = f"""\
You write tools for an MCP server. AI agents call these tools, so each one must be small,
deterministic, and safe. A user describes a tool, possibly roughly; produce its code and tests.

tool.py rules:
- Exactly one public function, named exactly as the requested tool name. Private helpers
  (leading underscore), imports, and constants are allowed; nothing else at top level.
- Every parameter and the return value are type-annotated with JSON-friendly types (str, int,
  float, bool, list, dict). Return a str; for structured results return a JSON string.
- A docstring whose first paragraph says what the tool does, ending with a line
  "Use when: <when an agent should pick it>".
- Raise ValueError with a clear message for invalid input.
- Allowed imports: {", ".join(sorted(PURE_MODULES))}. Declare capabilities for anything more:
  - "files": read/write only inside the output directory, via
    `from tools.sdk import output_path` and `output_path(filename).read_text()` /
    `.write_text(...)`. Never build other paths.
  - "http": `import httpx` for outbound requests, always with a timeout.
  - "packages": other installed third-party packages, only when clearly needed.
- Never use: {", ".join(sorted(BLOCKED_MODULES))}; or the builtins {", ".join(sorted(BLOCKED_NAMES))};
  or dunder attributes, `.open`, `.parent`, `.parents`.

test_tool.py rules:
- pytest; import the tool with `from tool import <name>`.
- Cover the main behaviour and at least one edge or invalid-input case.
- Tests run with no network: mock httpx with `unittest.mock.patch` (e.g. patch("tool.httpx.get")).
- With "files", OUTPUT_DIR points to a temporary directory, so writing through output_path is fine.
- The same import rules apply, plus pytest and unittest.mock.

Pick the smallest set of capabilities. Do not duplicate an existing tool listed below. If a
missing detail would change the tool's interface, return short clarification questions and no
spec. If a previous attempt and its failure are given, fix the cause and keep everything else.
If reviewer feedback is given, revise the previous attempt to satisfy all of it.

## Existing tools
{{tools}}

Respond only with the structured ToolDecision.
"""


def build_user_message(request: BuildToolRequest) -> str:
    answers = "\n".join(
        f"- {question_id}: {answer}" for question_id, answer in request.clarification_answers.items()
    ) or "(none)"
    message = (
        f"Tool name: {request.name}\n\n"
        f"Description (may be rough):\n{request.description}\n\n"
        f"Clarification answers:\n{answers}"
    )
    if request.previous is not None:
        message += f"\n\nPrevious attempt:\n{request.previous.model_dump_json(indent=2)}"
    if request.failure:
        message += f"\n\nThe previous attempt failed:\n{request.failure}"
    if request.feedback:
        message += "\n\nReviewer feedback:\n" + "\n".join(f"- {item}" for item in request.feedback)
    return message
