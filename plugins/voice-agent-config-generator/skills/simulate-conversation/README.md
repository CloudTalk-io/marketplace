# simulate-conversation — dry-run a voice agent before it takes calls

Give this skill a **Voice Agent v2 config** and it plays a phone call against it: one subagent acts
as the agent (strictly per the config) and as a caller persona, and a second, **blind** subagent
scores the resulting transcript. Output is a short chat block — verdict, six scores, failed gates,
gaps, awkward moments, and at most five **config-level** edits. Nothing is dialed and nothing is
saved, unless the user explicitly opts into the live lap.

Its sibling skill,
[`voice-agent-config-generator`](../voice-agent-config-generator/README.md), authors and validates
the config; this one asks whether the config actually behaves.

## How it is invoked

[`SKILL.md`](./SKILL.md) is the entry point — its `description` is the trigger, so a request like
"test my agent", "simulate a call", "how would this handle an angry caller", or "find gaps in this
config" loads it. It also runs naturally as a quality pass right after a config is generated.

It takes three inputs, all with defaults:

| Input | Accepted forms | Default |
|---|---|---|
| **Config** | a draft from the conversation · pasted JSON · connected: `cloudtalk_get_voice_agent` | the most recent draft |
| **Persona** | a named card from [`personas/`](./personas/) · auto-derived from the use case | the card that stresses the riskiest surface |
| **Depth** | one conversation · `thorough` = three personas in parallel | one conversation |

A structurally broken config simulates badly for the wrong reasons, so validate first:
`python3 ../voice-agent-config-generator/scripts/validate_config.py <config>`.

## Personas

One card per run — intent and style only, never scripted lines. The conversation itself happens in
the agent's configured `language`.

| Card | Stresses | Patience |
|---|---|---|
| [`cooperative-caller`](./personas/cooperative-caller.json) | the happy path end to end — does the designed flow hold at all? | high |
| [`impatient-caller`](./personas/impatient-caller.json) | brevity, pace, and transfer honesty under pressure | low |
| [`confused-caller`](./personas/confused-caller.json) | repair: repetition, read-backs, steering back on task | medium |
| [`edge-prober`](./personas/edge-prober.json) | scope limits, invented capabilities, mid-call changes | medium |
| [`wrong-fit-caller`](./personas/wrong-fit-caller.json) | graceful decline and routing when another line is needed | medium |

Each card carries a `goal_template` whose `<GOAL>` the runner fills from the config's use case, plus
an opening intent, follow-up intents, and success criteria. See
[`personas/README.md`](./personas/README.md).

## What the judge measures

The full rubric — anchors, gate table, and the strict-JSON output contract — is
[`rubric.md`](./rubric.md). In summary:

**Six scored dimensions, 1–5:** `verbosity_discipline` (turn length fits a phone voice and the
configured `verbosity`) · `natural_flow` (turns build on each other, no robotic repetition) ·
`register_tone` (matches the configured `tone`, one language throughout) · `question_discipline`
(one question per turn) · `helpfulness` (the caller's goal advanced honestly) · `ending_quality`
(the call ends through a configured path). A 5 needs quotable positive evidence; a clean but
unremarkable run is a 4.

**Seven correctness gates,** each `pass` / `fail` / `n/a`: `greeting_verbatim`,
`language_consistency`, `hangup_path`, `transfer_honesty`, `extract_data_coverage`,
`no_invented_capabilities`, `no_unresolved_variables`.

**Verdict rules:** any gate failure caps the verdict at `fail`, whatever the scores — as do two or
more dimensions at 1–2. All gates passing with some dimension ≤ 3 (or findings worth fixing) is
`pass_with_gaps`. `pass` means all gates pass, every dimension ≥ 4, and nothing material in `gaps`.

## Why two different models

The two subagents are deliberately asymmetric:

- **Simulator — small and fast.** Production voice agents run on small, low-latency models, so a
  small simulator is the honest approximation of how the config will really be interpreted. A
  stronger model quietly repairs prompt weaknesses a live agent would trip on, and the run comes
  back cleaner than reality.
- **Judge — the strongest available, and blind.** Grading depth is where the quality of the report
  comes from. It receives only the rubric, the config, and the transcript: never the persona card or
  any hint of what was being tested, so it grades the agent rather than the test.

**Model naming is environment-dependent.** Where the Claude model family is available this means
**haiku** for the simulator and **opus** for the judge. Elsewhere, keep the *design* and substitute:
the **smallest fast** model available for the simulator, the **strongest available** for the judge.
Never level them up or down to match each other — the asymmetry is the point.

## Limits

Simulation exercises conversational behavior, not the stack: real latency, voice quality,
provider-side turn-taking and barge-in, actual tool/webhook responses, and number routing are out of
reach. Two optimisms are built in — the simulator knows the whole config (so knowledge-base
fallbacks are under-exercised) and elapsed time is not modeled (so a too-tight `maxCallDuration`
simulates fine). The optional live test call (SKILL.md §6, connected mode, explicit opt-in only) is
what covers the rest.
