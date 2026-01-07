# agent/text/bash.py
"""
keep this as dead simple as possible
"""

import tree_sitter_bash
from tree_sitter import Language, Node, Parser, Query, QueryCursor, Tree

# --- samples ---

# the root node has type program which would emcompass a full shell script.
# enabling a full script into a subprocess would enable arbitrary execution.
# NOTE: tests and functions would need be skipped.
# this would need to be explicitly filtered out from the shell() function.

# simple one-liner (node.type: command)
inline = r'echo "Hello," " World!"'

# one or other (node.type: list)
conditional = r'echo "Hello," " World!" || exit 1'

# simple pipe to count n chars (node.type: pipeline)
pipeline = r'echo "Hello, world!" | wc -c'

# simple script pretending to be a real program 🥲 (node.type: program)
script = r"""
# foo.sh – a tiny demo shell
if [ -z "$1" ]; then
    name="User"
else
    name="$1"
fi

function greet() {
    echo "Greetings and salutations!"
}

function insult() {
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

# --- core ---


def language() -> Language:
    # get the PyObject* language binding
    capsule = tree_sitter_bash.language()
    # create the language instance object
    return Language(capsule)


def tree(source: str) -> Tree:
    # create the language parser
    parser = Parser(language())
    # Tree‑Sitter expects bytes; utf8 is fine for shell scripts.
    return parser.parse(source.encode("utf-8"))


def walk(node: Node, depth: int = 0):
    """Pretty-print a small subtree."""
    indent = "  " * depth
    # Show only the first 30 bytes of text so the output stays readable.
    txt = node.text[:30].decode("utf8", errors="replace")
    print(f"{indent}{node.type:2} ({txt!r})")

    for child in node.children:
        walk(child, depth + 1)


# --- queries ---


# the key matches the capture identifier, e.g. key -> cmd
def query(node: Node, source: str) -> dict[str, list[Node]]:
    q = Query(language(), source)
    c = QueryCursor(q)
    return c.captures(node)


# only capture root-level commands.
# e.g. ignore tests, functions, nested bodies, etc.
# some things may be desirable, like assignments and substitutions.
# e.g. modifying an environment variable to run a command like cmake for example.
# substitutions may add more complexity than it's worth  - not sure yet.
# ideally, we just handle commands and pipelines cleanly.
# lists are convenience for the llms.
def capture_commands(node: Node) -> list[Node]:
    """Return a list of captured commands."""
    source: str = r"""
    (program [
            (command)
            (pipeline (command))
            (list     (command))
        ] @root_command
    )
    """
    captures: dict[str, list[Node]] = query(node, source)
    commands: list[Node] = []
    for key in captures.keys():
        commands.extend(captures[key])
    return commands


def capture_names(node: Node) -> list[Node]:
    """Return a list of captured command names."""
    source = r"""
    (program [
            (command  (command_name) @name)
            (pipeline (command (command_name) @name))
            (list     (command (command_name) @name))
        ]
    )
    """
    captures: dict[str, list[Node]] = query(node, source)
    return [n for n in captures.get("name", [])]


# note: the models expect a serialized json object.
def capture_denied(node: Node) -> list[Node]:
    """Return a list of disallowed command names, else return a empty list."""
    from agent.config import config

    allowed = set(config.get_value("shell.allowed", []))
    names = capture_names(node)
    disallowed = []
    for name in names:
        if name.text.decode("utf8") not in allowed:
            disallowed.append(name)  # return the invalid node
    return None  # all nodes are executable


# --- run ---

if __name__ == "__main__":
    from argparse import ArgumentParser

    choices = {
        "command": inline,
        "pipeline": pipeline,
        "list": conditional,
        "inject": script,
    }

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
    args = parser.parse_args()

    selected = choices[args.keyword]
    root = tree(selected).root_node

    if args.walk:
        walk(root, depth=0)

    commands = capture_commands(root)
    if commands:
        print(f"Captured {len(commands)} command(s):")
        for command in commands:
            print(
                f"cmd: `{command.text.decode('utf8')}`, "
                f"start: {command.start_point}, "
                f"end: {command.end_point}"
            )

        names = capture_names(root)
        print(f"Queried {len(names)} commands:")
        for name in set(names):  # filter out repeats
            print(f"command_name: {name}")
    else:
        print("No captures matched.")
