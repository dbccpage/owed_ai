"""Generate the class-by-class developer reference in docs/developer/reference/.

Reads the source with ``ast`` (nothing is imported or executed) and writes one
Markdown page per module plus an index. Run after changing public code:

    uv run python scripts/build_reference.py          # rewrite the pages
    uv run python scripts/build_reference.py --check  # fail if they are stale
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "anomalon_workbench"
OUT = ROOT / "docs" / "developer" / "reference"
UNDOCUMENTED = "_No docstring yet._"


def public(name: str) -> bool:
    return not name.startswith("_") or name == "__init__"


def signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = ast.unparse(node.args)
    returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    return f"{prefix} {node.name}({args}){returns}"


def doc(node: ast.AST) -> str:
    text = ast.get_docstring(node)  # type: ignore[arg-type]
    return text.strip() if text else UNDOCUMENTED


def first_line(node: ast.AST) -> str:
    return doc(node).splitlines()[0]


def render_function(node: ast.FunctionDef | ast.AsyncFunctionDef, level: str) -> list[str]:
    return [f"{level} `{node.name}`", "", "```python", signature(node), "```", "", doc(node), ""]


def render_class(node: ast.ClassDef) -> list[str]:
    bases = ", ".join(ast.unparse(b) for b in node.bases)
    lines = [f"## class `{node.name}`" + (f" ({bases})" if bases else ""), "", doc(node), ""]
    fields = [
        f"- `{ast.unparse(item.target)}: {ast.unparse(item.annotation)}`"
        for item in node.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name) and public(item.target.id)
    ]
    if fields:
        lines += ["Fields:", "", *fields, ""]
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and public(item.name):
            lines += render_function(item, "###")
    return lines


def render_module(path: Path) -> tuple[str, str, int]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    module = "anomalon_workbench" if path.stem == "__init__" else f"anomalon_workbench.{path.stem}"
    lines = [f"# `{module}`", "", f"Source: `src/anomalon_workbench/{path.name}`", "", doc(tree), ""]
    count = 0
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and public(node.name):
            lines += render_class(node)
            count += 1
    functions = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and public(n.name)]
    if functions:
        lines += ["## Functions", ""]
        for node in functions:
            lines += render_function(node, "###")
    return module, "\n".join(lines).rstrip() + "\n", count


def build() -> dict[Path, str]:
    pages: dict[Path, str] = {}
    rows = []
    for path in sorted(PACKAGE.glob("*.py")):
        module, text, classes = render_module(path)
        name = f"{module}.md"
        pages[OUT / name] = text
        rows.append(f"| [`{module}`]({name}) | {classes} | {first_line(ast.parse(path.read_text(encoding='utf-8')))} |")
    index = [
        "# Developer reference",
        "",
        "Generated from the source by `scripts/build_reference.py`; do not edit by hand.",
        "One page per module, listing each public class, its fields and methods, and the",
        "module's public functions, with their docstrings.",
        "",
        "| Module | Classes | Summary |",
        "| --- | --- | --- |",
        *rows,
        "",
    ]
    pages[OUT / "README.md"] = "\n".join(index)
    return pages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if the committed pages differ")
    args = parser.parse_args()
    pages = build()
    stale = sorted(
        str(p.relative_to(ROOT))
        for p, text in pages.items()
        if not p.exists() or p.read_text(encoding="utf-8") != text
    )
    extra = sorted(str(p.relative_to(ROOT)) for p in OUT.glob("*.md") if p not in pages) if OUT.exists() else []
    if args.check:
        if stale or extra:
            print("Developer reference is stale; run scripts/build_reference.py:", *stale, *extra, sep="\n  ")
            return 1
        print(f"Developer reference is current ({len(pages)} pages).")
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    for p in extra:
        (ROOT / p).unlink()
    for p, text in pages.items():
        p.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {len(pages)} pages to {OUT.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
