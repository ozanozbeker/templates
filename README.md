# dotfiles

Config files for every repo, composed from a base and layers.

The root holds what every repo gets: prek hooks, rumdl, tombi, a `.gitignore`, `SECURITY.md`, Dependabot and the workflows that run on a pull request.
Each directory is a layer that adds what one kind of project needs, in the same tree shape.
`compose.py` writes the root and the named layers into a repo, in that order.

## Layers

| Layer     | Adds                                                                                |
| --------- | ----------------------------------------------------------------------------------- |
| `python`  | ruff, ty, pytest, coverage, the uv hooks, and a CI matrix from the floor Python up  |
| `library` | release-please, PyPI trusted publishing, a docs job, and the classifiers PyPI reads |
| `dagster` | ruff and pytest settings for a Dagster project                                      |
| `fastapi` | ruff and pytest settings for a FastAPI app                                          |

`python` comes first.
`library` is for a package on PyPI; an app skips it.
`dagster` and `fastapi` sit on top of either.

## Compose a repo

```sh
uv init --lib my_pkg && cd my_pkg
uv run ~/dotfiles/compose.py --package my_pkg --owner ozanozbeker --python 3.13 python library
```

`compose.py` merges each layer onto what the repo already has:

- A `.toml` file deep-merges.
  Tables recurse, arrays append without duplicates, and a scalar from the later layer wins, so `uv init`'s `[project]` keeps its name and build system.
- `.gitignore` appends the lines it lacks.
- Every other file is copied whole, and the later layer wins.
  An existing file is kept unless `--force` is passed.
  `.python-version` is always written, because it carries the floor.

After the copy, `<package>`, `<owner>`, `<repo>` and `<python>` are filled, and the Python versions from the floor to the newest release go into the classifiers and the CI matrix.
Run `uv sync` and `prek install` in the repo afterwards.

## Keep it current

`RELEASED` and `NEXT` in `compose.py` name the CPython versions.
Add a version at its final release, and move `NEXT` when the next version reaches its first beta.
The workflows pin each action to a SHA; bump a pin here when Dependabot bumps it in a repo that uses it.
The root's own `prek.toml`, `rumdl.toml` and `tombi.toml` are copies to hand out, not hooks that run here.

This repo is a reference, not a project: no hooks, no CI, no config of its own.
`compose.py` declares its dependencies inline, so `uv run` needs nothing else.
