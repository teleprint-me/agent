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

1. **shell_allowed()** - returns configuration metadata related to the terminal, including allowed commands.
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
from dataclasses import dataclass

import tree_sitter_bash
from tree_sitter import Language, Node, Parser, Point, Query, QueryCursor, Tree

from agent.config import config

# --- Data Structures ---


@dataclass
class Command:
    name: str  # e.g. "echo"
    slice: str  # e.g. "echo 'Hello, world!'"
    start: Point
    end: Point


class Terminal:

    @staticmethod
    def as_dict() -> dict[str, any]:
        """The end user terminal settings used to orchestrate shell execution."""
        return config.get_value("terminal", {})

    @staticmethod
    def shell() -> str:
        """The shell environment used to execute the input program."""
        return config.get_value("terminal.shell", "/usr/bin/bash")

    @staticmethod
    def command_names() -> list[str]:
        """A list of allowed commands enabling execution within a shell."""
        return list(set(config.get_value("terminal.command_names", [])))

    @staticmethod
    def executable() -> bool:
        """Enable shell execution within the executed subprocess."""
        return config.get_value("terminal.executable", False)

    @staticmethod
    def restricted() -> bool:
        """Enable shell restriction within the shell process."""
        return config.get_value("terminal.restricted", False)


# --- Parser ---


class BashParser:
    @staticmethod
    @functools.lru_cache
    def language() -> Language:
        """Return the pre-compiled bash language instance."""
        # get the PyObject* language binding and create the language instance
        return Language(tree_sitter_bash.language())

    @staticmethod
    def parse(source: str) -> Tree:
        """Return a abstract syntax tree for the input source code."""
        # Tree-Sitter expects bytes; utf8 is fine for shell scripts.
        return Parser(BashParser.language()).parse(source.encode("utf-8"))


# --- Query ---


class BashQuery:
    # the key matches the capture identifier:
    #   e.g. if capture is `@cmd`, then `key` is `cmd` and `val` is `list[Node]`
    # captures return a dict[str, list] and matches returns a list[tuple].
    #   see tree-sitter/__init__.pyi for type annotations.
    #     .venv/lib/python3.13/site-packages/tree_sitter/__init__.pyi
    #   see docs for reference.
    #     https://tree-sitter.github.io/py-tree-sitter/classes/tree_sitter.QueryCursor.html
    @staticmethod
    def captures(root: Node, source: str) -> dict[str, list[Node]]:
        """Return a dictionary containing captured results for the source query."""
        # create the language query (immutable)
        query = Query(BashParser.language(), source)
        # get the cursor for the current query (immutable)
        cursor = QueryCursor(query)
        # return the captured queries (returns a dictionary)
        return cursor.captures(root)

    # this is just a helper to simplify capture extraction.
    @staticmethod
    def nodes(root: Node, source: str) -> list[Node]:
        """Return a flattened list of captured nodes."""
        nodes = []
        captures = BashQuery.captures(root, source)
        for key in captures.keys():  # values are lists of nodes
            nodes.extend(captures[key])  # flatten
        return nodes

    # the model can call any allowed command.
    # allowed commands may be disabled or scoped to a specific task.
    @staticmethod
    def command_names(root: Node) -> list[Node]:
        """Return a list of captured command names."""
        return BashQuery.nodes(root, r"""(command  ((command_name) @name))""")

    # the model can define its own commands by defining a function.
    # defined functions become new allowed commands.
    @staticmethod
    def function_names(root: Node) -> list[Node]:
        """Return a list of captured function words."""
        return BashQuery.nodes(root, r"""(function_definition ((word) @id))""")

    # we can lint the models input program and return detailed
    # metadata to help the model recover via error correction.
    @staticmethod
    def errors(root: Node) -> list[Node]:
        """Return a list of captured syntax errors."""
        return BashQuery.nodes(root, source=r"""( [ (ERROR) (MISSING) ] @errors )""")

    @staticmethod
    def denied(root: Node) -> list[Node]:
        """Return a list of disallowed command names, else return a empty list."""
        names = BashQuery.command_names(root)
        return [n for n in names if n.text.decode() not in Terminal.command_names]


# --- Model Tools ---


# note: models require a string as a response object.
def shell_allowed() -> str:
    """Return a serialized dictionary of the terminal configuration."""
    if not Terminal.command_names:
        return "Shell commands are disabled."
    # warning: ensure the object dump is serialized and formatted!
    return json.dumps(Terminal.as_dict, indent=2)


# note: models require a string as a response object.
def shell_run(program: str) -> str:
    # validate the input program
    root = BashParser.parse(program).root_node
    names = _command_names(root)
    denied = _denied(root)
    if denied:
        return  # a serialized result detailing failed criteria
    if errors:
        return  # similar to denied, but adjusted for bad syntax

    # configure the arguments
    args = [Terminal.shell, "-c"]
    if Terminal.restricted:
        args.append("-r")
    args.append(program)

    # execute the program
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=True,
            shell=Terminal.executable,
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

    # sample command injection
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
