# Contributing

Before contributing, setup githooks scripts first
(to ensure the right commit message content):

Install the [``pre-commit``](https://pre-commit.com/) in order to run the linter:

```shell
# install the pre-commit tool
brew install pre-commit

## apply the configuration
pre-commit install
pre-commit install --install-hooks -t pre-commit -t commit-msg
```

For every change to this repository please create new PR.

## Commits

Commit messages has to follow this style:

Format: `<type>(<scope>): <subject>`

- `<scope>` is Jira task, it can be `CT-<number>` or `IN-<number>` format

`<type>` can be:

- `feat`: (new feature for the user, not a new feature for build script)
- `fix`: (bug fix for the user, not a fix to a build script)
- `docs`: (changes to the documentation)
- `style`: (formatting, missing semi colons, etc; no production code change)
- `refactor`: (refactoring production code, eg. renaming a variable)
- `test`: (adding missing tests, refactoring tests; no production code change)
- `chore`: (updating grunt tasks etc; no production code change)

### Example

```
feat(CT-5555): Reworked intercom components
^--^ ^-----^   ^--------------------------^
|    |         |
|    |         +-> Commit description
|    |
|    +-> Jira task
|
+-------> Type: chore, docs, feat, fix, refactor, style, or test
```

> NOTE: All commits should be signed with the committer’s verified signature.

## Branches

Branches names has to follow this style:

Format: `<type>/(<scope>)-<description>`

- `<scope>` is Jira task, it can be `CT-<number>` or `IN-<number>` format
- `<description>` is short description of Jira task

`<type>` can be:

- `feat`: (new feature for the user, not a new feature for build script)
- `fix`: (bug fix for the user, not a fix to a build script)
- `docs`: (changes to the documentation)
- `style`: (formatting, missing semi colons, etc; no production code change)
- `refactor`: (refactoring production code, eg. renaming a variable)
- `test`: (adding missing tests, refactoring tests; no production code change)
- `chore`: (updating grunt tasks etc; no production code change)

### Example

```
feat/CT-5555-Intercom-rework
^--^  ^----^ ^-------------^
|     |      |
|     |      +-> Jira task short description
|     |
|     +-> Jira task
|
+-------> Type: chore, docs, feat, fix, refactor, style, or test
```
