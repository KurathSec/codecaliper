# Releasing codecaliper

A release is a calibration event, not just a version bump: every release
states **three versions** (package · spec · grammars — see CHANGELOG.md), and
the tag is what mints the citable, archival artifact (PyPI package + GitHub
Release + Zenodo DOI). The pipeline itself is `.github/workflows/release.yml`.

## One-time setup (before the first tag)

1. **PyPI trusted publishing** (no API tokens). On <https://pypi.org>, go to
   *Account settings → Publishing → Add a new pending publisher* and register:

   | field | value |
   |---|---|
   | PyPI project name | `codecaliper` |
   | Owner | `KurathSec` |
   | Repository name | `codecaliper` |
   | Workflow name | `release.yml` |
   | Environment name | `pypi` |

   The project name is claimed on the first successful publish; nothing else
   to reserve.
2. **GitHub `pypi` environment.** *Repo → Settings → Environments → New
   environment → `pypi`*. Optional but recommended: add yourself as a
   required reviewer so the publish job pauses for a manual approval.
3. **Zenodo webhook.** On <https://zenodo.org> → *GitHub* → flip the toggle
   for `KurathSec/codecaliper` (done 2026-07-05). Zenodo archives every
   *published* GitHub Release: the first one mints both a version DOI and the
   permanent concept DOI.
4. **GitHub Pages** (docs site, `.github/workflows/docs.yml`): *Repo →
   Settings → Pages → Source: GitHub Actions* (done 2026-07-10; the site is
   live). This was mandatory before the first push of `docs.yml` to main —
   automatic enablement needs an admin-scoped token the workflow
   `GITHUB_TOKEN` can never hold; until the switch is flipped the
   `docs / deploy` job fails with a 403.

## Per-release procedure

1. `main` is green and the working tree is clean.
2. Bump `src/codecaliper/_version.py` to `X.Y.Z` (drop the `.dev0`).
   The package version is independent of the spec version: a spec MAJOR bump
   (a calibrated number changed) must be visible in the package version too —
   never ship a new spec under an already-released package version.
3. In `CHANGELOG.md`, rename `## [Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD`
   and check the `package · spec · grammars` line still matches
   `src/codecaliper/_version.py`, `spec/rulings/index.toml`, and
   `spec/validated_grammars.toml`. The release workflow extracts this section
   verbatim as the GitHub Release notes.
4. Commit (`Release vX.Y.Z`), push, wait for CI to go green.
5. Tag and push the tag (fail-fast: the spec version is read first, so a
   broken environment aborts instead of minting a tag with a mangled
   message):

   ```bash
   spec=$(.venv/bin/python -c 'from codecaliper import spec_version; print(spec_version())') \
     && git tag -a vX.Y.Z -m "codecaliper X.Y.Z (spec $spec)" \
     && git push origin vX.Y.Z
   ```

6. The `release` workflow then runs: **gate** (full suite + spec-docs
   staleness at the tagged commit) and **build** (sdist+wheel; refuses a tag
   that is not in main's history, does not match `_version.py`, is a dev
   version, or has no CHANGELOG section; asserts the sdist ships no excluded
   paths) in parallel → **publish-pypi** (trusted publishing) →
   **github-release** (publishes the Release with the CHANGELOG section as
   notes, which fires the Zenodo webhook). A PyPI failure therefore never
   leaves a Release/DOI pointing at an unpublishable build.
7. If a run fails partway, fix the cause and use **"Re-run failed jobs"** —
   never "Re-run all jobs": completed jobs are not idempotent (the artifact
   upload rejects a duplicate name), so a full re-run of a
   partially-published release strands the remaining steps. Re-running the
   failed jobs converges from any point: `publish-pypi` skips files PyPI
   already accepted (`skip-existing: true`), and a failure after PyPI
   publication is finished by re-running `github-release`.

## Post-release

1. Verify in a clean venv: `pip install codecaliper==X.Y.Z` and
   `codecaliper cite` (it must print the released version and spec).
2. Zenodo: the new record appears under *GitHub* within minutes. After the
   FIRST release, record the **concept DOI** (the one that always resolves to
   the latest version) in:
   - `README.md` — DOI badge next to the CI badge,
   - `CITATION.cff` — an `identifiers:` entry of type `doi`,
   - `paper/` (local, gitignored) — the availability section of the tool
     paper.
3. Open the next cycle: bump `_version.py` to the next `.dev0`, start a fresh
   `## [Unreleased]` CHANGELOG section, commit.

## What deliberately does NOT happen here

- No timestamps or DOIs are written into measurement outputs — provenance is
  spec/ruling/grammar versions only (`test_determinism.py`).
- `CITATION.cff` is never version-bumped: its `version`/`date-released`
  fields are deliberately absent, because Zenodo and GitHub take both from
  the published release itself and a hand-maintained copy would only drift.
- The BW faithfulness pipeline is NOT run in CI or at release time: fetching a
  third-party research corpus stays a deliberate local action
  (`validation/bw_faithfulness/README.md`). Releases ship only the tracked
  artifacts in `derived/`. Licence status per corpus is in `dataset.toml`: the
  Buse-Weimer author granted redistribution and derived publication; the
  Scalabrino 2018 and Dorn 2012 corpora have no permission at all and are never
  redistributed, only measured.
