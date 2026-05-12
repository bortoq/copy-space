# PyPI publishing (copy-space)

File: doc/pypi_publish.md

This document describes how to publish the Python package to PyPI without leaking credentials.

Preferred approach: trusted publishing from GitHub Releases (OIDC).
Fallback: manual token-based upload with twine.

------------------------------------------------------------

## Trusted publishing (recommended, no PyPI token)

What it is
- PyPI can trust GitHub Actions as a publisher via OIDC.
- Publishing happens from a GitHub Actions workflow, without storing a PyPI API token in GitHub secrets.

One-time setup on PyPI (project must exist)
- Go to the PyPI project page for copy-space.
- Open Publishing (Trusted publishers).
- Add a GitHub trusted publisher with:
  - Owner: bortoq
  - Repository: copy-space
  - Workflow file: publish_pypi.yml

Publish flow
- Create a git tag vX.Y.Z that matches pyproject.toml version.
- Create a GitHub Release for that tag.
- The workflow .github/workflows/publish_pypi.yml will build sdist and wheel and publish them to PyPI.

Notes
- If the trusted publisher is not configured on PyPI, the workflow will fail during publish.
- This method is recommended for future releases to avoid token handling.

------------------------------------------------------------

## Preconditions (manual token-based upload)

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

## Upload to PyPI (manual token)

  . tmp/venv_pypi/bin/activate
  export TWINE_USERNAME=__token__
  export TWINE_PASSWORD=YOUR_PYPI_TOKEN
  python -m twine upload dist/*
  deactivate

------------------------------------------------------------

## Notes

- Prefer scoped tokens after the project exists on PyPI.
- Keep tags and GitHub Releases consistent with pyproject.toml version.
