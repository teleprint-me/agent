# agent/text/bash.py
"""
keep this as dead simple as possible.

---
Issues
---

tree-sitter is not perfect and it has holes.
  - does not detect shebang and interprets them as comments.
  - does not detect job control operators, e.g. `&`.

---
Risks
---

i think the part with the most risk is that shebangs modify control flow.
you can technically tell the shell to run any program in any language.

---
References
---

  - for man page, see https://linux.die.net/man/1/bash
  - for more info, see https://linux.die.net/abs-guide/miscellany.html
    - Advanced Bash-Scripting Guide, Chapter 33. Miscellany
      - Section 1: Interactive and non-interactive shells and scripts
      - Section 2: Shell Wrappers
"""

import functools

import tree_sitter_bash
from tree_sitter import Language, Node, Parser, Query, QueryCursor, Tree

# --- programs ---

# the root node has type program which would emcompass a full shell script.
# enabling a full script into a subprocess would enable arbitrary execution.
# commands can be explicitly filtered out from the shell() function.
# additionally, functions are treated as user-defined commands.

# simple one-liner (node.type: command)
_command = r"""echo 'Hello,' ' World!'"""

# simple pipe to count n chars (node.type: pipeline)
_pipeline = r"""echo 'Hello, world!' | wc -c"""

# one or other (node.type: list)
_list = r"""echo 'Hello, world!' || printf 'Hello!\n'"""

# create a function and execute it!
_function = r"""fun() { echo 'Hello, world!'; }; fun"""

# has missing semicolons to trigger errors
_error = r"""fun() { echo 'Hello, world!' } fun"""

# simple script pretending to be a real program 🥲 (node.type: program)
_program = r"""
#!/usr/bin/env bash
# foo.sh – a tiny demo shell

if [ -z "$1" ]; then
    name="User"
else
    name="$1"
fi

function greet() {
    echo "Greetings and salutations!"
}

insult() {
    echo "Eat my shorts, $1!"
}

function farewell() {
    echo "It was nice meeting you!"
}

foo=$(greet)
echo "$foo"

bar=$(insult "$name")
echo "$bar"

baz=$(farewell)
echo "$baz"
"""

# exploit the difference between interpreters
_arbitrage = r"""
#!/usr/bin/env bash
# foo.py – a tiny demo pyshell

# arbitrary python program
python - <<'PY'
class Foo:
    @property
    def bar(self):
        return "bar"

def qux(foo: Foo):
    print(foo.bar)

def main():
    foo = Foo()
    qux(foo)

main()
PY
"""

_container = r"""
# see `set` under `SHELL BUILTIN COMMANDS` in `man bash` for info
# see `Shell Variables` under `PARAMETERS` in `man bash` for info
env -i \ # clear the environment for isolation
    HOME="$HOME" \ # keep a sane $HOME
    USER="${USER:-$(id -un)}" \
    LOGNAME="${LOGNAME:-${USER}}" \
    PATH="/usr/bin:/usr/local/bin" \
    TERM="xterm-256color" \
    LANG=en_US.UTF-8 \ # whatever locale is needed
    set -e \ # exit immediately on error
    set +m \ # disable job control
    set -u \ # treat unset variables as errors
    hash -r 2> /dev/null \ # forget past commands
    exec "$@" # jump into a program
"""

# --- parser ---


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


# --- query ---


class BashQuery:
    """
    Helpers for querying shell scripts with *tree-sitter*.

    All methods are `@staticmethod` - you simply call
    :py:meth:`BashQuery.<method>(root)` where `root` is the AST root node.
    """

    @staticmethod
    def captures(root: Node, source: str) -> dict[str, list[Node]]:
        """Return a dictionary containing captured results for the source query."""
        query = Query(BashParser.language(), source)
        cursor = QueryCursor(query)
        return cursor.captures(root)

    @staticmethod
    def nodes(root: Node, source: str) -> list[Node]:
        """Return a flattened list of captured nodes."""
        nodes = []
        captures = BashQuery.captures(root, source)
        for key in captures.keys():  # values are lists of nodes
            nodes.extend(captures[key])  # flatten
        return nodes

    @staticmethod
    def command_names(root: Node) -> list[Node]:
        """Return a list of nodes representing each `command_name` token."""
        return BashQuery.nodes(root, r"""(command  ((command_name) @name))""")

    @staticmethod
    def function_names(root: Node) -> list[Node]:
        """Return a list of nodes that are the names of user-defined functions."""
        return BashQuery.nodes(root, r"""(function_definition ((word) @id))""")

    @staticmethod
    def errors(root: Node) -> list[Node]:
        """Return a list of nodes that contain syntax error markers."""
        return BashQuery.nodes(root, r"""( [ (ERROR) (MISSING) ] @marker )""")


# --- utilities ---


def start(node: Node) -> dict[str, int]:
    return {
        "row": node.start_point.row,
        "column": node.start_point.column,
        "byte": node.start_byte,
    }


def end(node: Node) -> dict[str, int]:
    return {
        "row": node.end_point.row,
        "column": node.end_point.column,
        "byte": node.end_byte,
    }


def lint(root: Node) -> list[dict[str, any]]:
    return [
        {
            "text": node.text.decode(),
            "type": node.type,
            "start": start(node),
            "end": end(node),
        }
        for node in BashQuery.errors(root)
    ]


def command_names(root: Node) -> list[dict[str, any]]:
    return [
        {
            "text": node.text.decode("utf8"),
            "type": node.type,
            "start": start(node),
            "end": end(node),
        }
        for node in BashQuery.command_names(root)
    ]


def walk(root: Node, depth: int = 0, margin: int = 30):
    """Pretty-print a small subtree."""
    indent = "  " * depth
    txt = root.text[:margin].decode("utf8", errors="replace")
    print(f"{indent}{root.type:2} ({txt!r})")

    for node in root.children:
        walk(node, depth + 1)


# --- test ---

if __name__ == "__main__":
    import json
    import subprocess
    from argparse import ArgumentParser

    # --- keywords ---

    choices = {
        "command": _command,
        "pipeline": _pipeline,
        "list": _list,
        "function": _function,
        "error": _error,
        "program": _program,
        "arbitrage": _arbitrage,
        "container": _container,
    }

    # --- args ---

    parser = ArgumentParser()
    parser.add_argument(
        "keyword",
        default="command",
        choices=choices.keys(),
        help="Select a command type to parse out.",
    )
    parser.add_argument(
        "--walk",
        action="store_true",
        help="Pretty print the abstract syntax tree.",
    )
    parser.add_argument(
        "--lint",
        action="store_true",
        help="Query program for missing erroneous symbols.",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute the program specified by the keyword.",
    )
    args = parser.parse_args()

    # --- program ---

    program = choices[args.keyword]
    root = BashParser.parse(program)

    # --- walk ---

    if args.walk:
        print("Walk:")
        walk(root, depth=0)

    # --- lint ---

    if args.lint:
        errors = lint(root)
        if errors:
            print(f"Captured {len(errors)} error(s):")
            print(json.dumps(errors, indent=2))
        else:
            print("No errors.")

    # --- query ---

    names = command_names(root)
    if names:
        print(f"Captured {len(names)} command(s):")
        print(json.dumps(names, indent=2))
    else:
        print("No commands.")

    # --- run ---

    # deny execution of the following programs until the details have been resolved.
    deny = ["container"]

    if args.run and args.keyword in deny:
        print(
            f"Response: Your request to execute {args.keyword} "
            "is respectfully denied."
        )
        print(
            "Warning: It's not a good idea to run this unless "
            "you know what you're doing."
        )
        exit(1)

    if args.run and args.keyword not in deny:
        print("Run:")
        try:
            cmd = ["/usr/bin/bash", "-c", f"""{program}"""]
            res = subprocess.run(cmd, capture_output=True, check=True, text=True)
            print("status: ok")
            print(f"stdout: {res.stdout.strip() or '(No output)'}")
            print(f"stderr: {res.stderr.strip() or '(No error)'}")
            print(f"code: {res.returncode}")
        except subprocess.CalledProcessError as e:
            print("status: error")
            print(f"stdout: {e.stdout.strip() or '(No output)'}")
            print(f"stderr: {e.stderr.strip() or '(No error)'}")
            print(f"code: {e.returncode}")
            print(f"exception: {str(e)}")
