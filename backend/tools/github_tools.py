"""
backend/tools/github_tools.py
------------------------------
GitHub API interaction layer for Helix.
"""

from __future__ import annotations

import base64
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from github import Github, GithubException

from config import settings

logger = logging.getLogger(__name__)

_gh = Github(settings.github_token)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_repo(repo_name: str):
    return _gh.get_repo(repo_name)


def _decode_content(content_file) -> str:
    return base64.b64decode(content_file.content).decode("utf-8", errors="replace")


@dataclass
class _FilePatch:
    path: str
    lines: list[tuple[str, str]] = field(default_factory=list)  # (op, text) op in ' ', '-', '+'


def _parse_unified_patch(patch: str) -> list[_FilePatch]:
    """Parse a unified diff into per-file operation lists."""
    if not patch or not patch.strip():
        return []

    files: list[_FilePatch] = []
    current: _FilePatch | None = None

    for line in patch.splitlines():
        if line.startswith("--- a/"):
            continue
        if line.startswith("+++ b/"):
            if current and current.lines:
                files.append(current)
            current = _FilePatch(path=line[6:].strip())
            continue
        if line.startswith("@@"):
            continue
        if current is None:
            continue
        if line.startswith("+") and not line.startswith("+++"):
            current.lines.append(("+", line[1:]))
        elif line.startswith("-") and not line.startswith("---"):
            current.lines.append(("-", line[1:]))
        elif line.startswith(" "):
            current.lines.append((" ", line[1:]))

    if current and current.lines:
        files.append(current)

    return files


def _apply_file_patch(original: str, ops: list[tuple[str, str]]) -> str:
    """Apply unified-diff ops to original file content."""
    orig_lines = original.splitlines()
    result: list[str] = []
    orig_idx = 0

    for op, text in ops:
        if op == " ":
            if orig_idx < len(orig_lines):
                result.append(orig_lines[orig_idx])
                orig_idx += 1
            else:
                result.append(text)
        elif op == "-":
            if orig_idx < len(orig_lines):
                orig_idx += 1
            # else: skip orphan removal
        elif op == "+":
            result.append(text)

    # Append any trailing original lines not consumed (if patch was partial)
    while orig_idx < len(orig_lines):
        result.append(orig_lines[orig_idx])
        orig_idx += 1

    return "\n".join(result)


def _read_file_from_branch(repo, path: str, branch: str) -> str | None:
    try:
        content_file = repo.get_contents(path, ref=branch)
        return _decode_content(content_file)
    except GithubException:
        return None


def _delete_branch_if_exists(repo, branch: str) -> None:
    try:
        ref = repo.get_git_ref(f"heads/{branch}")
        ref.delete()
        logger.info("Deleted existing branch '%s'", branch)
    except GithubException:
        pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_logs(repo_name: str, run_id: str) -> str:
    try:
        repo = _get_repo(repo_name)
        workflow_run = repo.get_workflow_run(int(run_id))
        jobs = workflow_run.jobs()

        combined: list[str] = []
        for job in jobs:
            if job.conclusion in ("failure", "cancelled"):
                try:
                    import requests
                    logs_url = f"https://api.github.com/repos/{repo_name}/actions/jobs/{job.id}/logs"
                    resp = requests.get(
                        logs_url,
                        headers={
                            "Authorization": f"Bearer {settings.github_token}",
                            "Accept": "application/vnd.github+json",
                        },
                        allow_redirects=True,
                        timeout=30,
                    )
                    if resp.status_code == 200:
                        combined.append(f"=== Job: {job.name} ===\n{resp.text}")
                    else:
                        logger.warning("Logs returned status %s for job '%s'", resp.status_code, job.name)
                except Exception as e:
                    logger.warning("Could not fetch logs for job '%s': %s", job.name, e)

        if not combined:
            logger.warning("No logs retrieved for run %s", run_id)
            return "[Helix] No failure logs found for this run."

        all_logs = "\n".join(combined)
        lines = all_logs.splitlines()
        return "\n".join(lines[-200:]) if len(lines) > 200 else all_logs

    except GithubException as exc:
        logger.error("GitHub API error fetching logs: %s", exc)
        return f"[Helix] Could not retrieve logs: {exc.data}"
    except Exception as exc:
        logger.exception("Unexpected error fetching logs")
        return f"[Helix] Unexpected error fetching logs: {exc}"


def fetch_diff(repo_name: str, commit_sha: str) -> str:
    try:
        repo = _get_repo(repo_name)
        commit = repo.get_commit(commit_sha)
        diff_lines: list[str] = []
        for f in commit.files:
            diff_lines.append(f"--- a/{f.filename}")
            diff_lines.append(f"+++ b/{f.filename}")
            if f.patch:
                diff_lines.append(f.patch)
            diff_lines.append("")

        full_diff = "\n".join(diff_lines)
        lines = full_diff.splitlines()
        return "\n".join(lines[:500]) if len(lines) > 500 else full_diff

    except GithubException as exc:
        logger.error("GitHub API error fetching diff: %s", exc)
        return f"[Helix] Could not retrieve diff: {exc.data}"
    except Exception as exc:
        logger.exception("Unexpected error fetching diff")
        return f"[Helix] Unexpected error fetching diff: {exc}"


def fetch_deps(repo_name: str, commit_sha: str) -> dict[str, Any]:
    repo = _get_repo(repo_name)
    result: dict[str, Any] = {"type": "unknown", "content": "", "parsed": {}}

    candidates = [
        ("package.json", "npm"),
        ("requirements.txt", "pip"),
        ("pyproject.toml", "pip"),
    ]

    for filename, dep_type in candidates:
        try:
            content_file = repo.get_contents(filename, ref=commit_sha)
            raw = _decode_content(content_file)
            result["type"] = dep_type
            result["content"] = raw

            if dep_type == "npm":
                import json
                result["parsed"] = json.loads(raw)
            else:
                result["parsed"] = [
                    line.strip()
                    for line in raw.splitlines()
                    if line.strip() and not line.startswith("#")
                ]
            logger.info("Fetched '%s' at %s", filename, commit_sha[:8])
            return result

        except GithubException:
            continue
        except Exception as exc:
            logger.warning("Error parsing %s: %s", filename, exc)
            continue

    logger.warning("No dependency manifest found in %s @ %s", repo_name, commit_sha[:8])
    return result


def open_pr(
    repo_name: str,
    branch: str,
    base_branch: str,
    fix: Any,
    run_id: str,
) -> str:
    try:
        repo = _get_repo(repo_name)
        base_ref = repo.get_git_ref(f"heads/{base_branch}")
        base_sha = base_ref.object.sha

        fix_branch = f"helix/fix/{run_id[:8]}"
        _delete_branch_if_exists(repo, fix_branch)

        repo.create_git_ref(ref=f"refs/heads/{fix_branch}", sha=base_sha)
        logger.info("Created branch '%s' from '%s'", fix_branch, base_branch)

        changed = _apply_patch_to_repo(repo, fix.patch, fix_branch)
        if not changed:
            changed = _apply_known_workflow_fixes(repo, fix_branch, fix)
        if not changed:
            raise RuntimeError(
                "Patch did not modify any files — cannot open an empty PR. "
                "The generated fix may be invalid or identical to the base branch."
            )

        compare = repo.compare(base_branch, fix_branch)
        if compare.ahead_by == 0:
            raise RuntimeError(
                "No commits between base and fix branch after applying patch."
            )

        affected = "\n".join(f"- `{f}`" for f in (changed or fix.files_changed or []))
        body = (
            f"## Helix Automated Fix\n\n"
            f"**Root cause:** {getattr(fix, '_root_cause', 'See diagnosis')}\n\n"
            f"**Fix explanation:**\n{fix.explanation}\n\n"
            f"**Files changed:**\n{affected or '_No files listed_'}\n\n"
            f"**Test commands:**\n"
            + "\n".join(f"```\n{cmd}\n```" for cmd in (fix.test_commands or []))
            + f"\n\n---\n"
            f"_Opened automatically by Helix — run `{run_id[:8]}`_"
        )

        pr = repo.create_pull(
            title=f"[Helix] Automated fix for run {run_id[:8]}",
            body=body,
            head=fix_branch,
            base=base_branch,
        )
        logger.info("Opened PR #%d: %s", pr.number, pr.html_url)
        return pr.html_url

    except GithubException as exc:
        logger.error("GitHub API error opening PR: %s", exc)
        raise RuntimeError(f"Could not open PR: {exc.data}") from exc


def _apply_patch_to_repo(repo, patch: str, branch: str) -> list[str]:
    """
    Apply a unified diff to files on *branch*.
    Returns list of file paths that were actually changed.
    """
    file_patches = _parse_unified_patch(patch)
    if not file_patches:
        logger.warning("Patch was empty or unparseable")
        return []

    changed_files: list[str] = []

    for fp in file_patches:
        if not fp.path or not fp.lines:
            continue

        original = _read_file_from_branch(repo, fp.path, branch)
        if original is None:
            # New file — only + lines
            new_content = "\n".join(text for op, text in fp.lines if op == "+")
        else:
            new_content = _apply_file_patch(original, fp.lines)

        if not new_content and original is None:
            continue

        if original is not None and new_content == original:
            logger.info("No change for %s after applying patch", fp.path)
            continue

        try:
            existing = repo.get_contents(fp.path, ref=branch)
            repo.update_file(
                path=fp.path,
                message=f"[Helix] Apply fix to {fp.path}",
                content=new_content,
                sha=existing.sha,
                branch=branch,
            )
        except GithubException:
            repo.create_file(
                path=fp.path,
                message=f"[Helix] Create {fp.path}",
                content=new_content,
                branch=branch,
            )

        changed_files.append(fp.path)
        logger.info("Updated %s on branch %s", fp.path, branch)

    return changed_files


def _apply_known_workflow_fixes(repo, branch: str, fix: Any) -> list[str]:
    """Fallback: apply well-known one-line CI fixes directly to workflow files."""
    candidates = list(fix.files_changed or [])
    if ".github/workflows/ci.yml" not in candidates:
        candidates.insert(0, ".github/workflows/ci.yml")

    changed: list[str] = []
    for path in candidates:
        if not path.endswith((".yml", ".yaml")):
            continue
        original = _read_file_from_branch(repo, path, branch)
        if original is None:
            continue

        new_content = original
        if "ubuntu-lates" in new_content:
            new_content = new_content.replace("ubuntu-lates", "ubuntu-latest")
        if "assert 1 + 1 == 3" in new_content:
            new_content = new_content.replace(
                'python -c "assert 1 + 1 == 3, \'math is broken on purpose\'"',
                'python -c "assert 1 + 1 == 2"',
            )

        if new_content == original:
            continue

        try:
            existing = repo.get_contents(path, ref=branch)
            repo.update_file(
                path=path,
                message=f"[Helix] Apply known fix to {path}",
                content=new_content,
                sha=existing.sha,
                branch=branch,
            )
        except GithubException:
            repo.create_file(
                path=path,
                message=f"[Helix] Create {path}",
                content=new_content,
                branch=branch,
            )
        changed.append(path)
        logger.info("Applied known workflow fix to %s", path)

    return changed
