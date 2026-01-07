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
   Models may take creative or unexpected paths to achieve a goal.
   Demonstrating specification gaming in reasoning models:
       https://arxiv.org/abs/2502.13295

4. **Destructive actions**
   Agents might execute programs that could lead to destructive operations.
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

- **Process Management** - `subprocess.Popen` chaining can be used to
  connect standard streams between commands.  Reference implementations can be
  found at:
      https://stackoverflow.com/a/295564/15147156
      https://docs.python.org/3/library/subprocess.html#replacing-shell-pipeline

- **Privilege Management** - Only basic utilities are allowed (e.g.
  `cat`, `grep`).  Destructive operations such as `rm` or `rmdir` must be
  explicitly enabled by the user.  If removal is required, a safer alternative
  like `trash-cli` can be used.

- **Output Management** - All standard output and error streams are captured,
  encoded into UTF-8, and returned to the agent as a structured response.

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
import shutil
import subprocess
from pathlib import Path

import tree_sitter_bash
from tree_sitter import Language, Node, Parser, Point, Query, QueryCursor, Tree

from agent.config import config

# --- Structures ---


class Terminal:

    @staticmethod
    def as_dict() -> dict[str, any]:
        """End user settings used to orchestrate shell execution."""
        return config.get_value("terminal", {})

    @staticmethod
    def shell() -> str:
        """Binary used to execute the input program."""
        return config.get_value("terminal.shell", "/usr/bin/bash")

    @staticmethod
    def executable() -> bool:
        """Enable execution within a shell subprocess."""
        return config.get_value("terminal.executable", False)

    @staticmethod
    def restricted() -> bool:
        """Enable restrictions within a shell process."""
        return config.get_value("terminal.restricted", False)

    @staticmethod
    def command_names() -> list[str]:
        """Return a list of allowed executable commands within a shell."""
        return list(set(config.get_value("terminal.command_names", [])))


# --- Parser ---


class BashParser:
    """Thin wrapper around the pre-compiled *bash* language for tree-sitter."""

    @staticmethod
    @functools.lru_cache
    def language() -> Language:
        """Return a `Language` instance pointing at the compiled bash grammar."""
        return Language(tree_sitter_bash.language())

    @staticmethod
    def parse(source: str) -> Node:
        """Parse `source` into a tree-sitter AST and return its root node."""
        parser = Parser(BashParser.language())
        tree = parser.parse(source.encode())
        return tree.root_node


# --- Query ---


class BashQuery:
    """
    Helpers for querying shell scripts with *tree-sitter*.

    All methods are `@staticmethod` - you simply call
    :py:meth:`BashQuery.<method>(root)` where `root` is the AST root node.
    """

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
        """Return a list of nodes representing each `command_name` token."""
        return BashQuery.nodes(root, r"""(command  ((command_name) @name))""")

    # the model can define its own commands by defining a function.
    # defined functions become new allowed commands.
    @staticmethod
    def function_names(root: Node) -> list[Node]:
        """Return a list of nodes that are the names of user-defined functions."""
        return BashQuery.nodes(root, r"""(function_definition ((word) @id))""")

    # captured commands compared against a user defined allowlist.
    # model defined functions are appended to this list.
    @staticmethod
    def allowed(root: Node) -> list[str]:
        """Return a list of allowed command names."""
        allowlist = Terminal.command_names()
        functions = BashQuery.function_names(root)
        for n in functions:
            allowlist.append(n.text.decode())
        return allowlist

    # if the model attempts to violate the access control list,
    # we return a list of violations to allow it to attempt to achieve
    # its goal through (ideally) allowed means.
    @staticmethod
    def denied(root: Node) -> list[dict[str, any]]:
        """Return a list of denied command names."""
        allowlist = BashQuery.allowed(root)
        nodes = BashQuery.command_names(root)
        return [
            {
                "status": "deny",
                "command_name": node.text.decode(),
                "content": root.text[node.start_byte : node.end_byte].decode(),
                "start": {
                    "row": node.start_point.row,
                    "column": node.start_point.column,
                },
                "end": {
                    "row": node.end_point.row,
                    "column": node.end_point.column,
                },
            }
            for node in nodes
            if node.text.decode() not in allowlist
        ]

    # we can lint the models input program and return detailed
    # metadata to help the model recover by correcting its errors.
    @staticmethod
    def errors(root: Node) -> list[dict[str, any]]:
        """Return a list of nodes that contain syntax error markers."""
        nodes = BashQuery.nodes(root, r"""( [ (ERROR) (MISSING) ] @errors )""")
        return [
            {
                "status": "error",
                "error": node.text.decode(),
                "content": root.text[node.start_byte : node.end_byte].decode(),
                "start": {
                    "row": node.start_point.row,
                    "column": node.start_point.column,
                },
                "end": {
                    "row": node.end_point.row,
                    "column": node.end_point.column,
                },
            }
            for node in nodes
        ]


# --- Tools ---


# A tool must be a function, or staticmethod, and it must return a **str**.
class Shell:
    # check to ensure bash command is availble and within environment path.
    @staticmethod
    def path() -> dict[str, str]:
        """Return status based on shell availability."""
        path = Path(Terminal.shell())
        message = "Error: User misconfigured tool."
        if path.name != "bash":
            return {
                "status": "error",
                "content": f"{message} Shell must be `bash`, not `{path.name}`",
            }
        which = shutil.which(path.name)
        if not which:
            return {
                "status": "error",
                "content": f"{message} `{path}` is not a valid file.",
            }
        return {"status": "ok", "content": str(which)}

    # tool: allow the model to query shell availability.
    @staticmethod
    def allowed() -> str:
        """Return the terminal configuration as a serialized dictionary."""
        if not Terminal.command_names():
            return "Shell commands are disabled."
        return json.dumps(Terminal.as_dict(), indent=2)

    # tool: execute the models input program
    @staticmethod
    def run(program: str) -> str:
        # end user disabled shell
        if not Terminal.command_names():
            return "Shell commands are disabled."

        # check if the environment has bash
        path = Shell.path()
        if path["status"] == "error":
            return json.dumps(path, indent=2)

        # parse the input program and get the root node
        root = BashParser.parse(program)

        # check if input program is denied
        denied = BashQuery.denied(root)
        if denied:
            return json.dumps(denied, indent=2)

        # check if input program has errors
        errors = BashQuery.errors(root)
        if errors:
            return json.dumps(errors, indent=2)

        # note: i need to figure out how to convince bash the input is a file.
        #       for now, I just use the -c option, but the input should be
        #       treated as a conventional shell script.

        # build the command to execute
        args = [path["content"], "-c"]
        # end user restricted shell access
        if Terminal.restricted():
            args.append("-r")
        # convert the input program into a virtual script
        args.append(program.encode())  # look into `io` options.

        # execute the program
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                check=True,
                shell=False,  # avoid enabling this as much as possible
            )
            return json.dumps(
                {
                    "status": "ok",
                    "stdout": result.stdout.strip() or "(No output)",
                    "stderr": result.stderr.strip() or "(No error)",
                    "code": result.returncode,
                },
                indent=2,
            )
        except subprocess.CalledProcessError as e:
            return json.dumps(
                {
                    "status": "error",
                    "stdout": e.stdout.strip() or "(No output)",
                    "stderr": e.stderr.strip() or "(No error)",
                    "code": e.returncode,
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps(
                {
                    "status": "error",
                    "exception": str(e),
                    "code": e.returncode,
                },
                indent=2,
            )


# usage example
# figure out how to safely handle piped commands
# conditionals should be allowed for added flexibility and proper error handling
# the downside to this is that tree-sitter only officially supports bash
# the upside to this is that i don't have to reinvent yet another parser
# shlex is very limited and manually parsing split is error prone
# getting an automated AST can (hopefully) make life easier
if __name__ == "__main__":
    import sys

    # simple command injection to test boundaries
    default = "shopt -s extglob; wc -l file.txt ; cat /etc/passwd"
    program = " ".join(sys.argv[1:]) or default

    print(f"command: `{program}`")
    print(Shell.allowed())
    print(Shell.run(program))
