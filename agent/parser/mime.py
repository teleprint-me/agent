"""
agent.parser.mime
Get the mime type of a given file object.
"""

import inspect
from argparse import ArgumentParser

import magic

parser = ArgumentParser()
parser.add_argument("path", help="Path to plain text source file")
args = parser.parse_args()

# note that FileMagic has no internal __dict__.
# use dir instead of vars
# has 3 primary properties:
#   - encoding, e.g. utf-8
#   - mime_type, e.g. text/plain
#   - name, e.g. Unicode text, UTF-8 text
file_magic = magic.detect_from_filename(args.path)

print(f"FileMagic.encoding = '{file_magic.encoding}'")
print(f"FileMagic.mime_type = '{file_magic.mime_type}'")
print(f"FileMagic.name = '{file_magic.name}'")

if file_magic.encoding == "binary":
    print("File is currently unsupported")
    exit(1)

print("File is a plain text source file")
