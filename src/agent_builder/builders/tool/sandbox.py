"""Run a generated tool's tests in an isolated subprocess.

Isolation: a fresh temp directory as cwd and HOME, OUTPUT_DIR inside it, a stripped environment,
a timeout, and no network (`unshare -rn`, a user + network namespace that needs no root). If
`unshare` is unavailable the tests still run, and the report says `isolated: false`.
"""
import os
import shutil
import subprocess
import sys
from functools import cache
from pathlib import Path
from tempfile import TemporaryDirectory

from ...config import settings
from ...core.schemas import TestReport, ToolSpec
from .checks import check_tool
from .codegen import write_tool_files

TIMEOUT_SECONDS = 60
OUTPUT_TAIL = 3000


@cache
def _network_isolation_available() -> bool:
    try:
        return subprocess.run(["unshare", "-rn", "true"], capture_output=True, timeout=5, check=False).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def run_tests(spec: ToolSpec) -> TestReport:
    """Static checks first; only code that passes them is executed."""
    problems = check_tool(spec)
    isolated = _network_isolation_available()
    if problems:
        return TestReport(passed=False, problems=problems, isolated=isolated)

    with TemporaryDirectory(prefix="tool-sandbox-") as tmp:
        root = Path(tmp)
        write_tool_files(spec, root)
        (root / "tools").mkdir()
        (root / "tools" / "__init__.py").write_text("", encoding="utf-8")
        shutil.copy(settings.mcp_tools_dir / "sdk.py", root / "tools" / "sdk.py")

        command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "test_tool.py"]
        if isolated:
            command = ["unshare", "-rn", *command]
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": tmp,
            "OUTPUT_DIR": str(root / "outputs"),
            "PYTHONPATH": tmp,
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        try:
            result = subprocess.run(
                command, cwd=tmp, env=env, capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return TestReport(passed=False, output=f"tests timed out after {TIMEOUT_SECONDS}s", isolated=isolated)
    output = (result.stdout + result.stderr).strip()
    return TestReport(passed=result.returncode == 0, output=output[-OUTPUT_TAIL:], isolated=isolated)
