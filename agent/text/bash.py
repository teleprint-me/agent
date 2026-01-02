# agent/text/bash.py
"""
keep this as dead simple as possible
"""

import tree_sitter_bash
from tree_sitter import Language, Node, Parser, Query, QueryCursor, Tree

# --- samples ---

# it's okay if any of the following are unused

# simple one-liner (node.type: command)
inline = r'echo "Hello," " World!"'

# one or other (node.type: list)
conditional = r'echo "Hello," " World!" || exit 1'

# simple pipe to count n chars (node.type: pipeline)
pipeline = r'echo "Hello, world!" | wc -c'

# this has no node type. tests, variables, and functions would need be skipped.
# enabling a full script into the subprocess would enable arbitrary execution.
# this would need to be explicitly filtered out from the shell() function.
# simple script pretending to be a real program 🥲
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

# match any "echo" command and capture the string literal that follows
# keep this generic for now
query_source = r"""
(
    (command (command_name) @name) @cmd
)
"""


# the key matches the capture identifier, e.g. key -> cmd
def query(node: Node, source: str) -> dict[str, list[Node]]:
    q = Query(language(), source)
    c = QueryCursor(q)
    return c.captures(node)


# --- run ---

if __name__ == "__main__":
    root = tree(script).root_node
    walk(root, depth=0)

    captures = query(root, query_source)
    print(f"Captured ({type(captures)}):")
    for key in captures:
        nodes = captures[key]
        print(f"{key}: {len(nodes)} nodes: {nodes}")
        for node in nodes:
            print(node.text.decode("utf8"))
