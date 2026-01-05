import os
import ast
from pathlib import Path
from typing import Dict, Set, List

# ======================================================
# CONFIGURATION
# ======================================================

EXCLUDED_DIRS = {
    "tests",
    "scripts",    
    "venv",
    "site",
    "script",
    "ref",
    "examples",
    "docs",
    "distfit",
    "dca",
    ".github",
}

EXCLUDED_FILES = {
    "all_blocks.py",
    "all_blocks_bkp.py",
    "decide_time_conditions.py",
}

OUTPUT_FILE = "all_code.py"


# ======================================================
# FILE COLLECTION
# ======================================================

def is_excluded(path: Path) -> bool:
    if path.name in EXCLUDED_FILES:
        return True
    return any(part in EXCLUDED_DIRS for part in path.parts)


def collect_python_files(root: Path) -> List[Path]:
    files = []
    for path in root.rglob("*.py"):
        if not is_excluded(path):
            files.append(path)
    return sorted(files)


# ======================================================
# DEPENDENCY ANALYSIS
# ======================================================

def module_name(root: Path, file: Path) -> str:
    rel = file.relative_to(root).with_suffix("")
    return ".".join(rel.parts)


def extract_dependencies(tree: ast.AST) -> Set[str]:
    deps = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                deps.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                deps.add(node.module.split(".")[0])
    return deps


def build_dependency_graph(
    root: Path, files: List[Path]
) -> Dict[Path, Set[Path]]:
    module_map = {module_name(root, f): f for f in files}
    graph: Dict[Path, Set[Path]] = {f: set() for f in files}

    for file in files:
        tree = ast.parse(file.read_text(encoding="utf-8"))
        deps = extract_dependencies(tree)

        for dep in deps:
            for mod, mod_file in module_map.items():
                if mod.startswith(dep):
                    graph[file].add(mod_file)

    return graph


def topological_sort(graph: Dict[Path, Set[Path]]) -> List[Path]:
    visited = {}
    result = []

    def visit(node: Path):
        if node in visited:
            return
        visited[node] = True
        for dep in graph[node]:
            if dep != node:
                visit(dep)
        result.append(node)

    for node in graph:
        visit(node)

    return list(dict.fromkeys(result))


# ======================================================
# IMPORT HANDLING
# ======================================================

def extract_imports(tree: ast.AST) -> Set[str]:
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                imports.add(
                    f"import {a.name}" + (f" as {a.asname}" if a.asname else "")
                )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = []
            for a in node.names:
                names.append(
                    a.name + (f" as {a.asname}" if a.asname else "")
                )
            imports.add(f"from {module} import {', '.join(names)}")
    return imports


def strip_imports(source: str) -> str:
    lines = source.splitlines()
    return "\n".join(
        line for line in lines
        if not line.strip().startswith(("import ", "from "))
    ).strip()


# ======================================================
# PEP8 FORMATTING
# ======================================================

def format_pep8(code: str) -> str:
    try:
        import autopep8
        return autopep8.fix_code(code)
    except ImportError:
        return code


# ======================================================
# MAIN GENERATOR
# ======================================================

def generate_all_code(project_root: str):
    root = Path(project_root).resolve()
    files = collect_python_files(root)

    dep_graph = build_dependency_graph(root, files)
    ordered_files = topological_sort(dep_graph)

    all_imports: Set[str] = set()
    code_sections = []

    for file in ordered_files:
        source = file.read_text(encoding="utf-8")
        tree = ast.parse(source)

        all_imports |= extract_imports(tree)

        cleaned = strip_imports(source)
        cleaned = format_pep8(cleaned)

        if cleaned:
            code_sections.append(
                f"\n\n# ======================================================\n"
                f"# FILE: {file.relative_to(root)}\n"
                f"# ======================================================\n\n"
                f"{cleaned}"
            )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# ======================================================\n")
        f.write("# AUTO-GENERATED FILE — DESK PROJECT\n")
        f.write("# Dependency-aware | PEP8 formatted\n")
        f.write("# DO NOT EDIT MANUALLY\n")
        f.write("# ======================================================\n\n")

        for imp in sorted(all_imports):
            f.write(imp + "\n")

        f.write("\n\n")
        f.write("\n".join(code_sections))

    print(f"✔ all_code.py generated ({len(ordered_files)} files, dependency-ordered)")


# ======================================================
# ENTRY POINT
# ======================================================

if __name__ == "__main__":
    generate_all_code(".")
