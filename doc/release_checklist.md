# Release checklist

File: doc/release_checklist.md

Goal: make releases reproducible and prevent drift between tags, package metadata, docs, and native tool artifacts.

------------------------------------------------------------

1) Pre-flight (before tagging)

- Working tree is clean.
- Local checks pass:
  - make test
  - make tdd
- GitHub CI is green on main.

------------------------------------------------------------

2) Version consistency

- Decide release version X.Y.Z.
- Ensure pyproject.toml project version is X.Y.Z.
- Ensure docs and examples do not reference unstable test-only paths.
  Prefer examples/ for user-facing inputs.

------------------------------------------------------------

3) Tag and push

- Create an annotated tag vX.Y.Z on the intended commit.
- Push the tag to GitHub.

------------------------------------------------------------

4) Native tool artifacts

- Confirm the Release native tools workflow ran on the tag.
- Confirm artifacts exist for:
  - linux
  - macos
  - windows
- Confirm the assets are attached to the GitHub Release.

------------------------------------------------------------

5) PyPI publishing (optional)

- See doc/pypi_publish.md

------------------------------------------------------------

5) Bench and history

- Confirm CI bench smoke is green on the release commit.
- Confirm GitHub Pages bench history updates as expected.

------------------------------------------------------------

6) Docs status

- Ensure doc/status.md reflects the release state.
- Ensure doc/roadmap.md does not claim unfinished items are done.

------------------------------------------------------------

7) Post-release sanity

- In a clean venv, check:
  - pip install -e .
  - copyspace-validate --help
  - copyspace-solve --help
  - copyspace-pilot --help
