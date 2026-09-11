# Changelog

Each release bumps a semver (in the plugin manifest and `.claude-plugin/marketplace.json`) with a
dated entry below, made whenever the config schema or the generation guidance materially changes.
Installs still track the latest `main` — the version is a marker for the tooling and this log, not a pin.

## 0.1.0 — 2026-09-11

- **Versioning introduced.** The plugin now carries a semver (starting at `0.1.0`) in `plugin.json`
  and the marketplace catalog, bumped with each dated entry below.
- **Transfer safety corrected.** Where advanced transfer is enabled for the company, `agent` and
  `group` transfers run **attended** — the caller stays with the AI while the second leg is placed and
  a busy/declined/timed-out leg bounces back — so they are safe, not the cold-fallback risk earlier
  wording implied. `call_flow` is the only **always-cold** destination (the agent hangs up and the
  Call Flow continues), so use it only when the agent runs as a step inside a Call Flow.
- **`guardrails` is inert at runtime — keep it empty.** The array is accepted and stored, but the
  runtime has no `enabled` field for a guardrail, so every stored one decodes to disabled and is
  silently skipped. Emit `"guardrails": []` and put always-on rules in the `goalPrompt` `## Guardrails`
  prose section instead.
- **LLM registry expanded to 25 models.** All 25 are offered on ElevenLabs; 14 of them are also offered
  on Deepgram. An `llmOverride` must resolve to a model the **resolved** provider offers.
- **Default voice set is the four both-provider voices.** All four premade voice IDs are ElevenLabs
  voices that work on both ElevenLabs- and Deepgram-resolved agents; Jessica is the default (the only
  female voice in the set). Pick your preferred voice in the dashboard voice picker, which holds the
  full language-filtered catalog.
- **Outbound number: Automatic needs a real failover in both directions.** `defaultOutboundNumberId`
  defaults to `1` (Automatic), as the dashboard seeds it, which requires a real owned
  `failoverOutboundNumberId` in **both** directions (or set a real owned `defaultOutboundNumberId`
  directly). A bare `1` with no failover `400`s and nothing self-heals — complete it in the dashboard
  or resolve a number with `cloudtalk_list_numbers`.
- **Defaults aligned to the dashboard's create-time constants:** `stability` `0.3`, `similarity`
  `0.7`, `optimizeStreamingLatency` `2`, `temperature` `0.5`, `maxCallDuration` `30`; transfer drafts
  default `confirmationRequired: true` and `includeProperties: ["callerName", "summary"]`.
- **Transfer drafts omit integer ids instead of blanking them.** `groupId`/`agentId` are integers, so
  a draft **omits** the id/extension keys rather than sending `""` (an INVALID_TYPE the save rejects
  even on a disabled skill). A group draft ships `enabled: false` with `destination: "group"` and the
  target keys omitted, for the user to finish in the dashboard.
- **Save vs validate on unknown fields.** The create/update save **silently drops** an unknown or
  misspelled Expert-Mode key; only `/validate` (and the bundled validator) reject it — so run the
  validator to catch a typo the save would swallow.
- **Corrections.** Removed the phantom `upgradeSummary` field (it does not exist);
  `optimizeStreamingLatency` omitted on a write **resets to `0`**, not preserved, so always emit it;
  and there is **no hard `maxCallDuration` cap** — a value above 120 minutes draws a recommendation
  warning, not a save refusal (keep it ≤ 120).

## 2026-09-02

- **Setup: the plugin now asks for your API key.** Enabling the plugin prompts for the CloudTalk
  key (base64 of `API_KEY_ID:API_KEY_SECRET`); the input is masked and stored in your OS keychain
  instead of an exported shell variable. **Migration:** the `CLOUDTALK_MCP_KEY` environment
  variable is no longer read — paste the same value into the prompt (or keep your own
  `claude mcp add` server, which is unaffected). Leaving it empty keeps everything working offline.
- **Validator: an over-ceiling call duration now blocks instead of merely warning.** A
  `maxCallDuration` above 120 minutes exits non-zero, because the platform refuses that save
  outright.
- **Provider resolution fixed for more languages.** Plain two-letter language codes (Catalan,
  Estonian, Latvian, Lithuanian, …) now resolve to ElevenLabs as documented, so an agent in one of
  those languages no longer gets bogus "ElevenLabs settings ignored" / "model not offered" /
  "multilingual rejected" findings. Deepgram is picked only for the codes ElevenLabs lacks
  (`multi` and regional variants like `en-US`).
- **Wider connected-mode guidance:** list reads page (default 50, ceiling 200 — follow
  `pagination.next_page` before deciding something doesn't exist); the two agent ids and which
  tool takes which; a successful save can still return `error_codes`, and it returns a
  `dashboard_url` worth handing over; `search_calls` filters by the numeric agent id; creating a
  custom tool can attach it in the same call; `tone`/`verbosity` are now enum-checked at the MCP
  layer.
- **New example E10** — appointment booking with a `booking_confirmed` → `sendSms` confirmation,
  including which `{{appointment.*}}` variables exist before a booking and which only after.
  E4 gains a `toolCall` scenario and an `extractData` webhook; E9 gains a `## Known facts`
  variables section, a `customProperties` handover field, and a switched-off scenario.
- **Docs-sync CI check widened** to the LLM matrix, language sets, voice IDs, tone/verbosity, and
  scenario actions, so the validator's mirrored enums can no longer drift from the schema doc
  silently. CI additionally runs `pre-commit` over the whole repo and only builds `main` on push.
- **Corrections from a full re-read of the corpus.** The 120-minute call-duration ceiling is
  platform-wide, not connected-mode only; a malformed language code now falls back to Deepgram as
  the schema says instead of quietly landing on ElevenLabs; `secondaryLanguages` accepts every plain
  two-letter code, as the primary language already did; three or more `tone` labels draw a
  non-blocking advisory; `--json` gained an explicit `saveBlocking` flag; and the connected-mode
  guidance is corrected throughout — paging numbers per list family, what a non-admin key can
  actually read, `null` arguments being rejected rather than preserving, which writes return a
  `dashboard_url`, and which fields the MCP layer enforces.

## 2026-09-01

- Public fork of CloudTalk's internal plugin marketplace: Apache-2.0 license, public manifests
  and docs at [CloudTalk-io/marketplace](https://github.com/CloudTalk-io/marketplace).
- MCP-connected mode: the plugin bundles the CloudTalk MCP server (voice-agents profile), so
  with an API key Claude can read and operate your account — offline generation still works
  without one.
- New `simulate-conversation` skill: roleplay a caller persona against a config with an
  automated judge scoring the transcript.
- Identity fields (`tone`, `verbosity`) and the ElevenLabs expert-mode settings added to the
  schema, validator, and examples.
- Validator hardening: explicit `enabled` required on scenarios/guardrails/skills,
  direction-aware outbound-number contract, half-set transfer targets rejected, invented
  URLs/variables rejected, and stricter shape checks throughout.
