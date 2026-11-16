# Ignore Impact

**Rehearse a root `.gitignore` edit before touching your repository.**

A local, read-only workbench built with Python's standard library and real Git. Compare a candidate against the current rules, inspect every changed path and its deciding rule, then save exact-path expectations as a repeatable CLI contract. No API key, package installation or network service required.

## Start

Requires Python 3.10+ and Git on PATH. Download/extract this project, then:

```sh
python ignore_impact.py /absolute/path/to/repository
```

Open the printed `http://127.0.0.1:8766` URL. On Windows, use `py` instead of `python` if needed and quote paths containing spaces. Edit the root rules, add must-ignore/must-include paths, and click **Preview impact**. Downloading a candidate does not install it. Apply any edits yourself after review. Stop with Ctrl+C.

## Repeatable contracts

Save the contract in the UI, or write:

```json
{"ignore":[".env","dist/app.js"],"include":["src/main.py"]}
```

Use exact existing file paths relative to the repository root, including case and spaces. No wildcard contract expansion. Missing paths fail rather than silently pass.

```sh
python ignore_impact.py /path/to/repo --candidate candidate.gitignore --contract ignore-contract.json --json
```

Exit codes: 0 all supplied checks pass, 1 at least one check fails, 2 tool/input error. Without `--candidate`, check the current root rules. JSON output includes filenames and matching patterns, so review it before sharing or storing in public CI artifacts.

## Deliberate scope: portable rules

- Evaluates the root and nested working-tree `.gitignore` files using `git check-ignore --no-index -v -z` in a separate temporary Git repository.
- **Excludes global/system ignore files, `.git/info/exclude`, and source repository configuration.** These results are portable repository-rule experiments, **not an exact reproduction of your machine's `git status`**. Matching uses the temporary repository's native filesystem defaults. Case behavior can differ across operating systems.
- Reads source file paths, ignore files, and tracked-path metadata. It never copies ordinary source contents, commits, credentials, hooks or the index. Temporary placeholders are deleted after each evaluation.
- Tracked files remain included regardless of rule matches. A must-ignore contract fails for a tracked file. This is not a secret scanner or history cleaner.
- Snapshot is fixed at launch. Restart after renames, file creation, staging or changes to nested rules. The UI edits only the root rules.
- Fails on nested repositories/submodules and symlink `.gitignore` files. Directory symlinks are not followed; symlink paths are represented as file placeholders. Worktrees are supported through Git's tracked-path query, but worktree-specific ignore configuration remains excluded.
- Limit: 20,000 files, UTF-8 paths/rules, 256 KiB per ignore file, Git calls limited to 30 seconds. No partial results on overflow. UI shows at most 500 matching rows; filtering and full JSON export remain available.
- UI contract editing is line-based and therefore cannot represent filenames containing a newline; JSON CLI contracts can. No guarantee for changing repositories while snapshot capture runs.
- Local HTTP binds only to 127.0.0.1, validates Host, requires a random per-session token plus matching Origin for comparisons, serves no arbitrary filesystem paths, and sends no telemetry. Other processes or users with local access are outside this threat model.

## Relationship to other tools

[git-sim](https://github.com/initialcommit-com/git-sim) already offers excellent Git workflow simulation and visual `check-ignore` explanations, including nested/global/info-exclude rule sources and tracked files. [GitIgnore Doctor](https://github.com/Yecine-stack/gitignore-doctor) already uses Git as the oracle, explains rules, offers conservative broad/unused/missing-rule audits and has JSON/CI output.

We adopt those useful principles: real Git matching, source/line explanation, conservative conclusions, a local interface and machine-readable output. Our narrower focus is a **candidate root-rule edit → batch before/after delta → explicit path contract** workflow, without modifying the repository. This is a different workflow, not proof of overall superiority, better performance or wider Git compatibility. The other tools have features this project deliberately lacks. See `COMPARISON.md` for evidence and limitations.

MIT licensed. Original implementation; no competitor code included.
