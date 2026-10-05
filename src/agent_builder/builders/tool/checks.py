"""Static safety checks on generated tool code and tests, before anything executes.

These are a first line of defence, not a sandbox: a determined author can evade static checks,
which is why every tool also needs human approval. The rules:
- tool.py defines exactly one public function, named like the tool, typed, with a docstring.
- Imports come from a pure-computation allowlist, widened only by declared capabilities.
- Process, filesystem, introspection, and dynamic-code modules and builtins are never allowed.
"""
import ast

from ...core.schemas import ToolSpec

PURE_MODULES = {
    "base64", "bisect", "calendar", "collections", "copy", "csv", "dataclasses", "datetime",
    "decimal", "difflib", "enum", "fractions", "functools", "hashlib", "heapq", "html", "io",
    "itertools", "json", "math", "operator", "pprint", "random", "re", "statistics", "string",
    "textwrap", "typing", "unicodedata", "urllib.parse", "uuid", "zoneinfo",
}
CAPABILITY_MODULES = {"files": {"tools.sdk"}, "http": {"httpx"}}
TEST_MODULES = {"pytest", "unittest.mock", "tool"}
# Never allowed, even with the `packages` capability.
BLOCKED_MODULES = {
    "builtins", "code", "ctypes", "gc", "glob", "importlib", "inspect", "marshal",
    "multiprocessing", "os", "pathlib", "pickle", "pty", "shutil", "signal", "socket",
    "subprocess", "sys", "tempfile", "threading",
}
BLOCKED_NAMES = {
    "__import__", "breakpoint", "compile", "delattr", "eval", "exec", "getattr", "globals",
    "input", "locals", "open", "setattr", "vars",
}
# `io.open(...)`, `path.open()`, and walking up from an output path.
BLOCKED_ATTRS = {"open", "parent", "parents", "system", "popen"}


def _module_allowed(module: str, allowed: set[str], any_package: bool) -> bool:
    root = module.split(".")[0]
    if root in BLOCKED_MODULES or module in BLOCKED_MODULES:
        return False
    if any(module == name or module.startswith(f"{name}.") for name in allowed):
        return True
    return any_package and root not in {"tools"}


def _check_source(source: str, filename: str, allowed: set[str], any_package: bool) -> list[str]:
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as exc:
        return [f"{filename}: syntax error at line {exc.lineno}: {exc.msg}"]
    problems = []
    for node in ast.walk(tree):
        modules = []
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                problems.append(f"{filename}:{node.lineno}: relative imports are not allowed")
            modules = [node.module or ""]
        for module in modules:
            if not _module_allowed(module, allowed, any_package):
                problems.append(f"{filename}:{node.lineno}: import '{module}' is not allowed")
        if isinstance(node, ast.Name) and node.id in BLOCKED_NAMES:
            problems.append(f"{filename}:{node.lineno}: '{node.id}' is not allowed")
        if isinstance(node, ast.Attribute) and (node.attr.startswith("__") or node.attr in BLOCKED_ATTRS):
            problems.append(f"{filename}:{node.lineno}: attribute '{node.attr}' is not allowed")
    return problems


def _check_shape(spec: ToolSpec) -> list[str]:
    try:
        tree = ast.parse(spec.code)
    except SyntaxError:
        return []  # reported by _check_source
    public = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and not node.name.startswith("_")
    ]
    if [fn.name for fn in public] != [spec.name]:
        return [f"tool.py must define exactly one public function named '{spec.name}'"]
    fn = public[0]
    problems = []
    args = fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs
    if any(arg.annotation is None for arg in args) or fn.returns is None:
        problems.append(f"'{spec.name}' must annotate every parameter and its return type")
    if fn.args.vararg or fn.args.kwarg:
        problems.append(f"'{spec.name}' must not take *args or **kwargs")
    if not ast.get_docstring(fn):
        problems.append(f"'{spec.name}' needs a docstring")
    for node in tree.body:
        if not isinstance(
            node, ast.Import | ast.ImportFrom | ast.FunctionDef | ast.AsyncFunctionDef | ast.Assign
            | ast.AnnAssign | ast.Expr
        ):
            problems.append(f"tool.py:{node.lineno}: only imports, functions and constants at top level")
        elif isinstance(node, ast.Expr) and not isinstance(node.value, ast.Constant):
            problems.append(f"tool.py:{node.lineno}: no top-level calls or expressions")
    return problems


def check_tool(spec: ToolSpec) -> list[str]:
    """Every problem found; an empty list means the code may be run in the sandbox."""
    allowed = set(PURE_MODULES)
    for capability in spec.capabilities:
        allowed |= CAPABILITY_MODULES.get(capability, set())
    any_package = "packages" in spec.capabilities
    return (
        _check_shape(spec)
        + _check_source(spec.code, "tool.py", allowed, any_package)
        + _check_source(spec.tests, "test_tool.py", allowed | TEST_MODULES, any_package)
    )
