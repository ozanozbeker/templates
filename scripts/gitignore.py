"""Append each line given on the command line to .gitignore, once, in the working directory.

Copier runs this with its own interpreter, so it needs nothing but the standard library.
An empty argument is skipped, which lets a task pass a line under a Jinja condition.
"""

import sys
from pathlib import Path


def main() -> None:
    """Append the missing lines."""
    path = Path(".gitignore")
    existing = path.read_text().splitlines() if path.exists() else []
    wanted = [line for line in sys.argv[1:] if line and line not in existing]
    if not wanted:
        return
    text = path.read_text() if path.exists() else ""
    if text and not text.endswith("\n"):
        text += "\n"
    path.write_text(text + "\n".join(wanted) + "\n")


if __name__ == "__main__":
    main()
