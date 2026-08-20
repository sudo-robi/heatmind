"""Auto-generate documentation from codebase structure.

Walks the project tree, extracts imports / classes / functions / docstrings and
produces a structured map that can be rendered as markdown.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import Any


def _extract_info(filepath: str) -> dict[str, Any]:
    """Parse a single Python file and return structured info."""
    try:
        with open(filepath, encoding="utf-8") as fh:
            source = fh.read()
    except (OSError, UnicodeDecodeError):
        return {"classes": [], "functions": [], "docstring": None, "imports": []}

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {"classes": [], "functions": [], "docstring": None, "imports": []}

    classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

    docstring = ast.get_docstring(tree) or None

    imports: list[str] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    return {
        "classes": classes,
        "functions": functions,
        "docstring": docstring,
        "imports": imports,
    }


def scan_modules(base_path: str = ".") -> dict[str, Any]:
    """Walk *base_path* and extract info from every Python file."""
    modules: dict[str, Any] = {}
    base = Path(base_path).resolve()

    for dirpath, _dirnames, filenames in os.walk(base):
        for fname in sorted(filenames):
            if not fname.endswith(".py"):
                continue
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, base)
            parts = Path(rel).parts
            # skip hidden dirs, __pycache__, venv
            if any(p.startswith(".") or p == "__pycache__" or p == "venv" for p in parts):
                continue

            info = _extract_info(full)
            module_name = str(Path(rel).with_suffix("")).replace(os.sep, ".")
            modules[module_name] = {
                "file": rel,
                **info,
            }
    return modules


def generate_codemap(base_path: str = ".") -> dict[str, Any]:
    """Build a complete code map for the project at *base_path*."""
    modules = scan_modules(base_path)

    # Group by top-level package
    grouped: dict[str, dict[str, Any]] = {}
    for mod_name, info in modules.items():
        top = mod_name.split(".")[0] if "." in mod_name else "root"
        if top not in grouped:
            grouped[top] = {"files": [], "classes": [], "functions": []}
        grouped[top]["files"].append(info["file"])
        grouped[top]["classes"].extend(info["classes"])
        grouped[top]["functions"].extend(info["functions"])

    # Build dependency map
    dependencies: dict[str, list[str]] = {}
    for mod_name, info in modules.items():
        deps: list[str] = []
        for imp in info["imports"]:
            # Only include internal imports
            for other_mod in modules:
                if other_mod == mod_name:
                    continue
                top_other = other_mod.split(".")[0]
                if imp.startswith(top_other) or imp == other_mod:
                    deps.append(other_mod)
                    break
        if deps:
            dependencies[mod_name] = sorted(set(deps))

    # Stats
    total_files = len(modules)
    total_classes = sum(len(m["classes"]) for m in modules.values())
    total_functions = sum(len(m["functions"]) for m in modules.values())

    total_lines = 0
    base = Path(base_path).resolve()
    for mod_info in modules.values():
        full = os.path.join(str(base), mod_info["file"])
        try:
            with open(full, encoding="utf-8") as fh:
                total_lines += sum(1 for _ in fh)
        except OSError:
            pass

    return {
        "modules": grouped,
        "dependencies": dependencies,
        "entry_points": ["streamlit_app.py", "main.py"],
        "stats": {
            "total_files": total_files,
            "total_lines": total_lines,
            "total_classes": total_classes,
            "total_functions": total_functions,
        },
    }


def codemap_to_markdown(codemap: dict[str, Any]) -> str:
    """Render a *codemap* dict as a readable markdown document."""
    lines: list[str] = ["# Code Map\n"]

    stats = codemap["stats"]
    lines.append(
        f"**{stats['total_files']}** files · "
        f"**{stats['total_lines']:,}** lines · "
        f"**{stats['total_classes']}** classes · "
        f"**{stats['total_functions']}** functions\n"
    )

    lines.append("## Entry Points\n")
    for ep in codemap["entry_points"]:
        lines.append(f"- `{ep}`")
    lines.append("")

    lines.append("## Modules\n")
    for pkg_name, pkg_info in sorted(codemap["modules"].items()):
        lines.append(f"### `{pkg_name}`\n")
        lines.append(f"**Files:** {', '.join(f'`{f}`' for f in pkg_info['files'])}\n")
        if pkg_info["classes"]:
            lines.append(f"**Classes:** {', '.join(f'`{c}`' for c in pkg_info['classes'])}\n")
        if pkg_info["functions"]:
            lines.append(f"**Functions:** {', '.join(f'`{f}`' for f in pkg_info['functions'])}\n")

    if codemap["dependencies"]:
        lines.append("## Dependencies\n")
        for mod, deps in sorted(codemap["dependencies"].items()):
            lines.append(f"- `{mod}` → {', '.join(f'`{d}`' for d in deps)}")
        lines.append("")

    return "\n".join(lines)


def save_codemap(output_path: str = "docs/CODEMAP.md") -> str:
    """Generate and save the codemap to *output_path*.

    Returns the resolved output path.
    """
    codemap = generate_codemap()
    md = codemap_to_markdown(codemap)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    return str(out.resolve())
