# voice-agent-config-generator (plugin)

The CloudTalk voice-agent plugin for Claude, distributed via the `cloudtalk` plugin marketplace.
It helps customers and partners design, validate, and test **CloudTalk AI voice agents**, and it
bundles the CloudTalk MCP server so Claude can also operate your account when you connect an API
key (see the [repo README](../../README.md) for install and connection steps — everything also
works offline without a key).

## Skills

| Skill | What it does |
|---|---|
| [`voice-agent-config-generator`](./skills/voice-agent-config-generator/README.md) | Generate, fix, and validate **Voice Agent v2 (Expert Mode)** JSON configs — the payload pasted into the dashboard's Advanced/code tab — for any inbound/outbound use case. Runs a structural + behavioral validator before handing a config back. Works offline, or reads/writes your real account through the CloudTalk MCP when connected. |
| [`simulate-conversation`](./skills/simulate-conversation/README.md) | Roleplay a caller persona against a config — turn-by-turn, in the agent's language — and score the transcript with an automated judge, so you can test an agent before it takes real calls. |

## Try it

After installing, just describe what you want in plain language — no special syntax. A few first
prompts to try:

- **Build an agent.** *"Build me an inbound receptionist for a dental clinic that answers common
  questions and books appointments."* → Claude authors a validated, save-ready Voice Agent v2 config,
  runs the validator, and hands back the JSON to paste into the dashboard's Expert Mode (or, connected,
  saves it to your account after you confirm) — with a one-line status and any setup steps left.
- **Fix or validate a config.** *"Here's my current agent config — check it and fix anything that won't
  save."* (paste the JSON) → Claude validates the structure and behavior, explains what it changed, and
  returns a corrected config.
- **Test before it goes live.** *"Test this agent against an impatient caller who keeps interrupting."*
  → the `simulate-conversation` skill roleplays that caller against your config and a judge scores the
  transcript, flagging gaps and awkward moments.

Connected to your CloudTalk account (optional), the same prompts can read your real numbers, knowledge
bases, and agents and save changes for you — every account write asks you to confirm first.

## Contents

- `.claude-plugin/plugin.json` — plugin manifest: the bundled CloudTalk MCP server plus the
  `userConfig` entry Claude Code prompts for when the plugin is enabled (the API key, stored as a
  sensitive value and interpolated into the server's `Authorization` header). Leave it empty to
  stay offline.
- `skills/voice-agent-config-generator/` — `SKILL.md` (entry/router) plus bundled reference
  lenses (`schema.md`, `behavioral-guidance.md`, `generator-contract.md`,
  `referenced-resources.md`, `mcp-tools.md`, `variables.md`, `fields.json`), worked `examples/`,
  and the validator under `scripts/`.
- `skills/simulate-conversation/` — the caller-persona simulator and judge: `SKILL.md` (the run
  protocol), `rubric.md` (the judge's dimensions, gates, and output contract), `personas/` (the
  caller cards), and [its README](./skills/simulate-conversation/README.md).
