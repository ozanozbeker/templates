"""compose writes a repo that parses, has no placeholder left, and keeps what `uv init` wrote.

tomlkit reads the TOML 1.1 multi-line inline tables in `prek.toml`; tomllib reads them from Python 3.15 only.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

# S603: every argument is a literal or a pytest path.
# ruff: noqa: S603
import tomlkit

ROOT = Path(__file__).resolve().parent.parent
COMBOS = [
    [],
    ["python"],
    ["python", "library"],
    ["python", "dagster"],
    ["python", "fastapi"],
    ["python", "library", "dagster"],
]


def compose(dest: Path, layers: list[str], *extra: str) -> None:
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "compose.py"),
            "--dest",
            str(dest),
            "--package",
            "my_pkg",
            "--owner",
            "me",
            "--python",
            "3.12",
            *extra,
            *layers,
        ],
        check=True,
        capture_output=True,
    )


@pytest.mark.parametrize(
    "layers", COMBOS, ids=lambda layers: "+".join(layers) or "base"
)
def test_every_file_parses_and_no_placeholder_remains(
    tmp_path: Path, layers: list[str]
) -> None:
    compose(tmp_path, layers)
    for path in tmp_path.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text()
        assert "<" not in text.replace("<<", ""), (
            f"{path.relative_to(tmp_path)} holds a placeholder"
        )
        if path.suffix == ".toml":
            tomlkit.parse(text)
        if path.suffix == ".json":
            json.loads(text)
        assert not any(line != line.rstrip() for line in text.splitlines()), (
            f"{path.relative_to(tmp_path)} has trailing whitespace"
        )


def test_python_layer_fills_versions(tmp_path: Path) -> None:
    compose(tmp_path, ["python"])
    pyproject = tomlkit.parse((tmp_path / "pyproject.toml").read_text())
    assert pyproject["project"]["requires-python"] == ">=3.12"
    assert (
        "Programming Language :: Python :: 3.12" in pyproject["project"]["classifiers"]
    )
    assert (
        "Programming Language :: Python :: 3.11"
        not in pyproject["project"]["classifiers"]
    )
    assert (tmp_path / ".python-version").read_text() == "3.12\n"
    ci = (tmp_path / ".github/workflows/ci.yml").read_text()
    assert 'python: ["3.12", "3.13", "3.14", "3.15"]' in ci
    assert '- { os: macos-latest, python: "3.13" }' in ci
    assert '- { os: macos-latest, python: "3.12" }' not in ci


def test_floor_next_to_newest_drops_the_exclude(tmp_path: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "compose.py"),
            "--dest",
            str(tmp_path),
            "--package",
            "p",
            "--owner",
            "me",
            "--python",
            "3.14",
            "python",
        ],
        check=True,
        capture_output=True,
    )
    ci = (tmp_path / ".github/workflows/ci.yml").read_text()
    assert "exclude:" not in ci
    assert "skip the middle versions" not in ci


def test_toml_merges_onto_what_uv_init_wrote(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "my-pkg"\nversion = "0.1.0"\nrequires-python = ">=3.14"\n\n[build-system]\nrequires = ["uv_build"]\nbuild-backend = "uv_build"\n'
    )
    (tmp_path / ".python-version").write_text("3.14\n")
    compose(tmp_path, ["python", "dagster"])
    pyproject = tomlkit.parse((tmp_path / "pyproject.toml").read_text())
    assert pyproject["project"]["name"] == "my-pkg"
    assert pyproject["project"]["requires-python"] == ">=3.12"
    assert pyproject["build-system"]["build-backend"] == "uv_build"
    assert pyproject["tool"]["pytest"]["ini_options"]["pythonpath"] == ["."]
    assert "dagster-dg-cli" in pyproject["dependency-groups"]["dev"]
    assert (tmp_path / ".python-version").read_text() == "3.12\n"


def test_library_layer_adds_the_docs_job(tmp_path: Path) -> None:
    compose(tmp_path, ["python", "library"])
    ci = (tmp_path / ".github/workflows/ci.yml").read_text()
    assert "  docs:\n" in ci
    assert "great-docs build" in ci
    assert "hashFiles" not in ci


def test_layers_merge_toml_arrays_without_duplicates(tmp_path: Path) -> None:
    compose(tmp_path, ["python", "library", "dagster"])
    prek = tomlkit.parse((tmp_path / "prek.toml").read_text())
    assert [repo["repo"] for repo in prek["repos"]].count("local") == 1
    assert prek["default_language_version"]["python"] == "3.12"
    rumdl = tomlkit.parse((tmp_path / "rumdl.toml").read_text())
    assert rumdl["global"]["exclude"] == ["docs/agents/", "CHANGELOG.md"]
    assert rumdl["global"]["flavor"] == "quarto"
    ruff = tomlkit.parse((tmp_path / "ruff.toml").read_text())
    assert "CPY001" in ruff["lint"]["ignore"]
    assert "**/definitions.py" in ruff["lint"]["per-file-ignores"]


def test_an_existing_file_is_kept_without_force(tmp_path: Path) -> None:
    (tmp_path / "SECURITY.md").write_text("mine\n")
    compose(tmp_path, [])
    assert (tmp_path / "SECURITY.md").read_text() == "mine\n"
    compose(tmp_path, [], "--force")
    assert "private vulnerability reporting" in (tmp_path / "SECURITY.md").read_text()
