# templates

A [Copier](https://copier.readthedocs.io/) template for every repo: the hooks, configs and workflows, with the reason for each setting as a comment beside it.

## Use it

```sh
uvx copier copy gh:ozanozbeker/templates my-repo
```

Copier asks the questions in `copier.yml` and writes the files that the answers call for.
Then, in the new repo:

```sh
uv sync && uv run prek install && uv run prek run --all-files
```

A repo made from the template keeps a `.copier-answers.yml`.
When the template changes, `uvx copier update` in that repo re-applies the newest tag and merges the change onto the repo's own edits.

## Questions

| Question       | Decides                                                                                            |
| -------------- | -------------------------------------------------------------------------------------------------- |
| `repo`         | The GitHub and PyPI name, the links in `pyproject.toml`, `SECURITY.md` and the badges              |
| `owner`        | The GitHub owner in every link                                                                     |
| `language`     | The template directory: `python`, or `base` for a repo of prose and config                        |
| `package`      | The import name under `src/`                                                                       |
| `python_floor` | `.python-version`, `requires-python`, the classifiers and the CI matrix from the floor up          |
| `pypi`         | release-please, trusted publishing to PyPI, and the release-please config                          |
| `docs`         | The `docs` dependency group, the `docs` job, and the `site` and `pages` jobs after each release    |
| `framework`    | ruff and pytest settings for Dagster or FastAPI, and their dev tools                               |

`python_released`, `python_next` and `python_versions` are computed in `copier.yml`, never asked.
Add a CPython to `python_released` at its final release, and move `python_next` when the next version reaches its first beta.

## Layout

```text
copier.yml   the questions, the computed versions, and the settings
shared/      the files every language takes, with `{% if language == "python" %}` blocks
base/        a repo with no code: each file is one line, `{% include "shared/..." %}`
python/      the shared includes, plus ruff, ty, pyproject, src/, tests/ and the release workflows
```

`language` picks the directory Copier renders, through `_subdirectory`.
A new language is a new directory with the same includes and its own files.

A file that ends in `.jinja` is rendered, and any other file is copied as is.
A name wrapped in `{% if ... %}` exists only when the answer holds, so `{% if pypi %}release.yml{% endif %}.jinja` is written for a PyPI package only.

A workflow wraps each GitHub `${{ }}` expression in `{% raw %}`, so Jinja leaves it alone; the `+%}` on `endraw` keeps the line break that `trim_blocks` would otherwise drop.
Because of the blocks, a `.jinja` file is not valid TOML or YAML until rendered, so the check is to render and run the hooks on the result.

The workflows pin each action to a SHA.
Dependabot bumps the pin in each repo made from the template; bump it here too, so the next `copier update` does not revert it.

## Not here

`README.md`, `src/` and `tests/` are written once and never updated, because they are the repo's own after that.
The repository settings, rulesets and environments are applied with `gh`, not written as files.
