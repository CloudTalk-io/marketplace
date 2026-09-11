# Voice Agent v2 — Expert Mode configuration corpus

The reference set for generating and hand-authoring **Voice Agent v2 (Expert Mode)** JSON configs — used
**offline** (paste the JSON into the dashboard's Advanced/code tab to edit an agent) or **connected**
(the CloudTalk MCP reads and writes the agent directly against your account; every write asks for your
confirmation first).

> **Spine:** one tier-tagged schema is the single source of truth. Every field is tagged with an
> `authoring` class (see below). Each doc here is a *thin lens* that points at that schema rather
> than restating it — so one fact lives in exactly one place.

This folder **is** a Claude Skill (open [Agent Skills](https://agentskills.io) format).
[`SKILL.md`](./SKILL.md) is the entry point: its `description` is the trigger, and its body is a lean
workflow router. The lens docs below are bundled references the skill loads **on demand** (progressive
disclosure). It ships as part of the CloudTalk plugin — see the repo README for installation and for
connecting your account. Its sibling skill,
[`simulate-conversation`](../simulate-conversation/README.md), roleplays a caller against a finished
config and judges the transcript.

## Who reads what

| You are… | Start with | Then |
|---|---|---|
| **The config-generation skill** (LLM) | [`SKILL.md`](./SKILL.md) — the skill entry/router (loaded on invocation) | [`generator-contract.md`](./generator-contract.md) emit policy, [`schema.md`](./schema.md) shapes, [`behavioral-guidance.md`](./behavioral-guidance.md) quality, [`examples/`](./examples/) few-shots |
| **A person wiring a config's resources** (numbers, KBs, tools, transfers, calendars) | [`referenced-resources.md`](./referenced-resources.md) — what each referenced/environment field needs, connected and Dashboard paths | [`mcp-tools.md`](./mcp-tools.md) for the connected tool surface, [`schema.md`](./schema.md) for the field's shape |
| **Anyone authoring/validating by hand** | [`schema.md`](./schema.md) — full structural reference, every field tagged | [`behavioral-guidance.md`](./behavioral-guidance.md), [`variables.md`](./variables.md), [`examples/`](./examples/) |

## Files

| File | Owns (single source of truth for…) |
|---|---|
| [`SKILL.md`](./SKILL.md) | The Claude Skill entry point: trigger `description` + the lean workflow router that points at the lenses below. |
| [`scripts/validate_config.py`](./scripts/validate_config.py) | Structural + behavioral validator (stdlib Python 3.8+). Keys off `fields.json`; reports errors, behavioral warnings, and what still needs wiring. |
| [`fields.json`](./fields.json) | The field set + each field's `authoring` tag. Machine-readable spine. |
| [`schema.md`](./schema.md) | Field shapes, enums, dependency rules, provider/LLM auto-selection. Human view of `fields.json`. |
| [`behavioral-guidance.md`](./behavioral-guidance.md) | What makes a config *perform well* (prompt architecture, hangup coverage, language, overriding platform defaults, self-check). Provider-agnostic quality. |
| [`generator-contract.md`](./generator-contract.md) | How the skill *emits*: per-tier policy, the reference decision tree (reuse / fetch / substitute / ask / omit), the connected-mode write contract, output shape. |
| [`referenced-resources.md`](./referenced-resources.md) | For each `reference`/`environment` field: what it is, how to create it, how to wire the ID — connected and Dashboard paths. |
| [`mcp-tools.md`](./mcp-tools.md) | Connected mode: the CloudTalk MCP tool surface, write-safety rules, and the not-yet-available workaround table. |
| [`variables.md`](./variables.md) | Every `{{variable}}` the platform resolves — when it resolves, what it contains, and the silent empty-string behavior when unset. |
| [`examples/`](./examples/) | E1–E10 worked configs — clean, schema-only, save-ready: no placeholder IDs inside a *live* reference, but every non-E2 file carries a placeholder `failoverOutboundNumberId` to replace, and E4/E9/E10 carry further marked illustrative values (each named in the file's header). Executable documentation + few-shots. |

## The `authoring` tiers (full field partition)

Every field is exactly one of these. The first three are the emittable spectrum; `forbidden` closes
the partition so "never emit" is an explicit signal, not folklore.

| Tag | Meaning | Generator behavior |
|---|---|---|
| `generate` | Self-contained content/choice/number | Author it freely |
| `reference` | Points to a company resource by ID | Reuse, fetch over MCP, substitute, ask the user for the real ID, ship the skill switched off (transfers), or omit + instruct; **never a placeholder, never a guess** |
| `environment` | Env-specific phone-number selector | Defaults to `1` (Automatic), exactly as the dashboard seeds it — complete it with a real owned `failoverOutboundNumberId` in both directions, or set a real owned `defaultOutboundNumberId` directly (reuse/fetch/ask). Never guess `2`, never `null`, never a bare `1` with no failover — only `1` is magic and it still needs a real failover |
| `forbidden` | Computed / response-only, **or** system-managed by the dashboard/platform (`presetType`, `status`, `lastConfigurationStep`, `hasOverrides`) | Never emit. The platform sets these on save/create; authoring them is stripped, ignored, or overridden on import |

## "Nothing else to wire" — what's actually true

You first create an agent in the UI — usually just a **blank shell to unlock Expert Mode** — then edit it
(connected write, or paste). So the skill **generates the config fresh** for your use case, carrying over
only the shell's real IDs, not its behavior. **The common inbound assistant — greet, answer, capture, hang
up — needs no company resource of its own**, so its skills and scenarios are zero-touch; the one thing it
still needs is the **outbound number completed**: `defaultOutboundNumberId` defaults to `1` (Automatic, as
the dashboard seeds it), which needs a real owned `failoverOutboundNumberId` in both directions to be
save-ready — reuse the agent's, fetch it with `cloudtalk_list_numbers`, or the user completes it in the
dashboard; setting a real owned `defaultOutboundNumberId` directly is the alternative. The save `400`s on a
bare `1`, and nothing self-heals.

Two things add a step, and the skill is explicit about both rather than papering over them:
1. a `reference` field whose resource doesn't exist yet (the `reference`-tagged fields in
   [`fields.json`](./fields.json) — KB, custom tool, calendar, SMS sender), or
2. a **transfer to a human**. There is no zero-touch substitute for reaching a person: either the real
   agent/group **id + extension** is known (fetched or supplied) and it ships wired, or the skill arrives
   **switched off** (`enabled: false`, `rules: []`) with exactly one thing left to do — pick the target on
   that skill in the dashboard (it shows *"Requires configuration"*) and switch it on.

The generator **never ships a config that fails to save**, and never invents an ID to look complete: it
reuses an ID the agent already has, fetches one over MCP, prefers a self-contained substitute where one
exists (facts in the prompt instead of a KB), **asks for the real ID** and bakes it in, or ships the
feature off/omitted and lists the one remaining step in its chat reply. See
[`generator-contract.md`](./generator-contract.md) for the decision tree.

## Adding a new config field (maintenance recipe)

When the platform grows a field, the corpus absorbs it in one pass — touch each layer, in this order:

1. [`fields.json`](./fields.json) — the entry with its `authoring` tier (+ `enum`/`range` where stable).
2. [`schema.md`](./schema.md) — the §2 table row (same `authoring` tag) + a §3 dependency rule if
   cross-field + a §-section if the field is compound.
3. [`scripts/validate_config.py`](./scripts/validate_config.py) — the shape constant + check, unless the
   fields.json `enum`/`range` already covers it.
4. [`behavioral-guidance.md`](./behavioral-guidance.md) — what value to pick and why + a §8 self-check row.
5. [`scripts/test_validate.py`](./scripts/test_validate.py) — positive + negative assertions.
6. [`examples/`](./examples/) — demonstrate it in one example when user-facing.
7. `CHANGELOG.md` (repo root) — a dated entry, since consumers always track latest.

CI runs [`scripts/check_docs_sync.py`](./scripts/check_docs_sync.py), which fails the build when
`fields.json`, `schema.md` and the validator's mirrored enums drift apart. It checks exactly this: the
§2 field set + `authoring` tiers, the §4.2 per-provider LLM matrix, the §4.3 Deepgram language list plus
the plain-two-letter-code rule provider resolution keys off, the §4.4 premade voice IDs, the §11 `tone`
and `verbosity` enums, the §7.1 scenario actions, and the `elevenLabsSettings` sub-field set. Everything
else — thresholds, skill shapes, the legacy-alias map — is on the author: steps 1–3 above are
machine-checked, steps 4–7 are not.
