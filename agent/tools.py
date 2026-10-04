import os
from pathlib import Path

from langchain_core.tools import tool

ROOT = Path.cwd().resolve()
SKIP_DIRS = {".git", "agent", "__pycache__", ".pytest_cache", ".venv", "venv", "node_modules"}


def _safe_path(path: str) -> Path:
    full = (ROOT / path).resolve()
    if full != ROOT and ROOT not in full.parents:
        raise ValueError(f"path outside repository: {path}")
    return full


@tool
def list_files() -> str:
    """List all files in the repository (relative paths)."""
    found = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            found.append(os.path.relpath(os.path.join(dirpath, name), ROOT).replace("\\", "/"))
    return "\n".join(sorted(found))


@tool
def read_file(path: str) -> str:
    """Read a text file from the repository by relative path."""
    try:
        return _safe_path(path).read_text(encoding="utf-8")
    except Exception as e:
        return f"ERROR: {e}"


@tool
def edit_file(path: str, old_text: str, new_text: str) -> str:
    """Replace one exact occurrence of old_text with new_text in a file.
    Fails if old_text is not found exactly once."""
    try:
        full = _safe_path(path)
        content = full.read_text(encoding="utf-8")
    except Exception as e:
        return f"ERROR: {e}"
    count = content.count(old_text)
    if count == 0:
        return "ERROR: old_text not found in file. Read the file again and copy the text exactly."
    if count > 1:
        return f"ERROR: old_text found {count} times. Include more surrounding context so it is unique."
    full.write_text(content.replace(old_text, new_text, 1), encoding="utf-8")
    return f"OK: edited {path}"


TOOLS = [list_files, read_file, edit_file]
