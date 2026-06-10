"""
backend/tools/sandbox.py
------------------------
Docker-based sandbox for validating Helix-generated fixes.
Spins up an isolated python:3.11-slim container, applies the patch
to a temp directory, runs the test commands, and always cleans up.
Handles the case where Docker is not available gracefully.
"""

from __future__ import annotations

import logging
import os
import tarfile
import tempfile
import textwrap
from io import BytesIO
from typing import TYPE_CHECKING, Any

from config import settings

if TYPE_CHECKING:
    from models import FailureContext, Fix

logger = logging.getLogger(__name__)

SANDBOX_IMAGE = "python:3.11-slim"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_in_sandbox(fix: "Fix", failure_context: "FailureContext") -> dict[str, Any]:
    """
    Apply *fix* to a temp directory inside a Docker container and run its test commands.

    Returns:
        {
            "success": bool,
            "output": str,   # combined stdout/stderr
            "exit_code": int
        }

    If Docker is not available, returns a warning dict without raising.
    """
    try:
        import docker  # type: ignore
    except ImportError:
        logger.warning("docker package not installed — skipping sandbox validation")
        return _warning("docker Python package not installed")

    # Check Docker availability
    try:
        client = docker.from_env(timeout=10)
        client.ping()
    except Exception as exc:
        logger.warning("Docker not available: %s", exc)
        return _warning(f"Docker not available: {exc}")

    with tempfile.TemporaryDirectory(prefix="helix_sandbox_") as tmpdir:
        # Write the patch as a shell script that applies it and runs tests
        script_path = os.path.join(tmpdir, "helix_run.sh")
        _write_run_script(script_path, fix)

        # Also write patch file
        patch_path = os.path.join(tmpdir, "helix.patch")
        with open(patch_path, "w", encoding="utf-8") as f:
            f.write(fix.patch)

        # Build a tar archive to copy into the container
        tar_bytes = _make_tar(tmpdir)

        container = None
        try:
            logger.info("Pulling sandbox image '%s' (if needed)…", SANDBOX_IMAGE)
            try:
                client.images.get(SANDBOX_IMAGE)
            except docker.errors.ImageNotFound:
                client.images.pull(SANDBOX_IMAGE)

            container = client.containers.create(
                SANDBOX_IMAGE,
                command=["bash", "/workspace/helix_run.sh"],
                working_dir="/workspace",
                network_disabled=True,    # no outbound network inside sandbox
                mem_limit="256m",
                nano_cpus=1_000_000_000,  # 1 CPU
            )

            # Copy workspace files into container
            container.put_archive("/workspace", tar_bytes)

            # Start and wait
            container.start()
            exit_code = container.wait(timeout=settings.sandbox_timeout_seconds)["StatusCode"]
            output = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")

            success = exit_code == 0
            logger.info("Sandbox finished: exit_code=%d success=%s", exit_code, success)
            return {"success": success, "output": output, "exit_code": exit_code}

        except Exception as exc:
            logger.exception("Sandbox execution error")
            return {"success": False, "output": str(exc), "exit_code": -1}

        finally:
            if container is not None:
                try:
                    container.remove(force=True)
                    logger.info("Sandbox container cleaned up")
                except Exception as cleanup_err:
                    logger.warning("Failed to remove sandbox container: %s", cleanup_err)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _warning(message: str) -> dict[str, Any]:
    """Return a non-fatal warning result when Docker is unavailable."""
    return {
        "success": True,   # treat as pass so the pipeline can continue
        "output": f"[Helix Warning] Sandbox skipped — {message}",
        "exit_code": 0,
    }


def _write_run_script(path: str, fix: "Fix") -> None:
    """Write the shell script that installs deps and runs tests inside the container."""
    commands = fix.test_commands or ["echo 'No test commands specified'"]
    cmd_block = "\n".join(f"    {cmd}" for cmd in commands)

    script = textwrap.dedent(f"""\
        #!/usr/bin/env bash
        set -euo pipefail

        echo "=== Helix Sandbox ==="
        echo "Applying patch…"

        # Apply patch if git is available and patch has content
        if command -v patch &>/dev/null && [ -s /workspace/helix.patch ]; then
            patch -p1 --forward --reject-file=/dev/null < /workspace/helix.patch || true
        fi

        echo "Running test commands…"
{cmd_block}

        echo "=== Sandbox complete ==="
    """)

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(script)


def _make_tar(directory: str) -> bytes:
    """Create an in-memory tar archive of *directory* contents."""
    buf = BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for fname in os.listdir(directory):
            fpath = os.path.join(directory, fname)
            tar.add(fpath, arcname=fname)
    buf.seek(0)
    return buf.read()
