from agent_builder.builders.tool.checks import check_tool
from agent_builder.builders.tool.sandbox import run_tests
from agent_builder.core.schemas import ToolSpec

CODE = '''import json

def word_count(text: str) -> str:
    """Count words.
    Use when: an agent needs a word count."""
    return json.dumps({"words": len(text.split())})
'''
TESTS = '''import json
from tool import word_count

def test_counts_words():
    assert json.loads(word_count("a b c"))["words"] == 3
'''


def _spec(**overrides) -> ToolSpec:
    base = {"name": "word_count", "description": "d", "use_when": "u", "code": CODE, "tests": TESTS, "rationale": "r"}
    return ToolSpec(**{**base, **overrides})


def test_imports_are_gated_by_declared_capabilities():
    http_code = "import httpx\n" + CODE
    assert check_tool(_spec()) == []
    assert any("import 'httpx'" in p for p in check_tool(_spec(code=http_code)))
    assert check_tool(_spec(code=http_code, capabilities=["http"])) == []
    assert any("import 'os'" in p for p in check_tool(_spec(code="import os\n" + CODE, capabilities=["packages"])))


def test_sandbox_runs_passing_tests_and_reports_failures():
    assert run_tests(_spec()).passed
    failing = run_tests(_spec(tests=TESTS.replace("== 3", "== 4")))
    assert not failing.passed
    assert "assert 3 == 4" in failing.output
