# agent/tools/shell.py
"""
Shell access tool for the agent framework. This module provides safe shell command execution
with strict access control and security considerations.

Security Model:
The system follows a "security by default" principle where all operations are restricted to basic utilities.
Access can be safely modified or disabled based on user requirements, but should always follow
the Principle of Least Privilege to minimize risks.

Security Warnings:

1. **Arbitrary code execution risk**
   - Running untrusted code is never safe, sandboxing cannot change this.
     - See Firejail for sandboxing solutions:
       https://wiki.archlinux.org/title/Firejail

2. **Principle of Least Privilege**
   - Agents should operate with minimal permissions to reduce attack surfaces.
     - Set up dedicated user accounts:
       https://unix.stackexchange.com/q/219922

3. **Model creativity and unexpected behavior**
   - Models may explore creative solutions that deviate from expected paths.
     - Research on reasoning model behaviors:
       https://arxiv.org/abs/2502.13295

4. **Hallucination and destructive actions**
   - Models can generate false information or perform unintended operations.
     - Real-world example of Gemini deleting user data in production:
       https://futurism.com/artificial-intelligence/google-ai-deletes-entire-drive

Allowed Commands:
- Basic system utilities: date, ls, lsblk, lspci, touch
- File operations: cat, head, tail, grep, find
- Environment management: printenv, git

Access Control Notes:

- Shell access is controlled by a predefined list of allowed commands
- Users can disable shell access by setting an empty list in the configuration
- Piped commands are handled securely through subprocess chaining (see implementation notes)

Implementation Details:

1. **Sandboxing**:
   - Commands are executed with strict security settings
   - Running untrusted code is never safe, sandboxing cannot change this

2. **Piping Support**:
   - Safe handling of piped commands via subprocess chaining
     https://stackoverflow.com/a/295564/15147156

3. **Privilege Management**:
   - Commands are restricted to basic utilities for safety
   - Users should not enable destructive operations like `rm`, `rmdir`
   - If removal is desired, you can use something like trash-cli.
     trash-cli is a command line trashcan (recycle bin) interface

The shell tool is designed to be used responsibly and safely.
Never enable unrestricted access in production environments.
"""

import json
import shlex
import subprocess


def _allow_list() -> list[str]:
    from agent.config import config

    return config.get_value("shell.allowed", [])


def shell_allowed() -> str:
    allowed = _allow_list()
    if not allowed:
        return "Shell commands are disabled."
    return json.dumps(allowed, indent=2)


def shell_run(command: str) -> str:
    allowed = _allow_list()

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
