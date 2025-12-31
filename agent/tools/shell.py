# agent/tools/shell.py
"""
Warning: Running untrusted code is never safe - sandboxing cannot change this.
See https://wiki.archlinux.org/title/Firejail for sandboxing.
Warning: Agents should be given the least amount privilege possible.
See https://unix.stackexchange.com/q/219922 for setting up a user for agents.

My current idea is to:
- Create a group named `agent`.
- `chown`/`chmod` the scope to the group.
- Enable permissions for the agent to access allowed CLI tools.

This has its own risks, e.g. privilege escalation, destructive actions, impersonation, etc.
Limiting the behavior here is crucial to ensure the environment remains secure by default.

Models may hallucinate or become creative in problem solving taking unexpected paths to achieve a goal.

- Under no circumstance should the shell option ever be set to True.
- Users should not enable destructive actions such as rm, rmdir, etc.
- Piping must be parsed and handled appropriately to limit scope.
- Commands should be limited to what is allowed and optionally disabled.

Piping commands safely is possible without enabling the shell. It's a bit involved though.

1. https://stackoverflow.com/a/13332300/15147156

    ps = subprocess.Popen(('ps', '-A'), stdout=subprocess.PIPE)
    output = subprocess.check_output(('grep', 'process_name'), stdin=ps.stdout)
    ps.wait()

2. https://stackoverflow.com/a/9164238/15147156

    some_string = b'input_data'
    sort_out = open('outfile.txt', 'wb', 0)
    sort_in = subprocess.Popen('sort', stdin=subprocess.PIPE, stdout=sort_out).stdin
    subprocess.Popen(
        ['awk', '-f', 'script.awk'],
        stdout=sort_in,
        stdin=subprocess.PIPE).communicate(some_string)
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
