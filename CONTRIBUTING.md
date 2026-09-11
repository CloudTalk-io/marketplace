# Contributing

Thanks for helping improve CloudTalk's Claude plugins. Open a pull request for every change —
small, focused PRs are easiest to review.

## Run the checks locally

The validator test suite (stdlib Python, no dependencies):

```bash
python3 plugins/voice-agent-config-generator/skills/voice-agent-config-generator/scripts/test_validate.py
```

The docs-sync check, which verifies the schema docs and `fields.json` agree:

```bash
python3 plugins/voice-agent-config-generator/skills/voice-agent-config-generator/scripts/check_docs_sync.py
```

If you have the Claude Code CLI installed, also validate the plugin structure from the repo root:

```bash
claude plugin validate .
claude plugin validate ./plugins/voice-agent-config-generator
```

CI runs on every pull request (and on pushes to `main`): the validator test suite — which also validates
every bundled example — and the docs-sync check, both **blocking**; `pre-commit` over the whole repo,
also blocking, so run the hooks locally too, not only on staged files; and `claude plugin validate .` at
the repo root, currently **advisory**.

```bash
pre-commit run --all-files
```

## Pre-commit hooks

Install [pre-commit](https://pre-commit.com/) once, then enable the repo's hooks:

```bash
brew install pre-commit   # or: pip install pre-commit
pre-commit install
```

The hooks catch large files, merge-conflict markers, stray credentials, and whitespace issues
before they reach a PR.

## Commit messages

Use conventional-commit subjects: `<type>: <subject>` (an optional scope is fine,
e.g. `fix(validator): …`).

`<type>` is one of:

- `feat` — a new capability for plugin users
- `fix` — a bug fix
- `docs` — documentation only
- `refactor` — restructuring without behavior change
- `test` — adding or reworking tests
- `chore` — maintenance (CI, tooling, housekeeping)

Example: `feat(schema): add backgroundSound to the ElevenLabs settings`

## What to update together

- Schema or validator changes: update `fields.json`, `schema.md`, `validate_config.py`, and the
  tests in the same PR, and keep the bundled `examples/` passing the validator — `test_validate.py`
  validates every one of them, so a broken example fails the suite.
- Material schema or guidance changes: bump the semver in the plugin's `.claude-plugin/plugin.json`
  and `.claude-plugin/marketplace.json`, and add a matching dated entry to [CHANGELOG.md](./CHANGELOG.md) —
  the version plus the changelog is how consumers track what changed.
