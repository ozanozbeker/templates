# templates

A [Copier](https://copier.readthedocs.io/) template for every repo: the hooks, configs and workflows, with the reason for each setting as a comment beside it.

## Use it

Create the repo on GitHub, let `uv init` write the project, then render the template into the clone:

```sh
gh repo create ozanozbeker/my-repo --public --clone --add-readme --license mit --gitignore Python
cd my-repo
uv init --lib --python 3.14   # or --app
uvx copier copy gh:ozanozbeker/templates .
```

Copier asks the questions in `copier.yml` and writes the files that the answers call for.
It writes none of the files GitHub or `uv init` wrote, and when it finishes it prints what to add to `.gitignore` and `pyproject.toml` and the `uv add` line for the tools.

A repo made from the template keeps a `.copier-answers.yml`.
When the template changes, `uvx copier update` in that repo re-applies the newest tag and merges the change onto the repo's own edits.

## Questions

| Question       | Decides                                                                                            |
| -------------- | -------------------------------------------------------------------------------------------------- |
| `repo`         | The GitHub and PyPI name, and the links in `pyproject.toml` and `SECURITY.md`                      |
| `owner`        | The GitHub owner in every link                                                                     |
| `language`     | The template directory: `python`, or `none` for a repo of prose and config                        |
| `package`      | The import name under `src/`, for `.coveragerc` and the wheel check in `release.yml`               |
| `python_floor` | The CI matrix from the floor up, and the classifiers the message prints                            |
| `pypi`         | release-please, trusted publishing to PyPI, and the release-please config                          |
| `docs`         | The `docs` dependency group, the `docs` job, and the `site` and `pages` jobs after each release    |
| `framework`    | ruff and pytest settings for Dagster or FastAPI                                                    |

`python_released`, `python_next` and `python_versions` are computed in `copier.yml`, never asked.
Add a CPython to `python_released` at its final release, and move `python_next` when the next version reaches its first beta.

## Layout

```text
copier.yml   the questions, the computed versions, and the settings
shared/      the files every language takes, with `{% if language == "python" %}` blocks
none/        a repo with no code: each file is one line, `{% include "shared/..." %}`
python/      the shared includes, plus ruff, ty, pytest, coverage, typos and the release workflows
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

`README.md`, `LICENSE` and `.gitignore` are GitHub's at `gh repo create`, and `pyproject.toml`, `.python-version` and `src/` are `uv init`'s.
The template adds beside them and never writes them, which is why pytest, coverage and typos read `pytest.ini`, `.coveragerc` and `typos.toml` instead of `[tool.*]` tables.
The repository settings, rulesets and environments are applied with `gh`, not written as files.
