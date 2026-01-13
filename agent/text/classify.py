"""
https://stackoverflow.com/a/1446870/15147156
# Source - https://stackoverflow.com/a/1446870
# Posted by Thomas, modified by community. See post 'Timeline' for change history
# Retrieved 2026-01-12, License - CC BY-SA 3.0
"""

import string
from string import printable


def istext(filename):
    """classify the input file path and return true if plaintext, otherwise false."""

    s = open(filename).read(512)
    text_characters = "".join(map(chr, range(32, 127)) + list("\n\r\t\b"))
    _null_trans = string.maketrans("", "")
    if not s:
        # Empty files are considered text
        return True
    if "\0" in s:
        # Files with null bytes are likely binary
        return False
    # Get the non-text characters (maps a character to itself then
    # use the 'remove' option to get rid of the text characters.)
    t = s.translate(_null_trans, text_characters)
    # If more than 30% non-text characters, then
    # this is considered a binary file
    if float(len(t)) / float(len(s)) > 0.30:
        return False
    return True


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("path", help="Input file to classify.")
    args = parser.parse_args()

    print(f"Is text file: {istext(args.path)}")
