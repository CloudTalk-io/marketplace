---
name: simulate-conversation
description: >-
  Test a CloudTalk Voice Agent v2 config by simulating a phone conversation against it: a subagent
  plays the agent strictly per the config against a caller persona, then a blind judge scores the
  transcript and returns gaps, awkward moments, and concrete config-level fixes. Use whenever the
  user wants to test or preview a voice agent config — "test my agent", "simulate a call", "how
  would my agent handle an angry caller", "find gaps in this config", "run a simulated
  conversation" — and as a quality pass right after generating a config. Works on a conversation
  draft or pasted JSON; with the CloudTalk MCP connected it can also fetch a saved config and, on
  explicit user opt-in, place a real test call and judge that transcript.
license: Apache-2.0
---

# Simulate a conversation against a Voice Agent config

Dry-run a config before it takes real calls. One subagent plays **both sides** of a phone call — the
agent strictly per the config, the caller per a persona card — and a second, **blind** subagent
judges the transcript against `rubric.md`. Output: verdict, scores, failed gates, and ≤5
config-level edits. Nothing is dialed or saved; no MCP needed — except the optional live lap (§6).

## 1 · Inputs

| Input | Accepted forms | Default |
|---|---|---|
| **Config** | draft from this conversation · pasted JSON · connected: `cloudtalk_get_voice_agent` | the most recent draft in the conversation |
| **Persona** | a named card from `personas/` · auto-derived from the use case | auto-pick the most relevant single card |
| **Depth** | one conversation · `thorough` = 3 personas, always including `impatient-caller` | one conversation |

Persona auto-pick — choose the card that stresses this config's riskiest surface:

| Card | Stresses |
|---|---|
| `cooperative-caller` | the happy path, end to end — does the designed flow itself hold? |
| `impatient-caller` | brevity, pace, transfer honesty under pressure |
| `confused-caller` | repair: repetition, read-backs, steering back on task |
| `edge-prober` | scope limits, invented capabilities, mid-call changes |
| `wrong-fit-caller` | graceful decline + routing when the caller needs a different line |

Prepare the run:

- Fill the card's `goal_template` placeholder `<GOAL>` from the config's use case (for
  `wrong-fit-caller`: an adjacent need this config does **not** serve).
- Bind every `{{variable}}` the way the runtime would, so the run neither invents context nor fakes a
  defect: user-declared call-property keys, `{{contact.*}}` and `{{caller_number}}` → plausible sample
  values (live, these come from the trigger's `call_properties` or a matched CRM contact);
  `{{appointment.event_name}}` · `.service_description` · `.duration_minutes` → read straight off the
  `appointmentBooking` skill; every other `{{appointment.*}}` → empty until a booking succeeds in-call.
  Anything left over is unbound and renders as an empty gap, exactly like the runtime.
- A structurally broken config simulates badly for the wrong reasons — if the JSON hasn't been
  validated yet, run the sibling skill's validator first:
  `python3 ../voice-agent-config-generator/scripts/validate_config.py <config>` (relative to this
  skill's directory).

> **✓ Gate — before spawning:** full config JSON in hand · exactly one persona card per run, with
> `<GOAL>` filled · every `{{variable}}` bound (or deliberately left empty) per the rule above.

## 2 · Simulator subagent

Spawn a fresh subagent per persona via the Agent/Task tool — never a raw API call — and run it on a
**small, fast model (haiku)**: production voice agents run on small low-latency models, so a haiku
simulator is the honest approximation of how the config will actually be interpreted; a stronger
model papers over prompt weaknesses a real agent would trip on. **Model names depend on the
environment** — haiku where the Claude family is available, otherwise the **smallest fast** model on
offer; keep the small-simulator/strong-judge asymmetry whatever the names are. Its prompt is exactly three parts,
nothing else (no rubric, no expectations, no commentary): **the config JSON** (plus the variable
bindings you chose, when the config uses any), **the one persona card**, and **this protocol,
verbatim**:

```text
Simulate one phone call. Output ONLY the transcript.

ROLES — you play both, strictly separated: the agent knows only the config; the caller knows only
the persona card plus what has been said aloud. Neither side ever uses the other's knowledge.

AGENT — act strictly per the config:
- startSpeakingFirst true → open by speaking `greeting` verbatim, word for word. Empty greeting:
  inbound falls back to a short generic opener in the agent's language, as the platform does; outbound
  stays silent — let the caller open and the dead air show, never paper over it.
  startSpeakingFirst false → stay silent until the caller speaks.
- Every agent word in the configured `language`. Switch only to a configured secondary language,
  and only to follow the caller.
- One question per turn. Follow the goalPrompt task flow and its decision criteria.
- A disabled skill (`enabled: false`) grants nothing. A live handoff exists only via an enabled
  `transferToHuman` rule, or `answerQuestions` enabled with `action: "transferToHuman"` and a real
  `transferConfig` — no scenario action can transfer. Otherwise offer a callback, never a handoff.
  When the transfer skill carries `confirmationRequired: true`, mark the ask itself with
  `[transfer-offer: <rule>]` and emit `[transfer: …]` only after the caller agrees.
- Ask only what `goalPrompt` and the custom skills instruct. **extractData grants no asking** — it runs
  post-call over the transcript, so never ask for a property just because it is listed: if the prompt
  never asks, the value is never said, and that silence is the finding.
- `[collect: <property>=<value>]` marks a value the agent actually heard that maps to an enabled
  extractData property — read back where the goalPrompt itself requires a read-back; re-emit if the
  caller corrects it.
- Enabled scenario matched → speak its `reply` verbatim (empty `reply` = say nothing extra), then honor
  its `action` (`toolCall`/`sendSms`/`hangup`); a `booking_confirmed` scenario fires off a successful
  in-call booking, not off its `when`. Enabled guardrail matched → speak its `reply`. Disabled ones
  never fire.
- Never invent a capability the config doesn't grant: no SMS without a sendSms scenario, no booking
  without enabled appointmentBooking, no transfer without an enabled rule or transferConfig, no
  live lookup without a toolCall scenario, no email, no keypad/IVR.
- A `{{variable}}` with no supplied value renders as an empty string — speak the line with the gap.

MARKERS — actions are bracket markers on their own line, never prose claims of having acted (words
say things; markers do things):
[transfer: <rule/destination>] · [transfer-offer: <rule>] · [hangup: <scenario>] ·
[sendSms: <scenario>] · [collect: <property>=<value>]

CALLER — act per the persona card:
- Pursue the filled goal with the card's style, patience, opening intent, and follow-up intents.
- Speak the agent's language unless the card says otherwise.
- Never help the agent: no volunteering what wasn't asked, no steering it back on task, no
  excusing its mistakes.
- End your FINAL caller line with [GOAL_MET] or [GIVING_UP].

STOP — after a [transfer:] or [hangup:] marker; after the caller's tagged final line (the agent
may still close per its config); or at the hard cap of 10 caller turns, even mid-task.

TRANSCRIPT — alternating lines `CALLER: <words>` / `AGENT: <words>` plus marker lines; the AGENT
line opens when `startSpeakingFirst` is true, the CALLER line otherwise. No headers, no analysis,
no summary.
```

## 3 · Judge subagent — blind

Spawn a second fresh subagent on the **strongest available model (opus)** — the judge's depth is
where quality comes from, while the simulator's smallness is where fidelity comes from. Again the
name is environment-dependent: opus where the Claude family is available, otherwise the
**strongest available** model — never the same tier as the simulator. Its prompt is
exactly three parts, in this order: **the full text of `rubric.md`** · **the config JSON** · **the
transcript**. Never pass the persona card, the simulator prompt, or any hint of what you expect — a
judge that knows what was tested grades the test, not the agent.

It returns STRICT JSON (field-level contract and anchors live in `rubric.md`):

- `verdict`: `pass` | `pass_with_gaps` | `fail` — **any failed gate caps it at `fail`**, whatever
  the scores.
- `scores`: the six rubric dimensions, 1–5.
- `correctness_gates`: the seven gates, `pass` | `fail` | `n/a`.
- `gaps`: config-level holes the conversation exposed.
- `awkward_moments`: `{turn, quote (verbatim, original language), why (English)}`.
- `edit_suggestions`: ≤5 × `{path, change, because}` — **config fields only** (`goalPrompt`,
  `scenarios[1].reply`, `skills.transferToHuman.enabled`, …), never the harness, the simulation, or
  the platform.

Output not parseable as that JSON → re-spawn once with the same three parts; never repair or fill
it in yourself.

## 4 · Report — fixed chat block

Render exactly this; omit a section only when it is empty. Never dump the transcript unasked.

```text
**Simulation:** <persona-id> vs <agentName> — **<verdict>**
**Scores:** verbosity <n> · flow <n> · tone <n> · questions <n> · helpfulness <n> · ending <n>
**Gates failed:** <gate> — <one-line evidence>          ← line absent when all pass
**Gaps:**
- <one line each>
**Awkward moments:**
- turn <n> — "<verbatim quote>" — <why>
**Suggested edits:**
| # | Config path | Change | Because |
|---|---|---|---|
**Transcript:** <n> caller turns, ended via <path> — available on request.
```

Show the full transcript verbatim whenever the user asks for it.

## 5 · Thorough mode

Three personas — `impatient-caller` always, plus the two most relevant others — as **three
independent simulator+judge pairs**: spawn the three simulators in parallel (one message, three
spawns), then the three judges in parallel. No shared state between pairs. Render one compact §4
block per persona, then a short synthesis paragraph: **recurring findings first** (a gap two judges
hit is the headline), then one line per persona.

## 6 · Live test call — connected mode, explicit user opt-in only

Simulation predicts; a live lap measures the real stack. Offer it only when the CloudTalk MCP is
connected. **Never auto-place a call.**

1. **Saved config only.** The live call runs what is SAVED on the agent, not your draft — fetch with
   `cloudtalk_get_voice_agent` and confirm it matches the config under test before anything dials.
2. **Outbound agent:** `cloudtalk_trigger_aiva_call` places a **real phone call** — say so plainly.
   It is confirm-gated, and the destination is a number the user provides as their own phone.
   **Never suggest, guess, or reuse a customer's number.**
3. **Inbound agent:** trigger nothing — tell the user to call the agent's assigned number from
   their own phone.
4. **Judge the real call:** locate it with `cloudtalk_search_calls`, fetch the transcript with
   `cloudtalk_get_call_transcript`, and run the **same §3 judge** on it. Real transcripts carry no
   bracket markers — the judge scores from the spoken lines and how the call actually ended.

## 7 · What this cannot verify

Simulation exercises the config's conversational behavior, not the stack: real latency and voice
quality, provider-side turn-taking and barge-in, actual tool/webhook responses (a `toolCall` result
here is imagined), and number routing are out of reach. The §6 live lap — or a test call from the
dashboard — is what covers those.

Two optimisms are built into the roleplay itself: the simulator knows the whole config, so it answers
questions a live agent without a linked knowledge base could not (`answerQuestions` fallbacks are
under-exercised — judge them skeptically), and elapsed time is not modeled, so a too-tight
`maxCallDuration` that would truncate a real call simulates fine.
