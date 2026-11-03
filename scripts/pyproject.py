# /// script
# requires-python = ">=3.10"
# dependencies = ["tomlkit>=0.13"]
# ///
"""Add the tools with `uv add` and set the Python classifiers and the project URLs in pyproject.toml.

`copier update` also renders the template into empty temporary directories to compute its diff, and
runs the tasks there too, so the script returns at once when there is no pyproject.toml.
The classifiers for CPython versions are replaced, so a floor change on `copier update` moves them.
Every other classifier, every URL the file already has, and everything uv wrote are kept.
"""

import argparse
import subprocess
from pathlib import Path

import tomlkit
from tomlkit.items import Table

PYTHON = "Programming Language :: Python :: "


def main() -> None:
    """Edit pyproject.toml in the working directory."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--versions", required=True, help="comma-separated, floor first")
    parser.add_argument("--docs", default="False")
    parser.add_argument("--dev", nargs="*", default=[], help="tools for the dev group, added with no bound")
    args = parser.parse_args()

    path = Path("pyproject.toml")
    if not path.exists():
        return

    # `--raw` adds each tool with no lower bound, because `uv.lock` pins it and an upgrade moves it to the latest release.
    dev = [tool for tool in args.dev if tool]
    if dev:
        subprocess.run(["uv", "add", "--raw", "--group", "dev", *dev], check=True)
    if args.docs == "True":
        # Not in `dev`, so the test and lint jobs skip Quarto's Jupyter stack.
        subprocess.run(["uv", "add", "--group", "docs", "great-docs>=0.17"], check=True)

    doc = tomlkit.parse(path.read_text())
    project = doc["project"]
    assert isinstance(project, Table)

    kept = [c for c in project.get("classifiers", []) if not str(c).startswith(PYTHON) and str(c) != "Typing :: Typed"]
    classifiers = tomlkit.array()
    for item in [*kept, PYTHON + "3", *(PYTHON + v for v in args.versions.split(",")), "Typing :: Typed"]:
        classifiers.append(item)
    classifiers.multiline(True)
    project["classifiers"] = classifiers

    github = f"https://github.com/{args.owner}/{args.repo}"
    urls = {"Changelog": f"{github}/releases", "Homepage": github, "Issues": f"{github}/issues", "Source": github}
    if args.docs == "True":
        urls["Documentation"] = f"https://{args.owner}.github.io/{args.repo}/"
    table = project.get("urls")
    if not isinstance(table, Table):
        table = tomlkit.table()
        project["urls"] = table
    for key in sorted(urls):
        if key not in table:
            table[key] = urls[key]

    # tombi adds the blank line before each table header when the hooks run.
    path.write_text(tomlkit.dumps(doc))


if __name__ == "__main__":
    main()
