"""Patch apply/rollback helpers, built on unidiff for parsing and validation."""

from unidiff import PatchSet


def parse_diff(diff_text: str) -> PatchSet:
    return PatchSet(diff_text)


def validate_patch(diff_text: str, max_lines: int, denied_paths: list[str]) -> tuple[bool, str]:
    """Guardrail check before a patch is ever applied.

    Rejects patches that touch denied paths (e.g. workflow files, secrets) or
    exceed max_lines of changes.
    """
    patch = parse_diff(diff_text)
    changed_lines = sum(f.added + f.removed for f in patch)
    if changed_lines > max_lines:
        return False, f"patch too large: {changed_lines} lines > {max_lines}"
    for f in patch:
        if any(f.path.startswith(p) for p in denied_paths):
            return False, f"patch touches denied path: {f.path}"
    return True, ""


def apply_patch(repo_path: str, diff_text: str) -> None:
    """Apply diff_text to the working tree at repo_path.

    TODO: shell out to `git apply` (or `git apply --check` first) inside repo_path.
    """
    raise NotImplementedError
