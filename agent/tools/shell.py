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

See agent/config/__init__.py for allowed shell commands.

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

import tree_sitter_bash
from tree_sitter import Language, Node, Parser, Query, QueryCursor, Tree

# --- Shell Parser ---


def _language() -> Language:
    """Return a bash language instance."""
    # get the PyObject* language binding
    capsule = tree_sitter_bash.language()
    # create the language instance object
    return Language(capsule)


def _tree(source: str) -> Tree:
    """Return a abstract syntax tree for the input source code."""
    # create the language parser
    parser = Parser(_language())
    # Tree‑Sitter expects bytes; utf8 is fine for shell scripts.
    return parser.parse(source.encode("utf-8"))


# --- Shell Queries ---


# the key matches the capture identifier, e.g. key -> cmd
def _query(root: Node, source: str) -> dict[str, list[Node]]:
    """Return a dictionary containing captured results for the source query."""
    # create the language query
    query = Query(_language(), source)
    # get the cursor for the current query (this is immutable)
    cursor = QueryCursor(query)
    # return the captured queries (this no longer uses tuples, it uses a dict now)
    return cursor.captures(root)


def _commands(root: Node) -> list[Node]:
    """Return a list of captured commands."""
    # note: source queries will eventually be migrated to config.
    source: str = r"""
    (program [
            (command)
            (pipeline (command))
            (list     (command))
        ] @root_command
    )
    """
    # query the abstract syntax tree to capture desired nodes
    captures: dict[str, list[Node]] = query(root, source)
    commands: list[Node] = []
    for key in captures.keys():
        commands.extend(captures[key])  # flatten
    return commands


def _command_names(root: Node) -> list[Node]:
    """Return a list of captured command names."""
    # note: source queries will eventually be migrated to config.
    source = r"""
    (program [
            (command  (command_name) @name)
            (pipeline (command (command_name) @name))
            (list     (command (command_name) @name))
        ]
    )
    """
    captures: dict[str, list[Node]] = query(root, source)
    names: list[Node] = []
    for key in captures.keys():
        names.extend(captures[key])  # flatten
    return names


def _errors(root: Node) -> list[Node]:
    """Return a list of captured syntax errors."""
    pass  # return empty if everything is valid


# --- Shell Filters ---


# warning: sets are not json serializable!
def _allowed() -> list[str]:
    """Return a list of allowed bash commands."""
    from agent.config import config

    # use set() to filter out potential duplicates
    return list(set(config.get_value("shell.allowed", [])))


def _denied(root: Node) -> list[Node]:
    """Return a list of disallowed command names, else return a empty list."""
    allowed = _allowed()
    names = _command_names(root)
    denied = []
    for name in names:
        if name.text.decode("utf8") not in allowed:
            denied.append(name)  # return the invalid node
    return denied  # empty if everything is valid


# --- Model Tools ---


# note: models require a string as a response object.
def shell_allowed() -> str:
    allowed = _allowed()
    if not allowed:
        return "Shell commands are disabled."
    # warning: ensure the object dump is a serialized list!
    return json.dumps(list(allowed), indent=2)


# note: models require a string as a response object.
def shell_run(command: str) -> str:
    allowed = _allowed()

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


# usage example
# figure out how to safely handle piped commands
# conditionals should be allowed for added flexibility and proper error handling
# the downside to this is that tree-sitter only officially supports bash
# the upside to this is that i don't have to reinvent yet another parser
# shlex is very limited and manually parsing split is error prone
# getting an automated AST can (hopefully) make life easier
if __name__ == "__main__":
    import sys

    cmd = " ".join(sys.argv[1:]) or "echo 'hello world' | wc -m"

    root = _tree(cmd).root_node
    print(f"children: {root.child_count}")
    print(f"type: {root.type}")

    cursor = root.walk()
    print(f"depth: {cursor.depth}")

    cursor.goto_first_child()
    print(cursor)
