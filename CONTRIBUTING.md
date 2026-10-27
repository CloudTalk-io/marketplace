# Contributing

Thanks for helping improve CloudTalk's Claude plugins. Open a pull request for every change —
small, focused PRs are easiest to review.

## Run the checks locally

The validator test suite (stdlib Python, no dependencies):

```bash
python3 plugins/cloudtalk/skills/voice-agent-builder/scripts/test_validate.py
```

The docs-sync check, which verifies the schema docs and `fields.json` agree:

```bash
python3 plugins/cloudtalk/skills/voice-agent-builder/scripts/check_docs_sync.py
```

If you have the Claude Code CLI installed, also validate the plugin structure from the repo root:

```bash
claude plugin validate .
claude plugin validate ./plugins/cloudtalk
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

## Writing a skill

`voice-agent-builder` is the reference for how a CloudTalk skill is built. Every skill in
`plugins/cloudtalk` follows the same shape, so a model can run it the same way every time and a
reviewer can check it against this list.

1. **The description is the trigger.** Frontmatter `description` says what the skill does, then when to
   use it, with the phrasings users actually type, and what it needs (plan, add-on). The body never
   repeats it.
2. **One job, stated first.** A one-line goal and what "done" looks like for the user. Explicit user
   instructions always win over the skill.
3. **Two kinds of input, treated oppositely.** *Judgment* (wording, ranking, what to recommend) the skill
   authors without asking. *Ground truth* (names, numbers, IDs, dates, what was said on a call) it reads
   from CloudTalk or asks for, in one batch, and never invents, defaults or copies from an example.
4. **A numbered workflow with gates.** Each step names the exact tools and arguments (including which of
   the two voice agent IDs, date formats, `limit`s and pagination). A step that must not be skipped ends
   with a `> **✓ Gate:**` checklist the model checks before moving on.
5. **Honest limits.** Say what CloudTalk cannot do and offer the nearest real path. Plan-gated data
   (Conversation Intelligence, Sales Dialer, AI Voice Agents) is reported once, not per call. Calls under
   30 seconds have no transcript or insights, for people and AI Voice Agents alike.
6. **An exact output shape.** Sections in order, what each line contains, how evidence is cited (call id,
   a short quote), and a coverage line saying what was read and what was not.
7. **Writes are the user's decision.** Reads run straight away. A write runs on one call after saying
   what will happen, and the app asks the user to approve it; never write what the user did not ask for.
   A write's result, not the attempt, is what you report.
8. **Budget and privacy.** The account allows 60 requests per minute: cap detail reads, fetch in parallel
   only where the app allows, and back off a minute on a rate-limit error. Show phone numbers and
   customer details only when the task needs them, masked otherwise.
9. **Non-negotiables last.** A short list of rules that hold whatever else happens, each one a rule the
   skill has actually broken or could plausibly break.
10. **Runs in Claude and ChatGPT.** No Python, subagents or host-specific features in `skills/`; anything
    that needs them lives in `claude-skills/`. Every skill in `skills/` has `agents/openai.yaml`. Skills
    talk to people in plain words: no company ids, user ids or tool names in what the user reads.
