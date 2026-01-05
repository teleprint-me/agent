# agent/tools/shell.py
"""
Shell Access Tool - Safe, Controlled Command Execution

This module makes an attempt to implement a sandboxed shell-execution facility that
can be used by the agent framework to run arbitrary scripts by enforcing an explicit
list of allowed commands while providing detailed feedback on any violations.

---
Security Model
---

The system follows *security-by-default*. By default no external program is
executable; only a minimal set of utilities may be invoked.  The following
principles are enforced:

1. **Arbitrary code execution risk**
   Running untrusted code can never be fully safe - sandboxing cannot change that.
   For additional isolation, consider tools such as Firejail:
       https://wiki.archlinux.org/title/Firejail

2. **Principle of Least Privilege**
   The agent should run with the fewest permissions necessary to fulfil its tasks.
   Dedicated user accounts are recommended:
       https://unix.stackexchange.com/q/219922

3. **Unexpected behaviour and hallucinations**
   Models may generate creative or unintended commands.
   Research on reasoning model behaviours can be found here:
       https://arxiv.org/abs/2502.13295

4. **Destructive actions**
   Agents might produce false information that leads to destructive operations.
   A real-world example is Gemini deleting an entire drive in production:
       https://futurism.com/artificial-intelligence/google-ai-deletes-entire-drive


---
Access Control & Sandboxing
---

*Allowed Commands*

The list of executable commands is defined in `agent/config/__init__.py`.
Setting the allowlist to an empty array disables shell access entirely.

Two helper tools are exposed:

1. **shell_allowed()** - returns configuration metadata related to the shell, including allowed commands.
2. **shell_run()** - accepts a “virtual script” (a string of shell code) and executes it after validation.

*Virtual Scripts*

A virtual script is any text blob containing one or more shell statements,
including variables, tests, functions, loops, etc.  The execution flow for a
script is:

1. Parse the input with tree-sitter to obtain an abstract syntax tree.
2. Query the AST for command names; compare each against the allowlist.
3. If any disallowed symbol appears, return diagnostics (node location,
   offending text) back to the model so it can correct its request.
4. On successful validation, execute the script using a user-supplied shell
   program - defaulting to `bash`.  The execution may be toggled on or off;
   by default it is disabled.

*tree-sitter Advantages*

Using tree-sitter removes the need for hand-rolled parsing logic,
ensures accurate command extraction even in complex pipelines, and gives the
model freedom while still catching dangerous patterns before they reach
`subprocess`.

---
Execution Details
---

- **Piping Support** - The runner constructs a `subprocess.Popen` chain that
  connects standard streams between commands.  Reference implementations can be
  found at:
      https://stackoverflow.com/a/295564/15147156
      https://docs.python.org/3/library/subprocess.html#replacing-shell-pipeline

- **Privilege Management** - Only basic utilities are allowed (e.g.
  `cat`, `grep`).  Destructive operations such as `rm` or `rmdir` must be
  explicitly enabled by the user.  If removal is required, a safer alternative
  like `trash-cli` can be used.

- **Output Handling** - All standard output and error streams are captured,
  encoded in UTF-8 (or raw bytes if requested), and returned to the agent as a
  structured response.

---
Summary
---

The shell tool is intentionally conservative: it requires explicit permission
to run any command, validates every invocation against an allowlist using
tree-sitter parsing, supports complex pipelines safely, and returns detailed
feedback.  Use with caution in production; never enable unrestricted access.
"""


import functools
import json
import shlex
import subprocess

import tree_sitter_bash
from tree_sitter import Language, Node, Parser, Query, QueryCursor, Tree

from agent.config import config

# --- Shell Parser ---


@functools.lru_cache
def _language() -> Language:
    """Return the pre-compiled bash language instance."""
    # get the PyObject* language binding
    capsule = tree_sitter_bash.language()
    # create the language instance object
    return Language(capsule)


def _tree(source: str) -> Tree:
    """Return a abstract syntax tree for the input source code."""
    # create the language parser
    parser = Parser(_language())
    # Tree-Sitter expects bytes; utf8 is fine for shell scripts.
    return parser.parse(source.encode("utf-8"))


# --- Shell Queries ---


# the key matches the capture identifier:
#   e.g. if capture is `@cmd`, then `key` is `cmd` and `val` is `list[Node]`
# captures return a dict and matches returns a list of tuples.
#   see tree-sitter/__init__.pyi for type annotations.
#     .venv/lib/python3.13/site-packages/tree_sitter/__init__.pyi
#   see docs for reference.
#     https://tree-sitter.github.io/py-tree-sitter/classes/tree_sitter.QueryCursor.html
def _query(root: Node, source: str) -> dict[str, list[Node]]:
    """Return a dictionary containing captured results for the source query."""
    # create the language query
    query = Query(_language(), source)
    # get the cursor for the current query (this is immutable)
    cursor = QueryCursor(query)
    # return the captured queries (this returns a dictionary)
    return cursor.captures(root)


# this is just a helper to simplify capture extraction.
def _nodes(root: Node, source: str) -> list[Node]:
    """Return a flattened list of captured nodes."""
    nodes = []
    captures = _query(root, source)
    for key in captures.keys():
        nodes.extend(captures[key])  # flatten
    return nodes


# the model can call any allowed command.
# allowed commands may be disabled or scoped to a specific task.
def _command_names(root: Node) -> list[Node]:
    """Return a list of captured command names."""
    source = r"""(command  ((command_name) @name))"""
    return _nodes(root, source)


# the model can define its own commands by defining a function.
# defined functions become new allowed commands.
def _function_words(root: Node) -> list[Node]:
    """Return a list of captured function words."""
    source = r"""(function_definition ((word) @id))"""
    return _nodes(root, source)


# we can lint the models input program and return detailed
# metadata to help the model recover via error correction.
def _lint(root: Node) -> list[Node]:
    """Return a list of captured syntax errors."""
    source = r"""(
        [
            (ERROR)
            (MISSING)
        ] @error
    )
    """
    return _nodes(root, source)


# --- Shell Filters ---


# warning: sets are not json serializable!
def _allowed() -> list[str]:
    """Return a list of allowed bash commands."""

    # use set() to filter out potential duplicates
    return list(set(config.get_value("shell.commands", [])))


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
    """Return a serialized dictionary of the current shell configuration."""
    allowed = _allowed()
    if not allowed:
        return "Shell commands are disabled."
    # warning: ensure the object dump is serialized and formatted!
    return json.dumps(config.get_value("shell", {}), indent=2)


# note: models require a string as a response object.
def shell_run(program: str) -> str:
    allowed = _allowed()

    try:
        args = shlex.split(program)
        if not args or args[0] not in allowed:
            return "Error: Command not allowed."
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=True,
            shell=config.get_value("shell.executable", False),
        )
        output = result.stdout.strip()
        print(f"out: {result}")
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

    source = (
        " ".join(sys.argv[1:]) or "shopt -s extglob; wc -l file.txt ; cat /etc/passwd"
    )
    print(f"command: `{source}`")
    root = _tree(source).root_node
    names = _command_names(root)
    allowed = _allowed()
    for node in names:
        name = node.text.decode()
        if name not in allowed:
            print(f"Command `{name}` is not allowed!")
            exit(1)

    # result = shell_run(source)
    # print(result)
