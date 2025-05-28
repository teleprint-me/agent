"""
Module: agent.tools.cli

My current idea is to:
- Create a group named `agent`.
- `chown`/`chmod` the scope to the group.
- Enable permissions for the agent to access allowed CLI tools.

This has its own risks, e.g. privelage escalation, destructive actions, impersonation, etc.
Limiting the behavior here is crucial to ensure the environment remains secure.
This is a simple and limited implementation, but it has issues due to the nature of how
this could go in practice.
"""

import subprocess


def shell(command: str) -> str:
    # Optionally: validate allowed commands
    # Optionally: log for review, or block if not approved
    # Optionally: sandbox (e.g. chroot, seccomp, firejail)

    allowed = ["ls", "cat", "head", "tail", "grep", "git"]
    if command.split()[0] not in allowed:
        return "Error: Command not allowed."
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            shell=False,  # NOTE: Enabling this is dangerous!
        )
    except subprocess.CalledProcessError as e:
        result = f"CalledProcessError: ReturnCode: {e.returncode}\n"
        if e.stderr:
            result += f"StandardError:\n{e.stderr}\n"
        if e.stdout:
            result += f"StandardOutput:\n{e.stdout}\n"
        return result
