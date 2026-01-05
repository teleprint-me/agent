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

Access Control and Sandboxing:

See agent/config/__init__.py for allowed shell commands.

- Shell access is controlled by a predefined list of allowed commands
- Users can disable shell access by setting an empty list in the configuration
- The model is given 2 tools:
  - A tool for listing accessible commands, if any.
  - A tool for executing "virtual" shell scripts.
- A "virtual script" is a "program" that enables arbitrary execution through the shell.
  - Shell execution may be toggled to False (default) or True
  - Shell execution may be restricted True (default) or False
- A program consists of one or more shell commands.
- A program may contain variables or function definitions.
  - A function definition is defined as a user defined command.
- Tree-sitter is used to parse the input program and ouputs a abstract syntax tree.
  - A query is used to output captures of arbitrary commands.
  - Captures are used to access command names which is compared to the user defined allow list.
  - If a captured command is not in the allow list, the node and its related metadata, along with access
    details is then relayed back to the model as output.
  - If a symbol is missing or a syntax error is discovered in the program (linting), then the issue
    is relayed back to the model to allow it to adjust and correct its error.
    - NOTE: Shell capabilities can be toggled on or off and command authorization will still apply.
      This will catch common sources of input injection that can compromise a system in production.
- Once the input program has been parsed, queried, captured, and validated, then it is considered for execution.
  - A program may be executed through a user defined shell program (default is bash).
  - A program may have shell access and or may be restricted. This is tunable according to end user needs, but
    defaults to False for security purposes.
  - A programs results (stdout, stderr, etc) should be captured and output back to the model as a response.

Using tree-sitter side-steps the need to manually handle and parse complex commands, pipelines, and more.
It gives the model freedom while constraining its errors without compromising end user environments.

Security considerations:

1. **Sandboxing**:
   - Commands are executed with strict security settings
   - Running untrusted code is never safe, sandboxing cannot change this

2. **Piping Support**:
   - Safe handling of piped commands via subprocess chaining
     https://stackoverflow.com/a/295564/15147156
     https://docs.python.org/3/library/subprocess.html#replacing-shell-pipeline

3. **Privilege Management**:
   - Commands are restricted to basic utilities for safety
   - Users should not enable destructive operations like `rm`, `rmdir`
   - If removal is desired, you can use something like trash-cli.
     trash-cli is a command line trashcan (recycle bin) interface

The shell tool is designed to be used responsibly and safely.
Never enable unrestricted access in production environments.
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
    # Tree‑Sitter expects bytes; utf8 is fine for shell scripts.
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
