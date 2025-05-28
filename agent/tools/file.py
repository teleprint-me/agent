"""
agent.tools.file

Usage Example:
    content = file_read('path/to/your/file.py', 100, 200)
    # This reads lines 100 to 200 of the file
"""

from typing import Optional


def file_read(
    filepath: str,
    start_line: int = 1,
    end_line: Optional[int] = None,
) -> str:
    """
    Reads lines from start_line to end_line (inclusive, 1-based) from a file.
    If end_line is None, reads to the end.
    """
    # Convert to zero-based indices for internal use
    start = max(0, start_line - 1)
    # If end_line is provided, it's inclusive (natural style), so +1 for slicing
    end = end_line if end_line is not None else None

    lines = []
    with open(filepath, "r") as f:
        for i, line in enumerate(f):
            if i < start:
                continue
            if end is not None and i > (end - 1):
                break
            lines.append(line)
    return "".join(lines)


def file_write(
    filepath: str,
    content: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
) -> str:
    """
    Overwrite lines start_line to end_line (inclusive, 1-based).
    If both are None, overwrite the entire file.
    """
    try:
        if start_line is None and end_line is None:
            with open(filepath, "w") as f:
                f.write(content)
            return f"Wrote {len(content)} bytes to '{filepath}'."

        # Read all lines first
        with open(filepath, "r") as f:
            lines = f.readlines()

        # Adjust to 0-based index (inclusive range)
        start = (start_line - 1) if start_line else 0
        end = (end_line) if end_line else start + 1

        # Replace the slice (note: end is exclusive in Python slice)
        replacement = content.splitlines(keepends=True)
        lines[start:end] = replacement

        with open(filepath, "w") as f:
            f.writelines(lines)
        return f"Wrote {len(content)} bytes to '{filepath}' in range({start_line}, {end_line})."
    except Exception as e:
        return f"Error: {e}"
