# Comparison notes (2026-11-16)

Sources reviewed:

- https://github.com/initialcommit-com/git-sim (README, `git check-ignore` section)
- https://github.com/Yecine-stack/gitignore-doctor (README, Explain, Audit, JSON and CI sections)

Both already explain ignore behavior. Git-sim also supports broad Git simulation, visual rule cards and more rule scopes. GitIgnore Doctor also detects potentially missing, unused and broad rules. Merely using Git, offering local operation, JSON or CI is **not new**.

Ignore Impact combines candidate root-rule editing, repository-wide before/after verdicts and user-authored exact-path expectations in one local workbench. Neither reviewed README documents that exact combined workflow. This is documentation-based evidence only, not proof that no version, plugin or script can provide it. GitIgnore Doctor was subsequently run on the same fixture as documented below. Git-sim has not been run; overall superiority has not been demonstrated. A maintainer can build similar functionality from Git commands.

## Reproducible acceptance scenario

In an isolated fixture, create `.gitignore` containing `*.log`, files `build.log`, `src/main.py`, `.env`, and a tracked `tracked.log`. Compare a candidate `*.log\n.env\nsrc/\n`.

Expected:
- `.env` and `src/main.py` become newly ignored.
- `tracked.log` stays included but displays its matching rule and tracked warning.
- Contract `ignore=[".env"]`, `include=["src/main.py"]` yields one pass and one fail.
- Source content, index and ignore files remain unchanged.

This scenario tests a useful, specific workflow; it does not establish higher quality across all competitor capabilities.

## Same-fixture execution against GitIgnore Doctor

Executed on Linux with Python 3.12.14 and Git 2.52.0, using GitIgnore Doctor commit `b519e0f5c3e799da4bb948e4ff274fa19c35c8ba` from its upstream repository. The fixture also included `nested/.gitignore` with `*.tmp` and `!keep.tmp`, plus `nested/a.tmp` and `nested/keep.tmp`.

- Doctor `explain build.log` correctly returned ignored, `.gitignore:1`, `*.log`. This is shared basic capability, not an advantage claimed here.
- Doctor `audit --json` identified `.env` as missing a rule (and reported `keep.tmp` as possibly unused).
- Its actual CLI help exposed `audit`, `explain`, and `explain-rule`; passing a candidate-rule option to `audit` failed with exit 2, unknown option.
- For an equivalent after-state, a **separate copy** of the fixture was made and its root ignore rules replaced with `*.log`, `.env`, `src/`. Doctor's audit no longer reported `.env`; it did not express the user-specific expectation that `src/main.py` must remain included.
- Ignore Impact's single candidate+contract invocation on the original fixture reported exactly two newly ignored paths (`.env`, `src/main.py`), `.env` must-ignore passed, tracked.log must-ignore failed, and src/main.py must-include failed. Exit 1 correctly signaled failed expectations. Hashes of all original fixture files, including Git metadata, were unchanged.

The demonstrated advantage is **direct, non-mutating candidate-rule impact plus explicit user-intent checks in one workflow**, compared with this tested Doctor CLI. It is not a speed benchmark or a claim that Doctor's broader heuristic audits are inferior. Git-sim was **not executed** in this comparison; its capabilities above remain documentation-based.
