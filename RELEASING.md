# Releasing codecaliper

A release is a calibration event, not just a version bump. Every release states
**three versions** (package · spec · grammars, see CHANGELOG.md), and the tag is
what mints the citable, archival artifact: the PyPI package, the GitHub Release
and the Zenodo DOI. The pipeline itself is `.github/workflows/release.yml`.

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
   environment → `pypi`*. Optional but recommended: add yourself as a required
   reviewer, so the publish job pauses for a manual approval.
3. **Zenodo webhook.** On <https://zenodo.org> → *GitHub* → flip the toggle for
   `KurathSec/codecaliper` (done 2026-07-05). Zenodo archives every *published*
   GitHub Release, and the first one mints both a version DOI and the permanent
   concept DOI.
4. **GitHub Pages** (the docs site, `.github/workflows/docs.yml`): *Repo →
   Settings → Pages → Source: GitHub Actions* (done 2026-07-10; the site is
   live). This was mandatory before the first push of `docs.yml` to main:
   automatic enablement needs an admin-scoped token that the workflow
   `GITHUB_TOKEN` can never hold, and until the switch is flipped the
   `docs / deploy` job fails with a 403.

## Version stamps: get the order right

The derived reports under `validation/bw_faithfulness/derived/` **stamp the
package version that generated them**. `extract.py` reads
`codecaliper._version.__version__` into `extract_meta.json`, and `report.py`
renders it into the report header ("codecaliper X.Y.Z, spec S").

So `_version.py` must be finalised **before** those reports are regenerated and
before the tag is cut. Regenerate in the wrong order and the archived, citable
artifact ships reports stamped `X.Y.Z.dev0`, advertising a development build as
the released one.

This is not hypothetical. v0.1.0's archived reports carry
`codecaliper 0.1.0.dev0` for exactly this reason: they were regenerated while
the tree was still on the pre-release version. The numbers in them are correct;
only the version string is wrong. Step 2 below is where that gets prevented.

## Per-release procedure

1. `main` is green and the working tree is clean.
2. Bump `src/codecaliper/_version.py` to `X.Y.Z` (drop the `.dev0`). The package
   version is independent of the spec version, but a spec MAJOR bump (a
   calibrated number changed) must be visible in the package version too: never
   ship a new spec under an already-released package version.
3. **Read the stamps the committed artifacts carry, and regenerate any that is
   not `X.Y.Z`.** The question is not "did anything feeding them change", it is
   "do they already say the version being released". Three tracked artifacts
   stamp the package version that generated them:

   ```bash
   grep -h '"tool_version"' validation/bw_faithfulness/derived/*.json
   grep -h '^- codecaliper' validation/bw_faithfulness/derived/bw_faithfulness_report.md
   grep -h '"tool_version"' tests/snapshots/corpus_values.json
   ```

   If every stamp already reads `X.Y.Z`, leave them alone: they are correct for
   the release that produced them, and a needless re-run only churns the diff. If
   any stamp reads a `.dev0`, or any other version, regenerate **now**, after step
   2, so that it cannot. The drift snapshot is one command
   (`python tools/update_snapshot.py`, which still refuses a numeric change). The
   Buse-Weimer lane is self-contained and needs no network (its raw inputs are
   tracked pins), but it does need the `[retrain]` ML stack:

   ```bash
   pip install -e ".[dev,retrain]" -c constraints/ci.txt -c constraints/retrain.txt
   cd validation/bw_faithfulness && python extract.py && python train.py && python report.py
   ```

   Then confirm that the regeneration moved **only** the version string, with no
   numeric change anywhere in the diff, and commit the results with the bump.

   Both greps above are deliberately non-recursive. `derived/arbitration_inputs/`
   holds the **pinned inputs** of the pre-registered arbitration, not outputs, and
   their `0.1.0.dev0` stamps are a true statement about the build that produced
   them. Regenerating those would not fix a stale stamp, it would falsify a
   record. Leave them alone.

   Keying this step off the *inputs* is the mistake that has now been made twice.
   The stamp goes stale whenever the lane is re-run mid-cycle, which is a normal
   thing to do and has nothing to do with whether anything feeding it changed.
   0.1.0 shipped reports stamped `0.1.0.dev0` that way, and 0.1.1 would have
   shipped reports stamped `0.1.1.dev0` for the same reason, because the lane had
   been re-run during the cycle when its raw inputs were tracked into the tree.
4. In `CHANGELOG.md`, rename `## [Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD` and
   check that the `package · spec · grammars` line still matches
   `src/codecaliper/_version.py`, `spec/rulings/index.toml` and
   `spec/validated_grammars.toml`. The release workflow extracts this section
   verbatim as the GitHub Release notes.
   Then grep the prose docs for the version strings being superseded: README.md,
   ARCHITECTURE.md, docs/index.md and docs/quickstart.md all quote released
   output ("CC = 7 under spec ...", the `codecaliper env` plate, the
   `codecaliper cite` line, the quickstart JSON excerpt), and every one of them
   went stale at both 0.1.1 and 0.2.0 because this step keyed off the CHANGELOG
   alone. Regenerate those blocks from the release being cut, not by hand.
5. Commit (`Release vX.Y.Z`), push, and wait for CI to go green.
6. Tag and push the tag. This is fail-fast: the spec version is read first, so a
   broken environment aborts instead of minting a tag with a mangled message.

   ```bash
   spec=$(.venv/bin/python -c 'from codecaliper import spec_version; print(spec_version())') \
     && git tag -a vX.Y.Z -m "codecaliper X.Y.Z (spec $spec)" \
     && git push origin vX.Y.Z
   ```

7. The `release` workflow then runs **gate** (the full suite plus spec-docs
   staleness at the tagged commit) and **build** (sdist and wheel; it refuses a
   tag that is not in main's history, does not match `_version.py`, is a dev
   version, or has no CHANGELOG section, and it asserts the sdist ships no
   excluded paths) in parallel, then **publish-pypi** (trusted publishing), then
   **github-release**, which publishes the Release with the CHANGELOG section as
   its notes and thereby fires the Zenodo webhook. A PyPI failure therefore never
   leaves a Release or a DOI pointing at an unpublishable build.
8. If a run fails partway, fix the cause and use **"Re-run failed jobs"**, never
   "Re-run all jobs". Completed jobs are not idempotent (the artifact upload
   rejects a duplicate name), so a full re-run of a partially-published release
   strands the remaining steps. Re-running the failed jobs converges from any
   point: `publish-pypi` skips files PyPI already accepted
   (`skip-existing: true`), and a failure after PyPI publication is finished by
   re-running `github-release`.

## Post-release

1. Verify in a clean venv: `pip install codecaliper==X.Y.Z` and
   `codecaliper cite`, which must print the released version and spec.
2. Zenodo: the new record appears under *GitHub* within minutes. After the FIRST
   release, record the **concept DOI** (the one that always resolves to the
   latest version) in:
   - `README.md`, the DOI badge next to the CI badge,
   - `CITATION.cff`, an `identifiers:` entry of type `doi`,
   - `paper/` (local, gitignored), the availability section of the tool paper.
3. Open the next cycle: bump `_version.py` to the next `.dev0`, start a fresh
   `## [Unreleased]` CHANGELOG section, and commit.

## What deliberately does NOT happen here

- No timestamps and no DOIs are written into measurement outputs. Provenance is
  spec, ruling and grammar versions only (`test_determinism.py`).
- `CITATION.cff` is never version-bumped. Its `version` and `date-released`
  fields are deliberately absent, because Zenodo and GitHub take both from the
  published release itself, and a hand-maintained copy would only drift.
- The BW faithfulness pipeline does not run in CI, and does not run at release
  time either unless step 3 above applies. It is self-contained, so needing a
  network is not the reason; re-running it pulls the whole `[retrain]` ML stack,
  which keeps it a deliberate local action
  (`validation/bw_faithfulness/README.md`). Releases ship the tracked pins and
  the tracked artifacts under `derived/`.
- No release adds dataset content. The wheel is the package alone; the sdist is
  the tracked tree minus the paths excluded in `pyproject.toml`, so it carries
  the tracked Buse-Weimer pins and never the gitignored `cache/`, and the build
  job asserts exactly that. Permission status per corpus is in `PERMISSIONS.md`,
  and machine-readably in `dataset.toml`.
