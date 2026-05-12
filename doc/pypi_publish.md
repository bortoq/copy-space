# PyPI publishing (copy-space)

File: doc/pypi_publish.md

This document describes how to publish the Python package to PyPI without leaking credentials.

------------------------------------------------------------

## Preconditions

- You have a PyPI account.
- You have an API token (recommended: scoped to the project after the first upload).

Optional (recommended for rehearsal):
- TestPyPI account and token.

------------------------------------------------------------

## Build artifacts (sdist + wheel)

Use an isolated venv:

  rm -rf tmp/venv_pypi dist build
  python3 -m venv tmp/venv_pypi
  . tmp/venv_pypi/bin/activate
  python -m pip install --upgrade pip
  python -m pip install build twine
  python -m build
  python -m twine check dist/*
  deactivate

------------------------------------------------------------

## Upload to TestPyPI (recommended first)

Set credentials via env vars (do not paste tokens into shells with history shared):

  . tmp/venv_pypi/bin/activate
  export TWINE_USERNAME=__token__
  export TWINE_PASSWORD=YOUR_TESTPYPI_TOKEN
  python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*
  deactivate

Verify install in a clean venv:

  rm -rf tmp/venv_testpypi
  python3 -m venv tmp/venv_testpypi
  . tmp/venv_testpypi/bin/activate
  python -m pip install --upgrade pip
  python -m pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple copy-space==X.Y.Z
  copyspace-pilot --help
  deactivate

------------------------------------------------------------

## Upload to PyPI

  . tmp/venv_pypi/bin/activate
  export TWINE_USERNAME=__token__
  export TWINE_PASSWORD=YOUR_PYPI_TOKEN
  python -m twine upload dist/*
  deactivate

------------------------------------------------------------

## Notes

- Prefer scoped tokens after the project exists on PyPI.
- Keep tags and GitHub Releases consistent with pyproject.toml version.
