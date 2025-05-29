"""
Module: agent.tools.shell

My current idea is to:
- Create a group named `agent`.
- `chown`/`chmod` the scope to the group.
- Enable permissions for the agent to access allowed CLI tools.

This has its own risks, e.g. privelage escalation, destructive actions, impersonation, etc.
Limiting the behavior here is crucial to ensure the environment remains secure.
This is a simple and limited implementation, but it has issues due to the nature of how
this could go in practice.

Warning: Running untrusted code is never safe, sandboxing cannot change this.
See https://wiki.archlinux.org/title/Firejail for sandboxing.
"""

import shlex
import subprocess


def shell(command: str) -> str:
    allowed = ["tree", "ls", "cat", "head", "tail", "grep", "git"]
    try:
        args = shlex.split(command)
        if not args or args[0] not in allowed:
            return "Error: Command not allowed."
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=True,
            shell=False,
        )
        output = result.stdout.strip()
        err = result.stderr.strip()
        if err:
            return f"StandardOutput:\n{output}\nStandardError:\n{err}"
        return output or "(No output)"
    except subprocess.CalledProcessError as e:
        result = f"Error: ReturnCode: {e.returncode}\n"
        if e.stderr:
            result += f"StandardError:\n{e.stderr.strip()}\n"
        if e.stdout:
            result += f"StandardOutput:\n{e.stdout.strip()}\n"
        return result
    except Exception as e:
        return f"Error: {str(e)}"
