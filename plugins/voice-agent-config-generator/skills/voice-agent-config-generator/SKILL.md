---
name: voice-agent-config-generator
description: >-
  Generate, fix, or validate a CloudTalk Voice Agent v2 "Expert Mode" configuration — offline as the JSON
  you paste into the dashboard's Advanced/code tab, or connected through the CloudTalk MCP, where it reads
  and writes the agent directly against your real account (numbers, knowledge bases, tools, transfer
  targets; every write needs your confirmation). Use whenever the user wants to create or edit ANY inbound
  or outbound AI voice/phone agent for CloudTalk — any use case or industry (reception, qualification,
  support, booking, surveys, reminders, notifications, lead capture, … — these are just examples, not the
  limit) — or asks for a voiceAgent config, a goalPrompt/greeting/scenarios/skills, or pastes an existing
  config to review, edit, or reuse. Produces a behaviorally-sound, save-ready config that reuses the
  agent's existing setup, and runs a structural + behavioral validator first.
license: Apache-2.0
---

# Voice Agent v2 (Expert Mode) config generator

Turn a use case — plus a few facts only the user can supply — into a **save-ready Voice Agent v2** JSON
config.

**Two modes, one contract.** If the CloudTalk MCP tools (`cloudtalk_*`) are available, you are
**connected**: read the agent with `cloudtalk_get_voice_agent` instead of asking for a paste, resolve
account IDs with the `list_*` reads, and save through the confirm-gated write tools
(`mcp-tools.md`, `generator-contract.md` *Connected mode*). Otherwise you are **offline**: the user pastes
their config, you return JSON for the dashboard's Advanced/code tab, and the save is an edit (`PUT`).
Either way the agent the user made in the UI is usually a **blank shell to unlock Expert Mode**: generate
the config **fresh** for the use case and carry over **only** its environment/wiring (the outbound number
+ any real IDs) — never its prompt, skills, or behavior. The output must be **behaviorally sound, not just
schema-valid**.

## Two kinds of input — treat them oppositely

| | What you do | Covers |
|---|---|---|
| **Design** | **Author it.** Don't interrogate; a complete request needs no interview. | tone, task flow, guardrails, scenarios, the `extractData` proposal, numeric/voice tuning, provider/LLM |
| **Ground truth** | **Obtain it — never invent, default, or copy from an example.** Connected: **fetch it** (numbers, transfer targets, KBs, tools, the agent's own document). Offline: ask. | the business's **real name** (spoken in `greeting`, always asked, never fetched), **real IDs** for any referenced feature explicitly requested (transfer target, KB, calendar, …), and an **outbound** agent's own number wiring |

If a ground-truth fact is missing and no read can supply it, **ask in one short batch and wait** before
emitting JSON. Never coin a brand name from the use case ("socks" → "Sock Shop"). **If you'd reach for a
placeholder or "stand-in," that is the signal to fetch or ask instead.**

## What you can build

Any inbound/outbound agent the platform supports — the worked examples are **illustrative, not a menu**
(exact shapes in `schema.md` §6–§7). The single LLM prompt is the lever: **no matching built-in skill →
express it in `goalPrompt` + a `custom` skill.** Only the genuinely unsupported is off the table — for it,
say so and offer the nearest supported path, never fake it:

- "hang up after 30 s of silence" → a **voicemail / unresponsive-caller `hangup` scenario** (the runtime
  can't measure silence duration).
- "press 1 for sales" IVR navigation → route the menu **upstream in the Call Flow Designer** (no DTMF).

## Bundled references — load on demand

| File | Read it for |
|---|---|
| `generator-contract.md` | **Start here.** Emit policy: per-tier rules, the reference decision tree (reuse / fetch / substitute / ask / omit), the connected-mode write contract, output shape. |
| `schema.md` | Field shapes, enums, dependency rules (§3), provider/LLM auto-selection (§5), `elevenLabsSettings` (§10), `tone`/`verbosity` (§11). |
| `fields.json` | Machine spine — every field's `authoring` tier. The validator keys off it. |
| `behavioral-guidance.md` | What makes a config *perform*: prompt architecture (§2), hangup (§4), language (§5), numeric settings (§7a-bis), overriding platform choices (§9), the §8 self-check. |
| `referenced-resources.md` | **Only when a referenced feature is requested** — what each resource is, how to wire its ID, connected and Dashboard paths. |
| `mcp-tools.md` | Connected mode only — the tool surface, write-safety rules, and what has no tool yet (with workarounds). |
| `variables.md` | Whenever a `{{variable}}` is in play — what resolves, when, and the silent empty-string trap. |
| `examples/` (E1–E10) | Few-shots. **E1** (auto-ElevenLabs, switched-off transfer) and **E6** (auto-Deepgram) are the save-ready archetypes; **E3** is the explicit-Call-Flow exception; **E4** adds a `toolCall` scenario and an `extractData` webhook; **E7** adds `takeMessage`; **E8** shows `tone`/`verbosity` + ElevenLabs tuning; **E9** scaffolds a group transfer as a disabled draft (`destination: "group"`, id/extension omitted — completed in the dashboard) + `sendSms`; **E10** is appointment booking + a `booking_confirmed` SMS. Only **E2** exits `1`, deliberately (the both-directions failover gate). |

## Workflow — follow in order

### 1 · Scope & intake — understand the job before building

- **State the job** in one line: who calls (or is called), and the outcome.
- **Reason about what *this* agent needs to do it well** — don't just tick a static list. An order-taker
  needs the fields to capture + read-back; a booking agent needs a real calendar (or a "log it, a human
  books" fallback); a support agent may need a KB; an outbound agent needs callee context + `{{variables}}`.
- **Author the Design inputs. Collect the Ground-truth inputs.** Connected, collect by reading: the agent's
  current document, the number list, the group/agent lists. Ask the user about a gap **only if** it is
  (a) something only they know **and** (b) its absence would force a fabrication or a materially worse
  agent. Otherwise pick a sensible default and **note the assumption** in one line. Batch all questions
  into one message — never drip-feed, never interrogate.
- **Edit-first shortcut.** Connected: `cloudtalk_get_voice_agent` **is** the paste — fetch it, reuse its
  real number and IDs, and still ask the one human question: *"What's the business's real name (callers
  hear it)?"* Offline: *"What's the business's real name? If you paste your agent's current config I'll
  reuse your real number and any IDs it already has — otherwise I'll need a real owned outbound number ID
  (or you set it in the dashboard) before it can save."*

> **✓ Gate — before you generate, you have (or have consciously deferred with a noted assumption):**
> - [ ] direction (`inbound`/`outbound`) and the agent's core goal
> - [ ] the **real business name** — asked, not coined from the use case
> - [ ] the **outbound number** completed: `defaultOutboundNumberId` defaults to `1` (Automatic, as the
>       dashboard seeds it) — complete it with a real owned `failoverOutboundNumberId` in both directions, or
>       set a real owned `defaultOutboundNumberId` directly (reuse the agent's real ID fetched or pasted, pick
>       one from `cloudtalk_list_numbers`, or ask). Never `2`, never fabricated, never `null`, never a bare
>       `1`; offline, the user completes the failover/number in the dashboard
> - [ ] primary `language` (+ any `secondaryLanguages`)
> - [ ] the data to collect **and** every use-case-specific need you identified (KB, calendar, transfer
>       target, callee variables) — each one present, or omitted on purpose with the user told
> - [ ] real IDs for any **explicitly requested** referenced feature — fetched, supplied, or else a
>       zero-touch substitute, a switched-off skill (transfers), or omit-and-instruct

### 2 · Resolve provider & LLM in your head — `schema.md` §5

- plain code (`en`, `de`, …) → **ElevenLabs** · Deepgram-exclusive (`en-US`, `pt-BR`, …) → **Deepgram** ·
  `secondaryLanguages` → **ElevenLabs**, and **pin `providerOverride: "elevenlabs"`**.
- trivial ElevenLabs agent auto-falls to a lightweight model → set `llmOverride: "anthropic - claude-haiku-4-5"`
  if it does real work (transfers, careful data capture). Overriding deliberately? `behavioral-guidance.md` §9.
- emit `elevenLabsSettings` **only** when the resolved provider is ElevenLabs.

### 3 · Stay self-contained by default — `generator-contract.md`

Emit only `generate` fields + the outbound number → nothing else to wire. Handling for common asks:

- transfer / "talk to a human" → wire a **direct** rule (`destination: "agent"`/`"group"`) with
  `enabled: true` only when you have the target's **id + extension**; else ship it `enabled: false` as a
  draft — scaffold the group (`destination: "group"`, id/extension **omitted**) or `rules: []` (step 6)
- knowledge → facts in `goalPrompt` or a custom skill; leave `knowledgeBaseIds` empty (connected: create a
  KB only on explicit request — its content is frozen after creation)
- end the call → a `hangup` scenario (the **only** way to grant `end_call`)
- outbound number → defaults to `1` (Automatic, as the dashboard seeds it) + a real owned
  `failoverOutboundNumberId` in both directions, or a real owned `defaultOutboundNumberId` set directly
  (reuse/fetch/ask); never guess, never `2`, never `null`, never a bare `1`

### 4 · Author `goalPrompt` — the five components — `behavioral-guidance.md` §2.1

identity · style guardrails · response guidelines · task flow (**one question per turn**, explicit decision
criteria) · ending. Numbered workflow, a `# Guardrails` heading, short action-based sentences. Custom
skills: **2–4** recommended, up to 6 tolerated (the validator warns above 6), each a real capability.
**All prose in the agent's `language`.**

> **✓ Gate:** all 5 components present · one question per turn · greeting not duplicated inside `goalPrompt`.

### 5 · Skills & scenarios — behavioral — `behavioral-guidance.md` §3–4

- **Always** include hangup scenarios: normal completion + prolonged silence (+ voicemail if outbound).
- `extractData` is post-call & passive — to *collect* a value, also instruct the prompt to ask for it and
  read it back. Each property atomic.
- `takeMessage` inbound-only, and emit it only deliberately: present-but-disabled renders an explicit
  "can't take messages". Don't auto-transfer `answerQuestions` without a KB/skills to try first.
- Every `reply` = the **literal sentence spoken** (no `Say:"…"`, no parentheticals, no `"."`/`"Nothing"`).
- **Every scenario and every skill object carries an explicit `enabled`** — see the guardrail below. Never
  emit the `guardrails` array; keep it empty (`[]`).

> **✓ Gate:** ≥1 hangup scenario · explicit `enabled` on every scenario and skill object · `guardrails: []` · every `reply` **and** every scenario `when` in the agent's `language`.

### 6 · Referenced features — only on explicit request — `referenced-resources.md`

**Never emit a placeholder/sentinel ID, and never guess one.** Resolve each reference, in order: (a) **reuse
a real ID the agent already has**; (b) **fetch it** — connected, the `list_*` reads answer most lookups
(`generator-contract.md` *Connected mode* — note `cloudtalk_list_groups` gives no extension; that half still
comes from the user); (c) a **zero-touch substitute** where one exists (knowledge → prompt or custom skill);
(d) **ask for the real ID** (explain why, and say what ships meanwhile); (e) **omit + tell the user how to
add it** (a calendar that must be connected first stays Dashboard-only even when connected).
*"Ship a working config first, then offer the upgrade"* applies **here** (optional features) — **not** to
ground truth (step 1). A genuine *cross-account* paste strips `toolCall`/`sendSms`; your own agent doesn't.

**Transfers have no zero-touch substitute** — reaching a human needs a real target. A **live**
`agent`/`group` rule needs **both** the id and the extension. When you don't have them, ship
`transferToHuman` `enabled: false` as a **draft**: the default **scaffolds the group** (a rule with
`destination: "group"` and `groupId`/`groupExtension` **omitted**), or `rules: []` when no group is in mind.
OMIT the id/extension keys on a draft — never blank an integer id to `""` (an INVALID_TYPE the save rejects
even when the skill is off). Keep the prompt promising a **callback** rather than a handoff, and tell the
user in plain terms to *finish setting up the transfer to their team in the dashboard* (the skill shows
*"Requires configuration"*), then switch it on. **`destination: "call_flow"` only when the user asks for it or says the agent runs inside a
Call Flow** (it hangs up and the flow continues; for a standalone agent it does nothing). A wrong
id/extension is validated **nowhere** and fails only mid-call — the AI resumes where advanced transfer is
enabled, but on a cold fallback the caller is dropped.

### 7 · Set numeric fields deliberately — `behavioral-guidance.md` §7a-bis, §4.4

`temperature` 0.5 baseline (~0.1–0.3 for highly structured flows) · `optimizeStreamingLatency` 2 (**never 4** — disables the TTS normalizer) ·
`stability` 0.3 / `similarity` 0.7 baselines · `maxCallDuration` a **generous** hard cap that truncates
the call, ≤120 (never omit — the dashboard fills 30): ~20–30 min inbound, ~10–15 min outbound ·
`dialTime` ≤90 if set at all. Overriding provider/LLM/tuning defaults → `behavioral-guidance.md` §9.

### 8 · Validate — fix every ERROR

```bash
python3 scripts/validate_config.py path/to/draft.json
```

(Run from this skill's directory, or pass full paths — the script resolves `fields.json` relative to
itself.) ERRORs cause the save to fail — fix all. Review WARNINGs for quality; save-blocking ones exit 1.
Then run the `behavioral-guidance.md` §8 self-check once more.

### 9 · Critique pass — non-trivial configs only

Multilingual / any transfer / data capture / appointment booking / a referenced resource → get an
**independent** critique first. **Preferred: run the `simulate-conversation` skill** — a persona subagent
plays a caller against the config and a blind judge reports gaps and awkward moments. Else a fresh-context
subagent, else a deliberate adversarial self-review (read it as a skeptic). Lenses: language consistency
**incl. every `when`**; greeting realism; **prose coherence** (re-read every prose field in the target
language); scenario coverage; `extractData` justification; schema + reuse/nothing-to-wire. Reconcile; note
any finding you deliberately override.

### 10 · Return — `generator-contract.md` output shape

**Connected:** validate locally, then write via `cloudtalk_update_voice_agent` (or `create`) — present the
confirmation preview, wait for the user, and after the confirmed save report the agent's **name + id**,
what changed, what remains, and how to verify (a test call + `cloudtalk_get_call_transcript`). The write's
structured result replaces the paste-and-see smoke test.

**Offline:**
1. **The importable JSON** — pure, schema-only, save-ready (no comments, no `_requiredResources`, no
   placeholder IDs, no forbidden fields), reusing the agent's existing setup.
2. **One-line status** — `✅ Ready to save — nothing else to wire`, or
   `⚠️ Saves as-is, but <feature> needs <N> setup step(s)`. A config carrying Automatic (`1`) with no real
   `failoverOutboundNumberId` is **not** ready — it will `400` — so flag the number as a setup step until a
   real owned id (default or failover) is in place.
3. **Setup checklist** — only when step 2 flags something (keep it rare so it gets read).
4. **`extractData` properties** — each with a one-line *why useful*, open to edit (never embed silently).
5. **Save smoke-test** — save once to confirm it sticks; a *"Failed to update VoiceAgent"* error means a
   referenced resource isn't provisioned (fix the reference, don't retry — `referenced-resources.md`).

## Non-negotiable guardrails

- **Never ask the user to paste their CloudTalk API key into the chat.** The key is supplied through the
  plugin's `userConfig` prompt (masked) and stored in the OS keychain — never in a chat message or a
  settings file. If the MCP isn't connected, direct the user to that prompt (or their own
  `claude mcp add` server); don't collect the key here (repo README).
- **Inbound** ⇒ `startSpeakingFirst: true` **and** a concrete `greeting`. There is no `firstMessage` field.
- **≥1 `hangup` scenario**, or the agent literally cannot end a call (the validator blocks the handoff).
- **Never emit the `guardrails` array — keep it empty (`[]`).** It is accepted and stored but **inert at
  runtime**: the API has no runtime `enabled` for a guardrail, so every stored one decodes to disabled and
  is silently skipped. Put always-on rules in the `goalPrompt` `## Guardrails` prose section instead.
- **Explicit `enabled` on every scenario and every skill object you emit.** Nothing defaults it: a missing
  `enabled` fails the import, and in a stored config it silently disables that unit. (`enabled: false` is a
  legal, useful shape — a skill shipped switched-off for the user to finish in the dashboard.)
- **Never emit `forbidden` fields** — computed/response-only or system-managed (full list in
  `generator-contract.md`: `provider`, `llm`, `version`/`minorVersion`/`id`/timestamps, `companyId`,
  `presetType`, `status`, `hasOverrides`, …).
- **Connected writes are round-trips.** Never synthesize an update payload from the conversation:
  `cloudtalk_get_voice_agent` → modify → send the **whole document** back. Carry `knowledgeBaseIds`
  (omitting it unlinks every KB) and `elevenLabsSettings` (present replaces wholesale) forward. Writes are
  confirm-gated (one no-op exception: an assign/unassign that changes nothing): **present the preview and
  wait — never treat `confirmation_required` as an error, never confirm on the user's behalf.**
- **Outbound number — complete it; the FE-faithful path is Automatic (`1`) + a real owned failover.**
  `defaultOutboundNumberId` **defaults to `1` (Automatic), exactly as the dashboard seeds it.** With `1`,
  `failoverOutboundNumberId` is **required in BOTH directions** and must be a real owned ID — the save `400`s
  without it and nothing self-heals (never `null`); reuse the agent's failover (fetched or pasted), fetch one
  (`cloudtalk_list_numbers`), or the user completes it in the dashboard. Setting a real owned
  `defaultOutboundNumberId` directly is the alternative. **Never guess, never `2`, never copy a number from an
  example; do not hand over a bare `1` (a config that will 400).**
- **Never invent a company resource ID, and never leave a placeholder ID in the JSON** — fetch it, reuse a
  real ID, substitute, ship the skill switched-off, or omit-and-instruct. **A transfer target is the
  sharpest case:** a **live** `agent`/`group` rule needs the id **and** the extension, nothing validates
  either, and a wrong one fails only mid-call — so a live target comes from a read or the user, while
  otherwise the skill ships as a **disabled draft**: a scaffolded group (`destination: "group"`, id/extension
  **omitted**), or `rules: []`. `agentId`/`groupId` are integers — **OMIT them on a draft; never blank them
  to `""`** (an empty string is an INVALID_TYPE the save rejects even on a disabled skill).
- **Never invent a URL or an *undeclared* `{{variable}}`** (`variables.md` — an unknown `{{placeholder}}`
  renders as an empty string, silently). Any URL (in a `sendSms` message, `greeting`, or `goalPrompt`) must
  be **user-supplied and copied verbatim**; there is **no booking/calendar-link variable**. To "text the
  booking link": use `triggerType: "booking_confirmed"` + `sendSms` with `{{appointment.*}}`, or a static
  user-provided URL (`generator-contract.md`).
- **All agent-`language` text** — `greeting`, every `reply`, `goalPrompt`, custom skills, **and every
  scenario/guardrail `when`** — in the agent's `language`.
