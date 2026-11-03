# /// script
# requires-python = ">=3.14"
# dependencies = ["tomlkit>=0.13"]
# ///
"""Compose a repo's config files from this repo's root and the layers named on the command line.

The root is the base every repo gets, and each top-level directory is a layer that mirrors the repo tree. A `.toml` file deep-merges onto what the destination already has, a `.gitignore`
appends the lines it lacks, and every other file is copied whole, with the later layer winning. After the copy,
the placeholders `<package>`, `<owner>`, `<repo>` and `<python>` are filled, and the Python versions from the
floor to the newest release go into the classifiers and the CI matrix.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import tomlkit
from tomlkit.items import AoT, Array, Table

if TYPE_CHECKING:
    from collections.abc import Iterable

ROOT = Path(__file__).resolve().parent

# Every CPython with a final release, oldest first. Add a version at its final release, and remove one in the
# first release after its end of life.
RELEASED = ["3.10", "3.11", "3.12", "3.13", "3.14", "3.15"]
# The newest CPython that has reached its first beta. It stays on a version after its final release, until the
# next version reaches its first beta.
NEXT = "3.15"
CLASSIFIER_ANCHOR = "Programming Language :: Python :: 3"
# The repo's own files at the root, which no repo receives.
NOT_CONFIG = {"compose.py", "README.md", "LICENSE"}


def merge(
    base: Table | tomlkit.TOMLDocument, layer: Table | tomlkit.TOMLDocument
) -> None:
    """Merge `layer` into `base` in place: tables recurse, arrays append without duplicates, scalars overwrite."""
    for key, value in layer.items():
        current = base.get(key)
        if isinstance(current, AoT) and isinstance(value, AoT):
            for item in value:
                current.append(item)
        elif isinstance(current, Table) and isinstance(value, Table):
            merge(current, value)
        elif isinstance(current, Array) and isinstance(value, Array):
            for item in value:
                if item not in current:
                    current.append(item)
        else:
            base[key] = value


def versions_from(floor: str) -> list[str]:
    """Return every released CPython from `floor` up."""
    if floor not in RELEASED:
        message = f"{floor} is not in RELEASED: {RELEASED}"
        raise SystemExit(message)
    return RELEASED[RELEASED.index(floor) :]


def matrix_exclude(text: str, versions: list[str]) -> str:
    """Fill the matrix `exclude` with the middle versions skipped on macOS and Windows, or drop it when there are none."""
    middle = versions[1:-1]
    if not middle:
        return re.sub(
            r"(?:^ *#[^\n]*\n)? *exclude: <python-exclude>\n",
            "",
            text,
            flags=re.MULTILINE,
        )
    lines = [
        f'          - {{ os: {os}, python: "{version}" }}'
        for os in ("macos-latest", "windows-latest")
        for version in middle
    ]
    return text.replace(" <python-exclude>", "\n" + "\n".join(lines))


def fill(text: str, package: str, owner: str, repo: str, floor: str) -> str:
    """Replace every placeholder in `text`."""
    versions = versions_from(floor)
    matrix = "[" + ", ".join(f'"{version}"' for version in versions) + "]"
    return (
        matrix_exclude(text, versions)
        .replace("<python-matrix>", matrix)
        .replace("<python-next>", NEXT)
        .replace("<python>", floor)
        .replace("<package>", package)
        .replace("<owner>", owner)
        .replace("<repo>", repo)
    )


def add_classifiers(text: str, floor: str) -> str:
    """Insert a classifier per supported Python after the `Programming Language :: Python :: 3` one."""
    doc = tomlkit.parse(text)
    project = doc.get("project")
    if not isinstance(project, Table) or "classifiers" not in project:
        return text
    classifiers = project["classifiers"]
    if not isinstance(classifiers, Array) or CLASSIFIER_ANCHOR not in classifiers:
        return text
    position = list(classifiers).index(CLASSIFIER_ANCHOR) + 1
    for version in reversed(versions_from(floor)):
        classifier = f"Programming Language :: Python :: {version}"
        if classifier not in classifiers:
            classifiers.insert(position, classifier)
    return tomlkit.dumps(doc)


def layer_files(layer: Path) -> list[Path]:
    """Return every file under `layer`, as a path relative to it."""
    if layer == ROOT:
        # The root is also the repo: its own files and the layer directories are not config.
        top = [path for path in ROOT.iterdir() if path.is_file() and path.name not in NOT_CONFIG]
        workflows = [path for path in (ROOT / ".github").rglob("*") if path.is_file()]
        files = [*top, *workflows]
    else:
        files = [path for path in layer.rglob("*") if path.is_file()]
    return sorted(path.relative_to(layer) for path in files if path.name != ".DS_Store")


def compose(dest: Path, layers: list[Path], *, force: bool) -> set[Path]:
    """Write every layer into `dest` and return the files written."""
    written: set[Path] = set()
    for layer in layers:
        for relative in layer_files(layer):
            source = layer / relative
            target = dest / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if relative.suffix == ".toml":
                doc = (
                    tomlkit.parse(target.read_text())
                    if target.exists()
                    else tomlkit.document()
                )
                merge(doc, tomlkit.parse(source.read_text()))
                target.write_text(tomlkit.dumps(doc))
            elif relative.name == ".gitignore":
                existing = target.read_text().splitlines() if target.exists() else []
                new = [
                    line
                    for line in source.read_text().splitlines()
                    if line not in existing
                ]
                if new:
                    target.write_text("\n".join([*existing, *new]) + "\n")
            elif (
                target.exists()
                and not force
                and target not in written
                and relative.name != ".python-version"
            ):
                print(
                    f"kept {relative}: exists, pass --force to overwrite",
                    file=sys.stderr,
                )
                continue
            else:
                shutil.copyfile(source, target)
            written.add(target)
    return written


def main() -> None:
    """Parse the command line and compose."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "layers",
        nargs="*",
        help="layer directories at the repo root, applied after the root in this order",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path(),
        help="the repo to write into (default: the working directory)",
    )
    parser.add_argument(
        "--package", required=True, help="the import name, such as my_package"
    )
    parser.add_argument("--owner", required=True, help="the GitHub owner")
    parser.add_argument(
        "--repo",
        help="the GitHub repo and PyPI name (default: the package name with - for _)",
    )
    parser.add_argument(
        "--python",
        default=RELEASED[-2],
        help=f"the floor CPython (default: {RELEASED[-2]})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite a non-TOML file that already exists",
    )
    args = parser.parse_args()

    repo = args.repo or args.package.replace("_", "-")
    layers = [ROOT, *(ROOT / name for name in args.layers)]
    for layer in layers:
        if not layer.is_dir() or (layer != ROOT and layer.name in {".github", ".git"}):
            message = f"no such layer: {layer}"
            raise SystemExit(message)

    written = compose(args.dest.resolve(), layers, force=args.force)
    for target in sorted(written):
        text = fill(target.read_text(), args.package, args.owner, repo, args.python)
        if target.name == "pyproject.toml":
            text = add_classifiers(text, args.python)
        target.write_text(text)
        print(f"wrote {target.relative_to(args.dest.resolve())}")


if __name__ == "__main__":
    main()
