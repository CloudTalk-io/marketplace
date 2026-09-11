# Voice Agent v2 — generator contract

> **Audience:** the config-generation skill (LLM). **This doc owns the *emit* mechanics**: per-tier
> policy, intent-gating, the reference decision tree (reuse / fetch / substitute / ask / omit), and the
> **connected-mode write contract**. It does **not** restate field shapes ([`schema.md`](./schema.md)),
> quality rules ([`behavioral-guidance.md`](./behavioral-guidance.md)), or the MCP tool surface
> ([`mcp-tools.md`](./mcp-tools.md)) — a generated config must satisfy all of them.

## Mission

The user reaches Expert Mode by first creating an agent in the dashboard UI — but **that is usually just
the prerequisite to unlock the code tab, not a sign they have a meaningful agent to preserve.** Most of the
time the UI agent is a near-empty **shell**, and the user expects you to **generate the config fresh** for
their use case. So treat this as **fresh authoring** (your normal job) — **don't preserve or extend the
shell's prompt, skills, scenarios, or behavior** unless the user explicitly asks. The **one** thing you
carry over from the existing agent is its **environment/wiring**: the outbound number (`defaultOutboundNumberId`
+ `failoverOutboundNumberId`) it was auto-assigned, plus any real company IDs it already has. The result
**replaces** the shell's config (the save is an edit, not a create), reuses that wiring so it saves with
**nothing else to wire**, and is *behaviorally* sound. Stay self-contained unless the user explicitly asks
for a feature that requires a company resource.

> Offline, the JSON path is always an **edit of an existing agent** — and since that agent is usually a
> shell, think "fresh config + carry over the wiring," not "preserve what's there." The same reasoning
> holds for an update in **connected mode**, where creating an agent outright is available too
> (*Connected mode* below).

## Step 0 — resolve provider & LLM in your head first

**Decide `language` before you resolve anything from it.** When the user names the agent's language, or
states a caller-language requirement, honour it. When they do neither, default `language` to the language
the user is writing in during setup, resolved to a supported agent code (`schema.md` §4.3); provider
auto-selection then follows from that code by the §5 rules below. Treat it as an overridable default: tell
the user in half a sentence that you set it to that language and will switch on request, one word from
them. If the setup conversation is in a language no supported agent code covers, fall back to a supported
one and say which, so they can redirect. This is a default, not a new field or enum, and it never overrides
an explicit language choice or a stated caller-language need.

Provider and LLM are **computed server-side** from `language`/overrides (`schema.md` §5). Before
writing anything else, determine the resolved provider from the language so your other choices are
consistent:

- plain language (`en`, `de`, …) → **ElevenLabs**; Deepgram-exclusive code (`en-US`, `pt-BR`, …) →
  **Deepgram**; `secondaryLanguages` → **ElevenLabs** — and when you set `secondaryLanguages`, also pin
  `providerOverride: "elevenlabs"` (multilingual must be ElevenLabs; guards against a stored Deepgram
  provider rejecting the save).
- **Multilingual has two mechanisms — don't conflate them.** Default to **ElevenLabs via
  `secondaryLanguages`**. **Deepgram `multi`** (Deepgram-only, switches its listen model to `nova-3`) is
  **explicit-only**: emit `language: "multi"` with `providerOverride: "deepgram"` **only when the user
  asks for Deepgram multilingual**, never auto-routed. Deepgram + `secondaryLanguages` is rejected at save
  (schema §4.3/§5).
- A *trivial* ElevenLabs agent auto-falls to lightweight **Qwen**. If the agent does real work
  (transfers, careful data capture) but is small, set `llmOverride: "anthropic - claude-haiku-4-5"`
  (behavioral §7b).
- Only emit `elevenLabsSettings` when the resolved provider is ElevenLabs.

## Step 0.5 — carry over the shell's wiring (only)

The agent you're editing is usually a blank shell, so the **only** thing worth taking from its current
config (shown in the code tab) is its environment/company-specific **wiring** — not its prompt, skills, or
scenarios. **In connected mode there is nothing to ask for:** `cloudtalk_get_voice_agent` returns the whole
document, which is both the wiring source and the mandatory base for the update (*Connected mode* below).
Offline, **offer to take it:** *"If you paste the config your editor currently shows, I'll keep your
working setup, including your real outbound number — otherwise I'll need a real owned number ID for it (or
you set it in the dashboard) before it can save."* From whatever the user gives you,
**harvest the real values worth reusing** and bake them in verbatim:

- the outbound number pair (`defaultOutboundNumberId` + `failoverOutboundNumberId`) — **whenever the paste
  has them**, because an Expert-Mode save stores exactly what you send;
- any already-wired IDs that fit the new use case — `knowledgeBaseIds`, transfer `agentId`/`agentExtension`
  or `groupId`/`groupExtension`, `appointmentBooking.integrationId`/`calendarId`, a scenario
  `toolReferenceId`, an SMS `senderNumber`.

**Don't get sidetracked by an irrelevant paste.** The pasted config is a *source of reusable IDs*, not a
base to mutate. If it's for a different use case, ignore its prompt, skills, scenarios, and behavior
wholesale — take only the IDs that fit what's being asked for and generate everything else fresh.

**Complete the outbound number.** `defaultOutboundNumberId` **defaults to `1` (Automatic), exactly as the
dashboard seeds it** — but the config save stores exactly what you send and does **not** auto-pick a number,
so a bare `1` is not save-ready: it needs a real owned `failoverOutboundNumberId` in **both directions** to
complete it (the save `400`s without it and nothing self-heals). Completing that failover is the FE-faithful
path — connected, read it from `cloudtalk_list_numbers`; offline, the user completes it in the dashboard, or
you ask, e.g. *"what outbound number should this agent use? — a real one your company owns, or leave it on
Automatic and I'll need a real failover number ID."* Setting a real owned `defaultOutboundNumberId` directly
is the alternative. **Never guess `2`, never send `failoverOutboundNumberId: null`, and never hand over a
config that will 400.**

## Per-tier emit policy

| Tier | Policy |
|---|---|
| `generate` | Author it. This is the bulk of every config. |
| `environment` | **Complete the outbound number — the FE-faithful path is Automatic (`1`) + a real owned failover.** `defaultOutboundNumberId` **defaults to `1` (Automatic), exactly as the dashboard seeds it** and cannot be omitted. With `1`, `failoverOutboundNumberId` is **required in BOTH directions** and must be a real owned id — the save `400`s without it, nothing self-heals, and `null` is never valid; reuse the agent's failover when editing, fetch it (`cloudtalk_list_numbers`), or the user completes it in the dashboard. Setting a real owned `defaultOutboundNumberId` directly is the alternative (omit the failover key only then). Only `1` is magic — **every other value, including `2`, is a literal phone-number ID the company must own** (there is no "Random"), and an unowned one is a hard `400` by name at save. |
| `reference` | **Off by default.** Emit only on explicit user intent, and then follow the **reference decision tree** below: substitute, ask for the real ID, or omit + instruct. **Never put a placeholder/sentinel ID in the body.** |
| `forbidden` | Never emit. Two groups: (a) computed/response-only — `provider`, `llm`, `version`/`minorVersion`, `id`/`voiceAgentId`/timestamps, the server-emitted diagnostics `warnings`/`errorCodes`/`upgradeAvailable`, `companyId`/`environmentName`, the server-managed booking fields, `firstMessage`; (b) system-managed — `presetType`, `status`, `lastConfigurationStep`, `hasOverrides` (the Expert-Mode editor sets these from the loaded agent / forces `hasOverrides:true` on save; the platform defaults `status` to enabled on create). |

**Always emit `enabled`** — on every scenario, every guardrail, and every skill object the body contains.
It is a required plain bool with no default anywhere in the stack: omit it and the import fails
(`422 expected required property enabled to be present`), and a stored unit without it is silently
inactive at runtime. Two traps worth knowing: a platform-side pre-check can **pass** a config whose
scenario has no `enabled` (the absent key reads as *disabled*) and the save then fails with that same
`422` — so
`scripts/validate_config.py` is the gate, never a server pre-flight alone; and `enabled: false` is a
*deliberate* shape, not a mistake — it ships a skill switched off for the user to finish in the dashboard
(transfers below, and behavioral §9 on disabled drafts).

**Never fabricate a URL or a variable** — same normative force as "never a placeholder ID":

- Any URL **anywhere** (a `sendSms` message, `goalPrompt`, `greeting`) must be **supplied by the user and
  copied verbatim** — never invent, guess, shorten, or restructure one.
- AIVA **cannot generate a per-call or per-appointment link** (booking link, calendar link, tracking link):
  no such variable exists. If the user asks to "text the booking link," **say it's unsupported** and offer
  the two real paths — a `booking_confirmed` `sendSms` carrying `{{appointment.*}}` details (behavioral §6),
  or a **static user-provided URL** (e.g. the company's public booking page), pasted verbatim.
- **Never emit an invented `{{placeholder}}`** hoping the platform fills it — an unknown variable renders as
  an **empty string** (silently deleted, no braces), corrupting the message (e.g. `Book here: ` with nothing
  after).

## Default scope: self-contained only

By default the generator emits **only** `generate` fields plus the `environment` number — an agent that
greets, answers, captures and hangs up saves with nothing else to wire. How the common asks land:

- **"Answer questions / knowledge"** → put the facts in `goalPrompt` or a custom skill (within size
  limits, behavioral §7); leave `knowledgeBaseIds` empty; tell the user to attach a KB in the UI if
  the content is large.
- **Ending calls** → `scenarios` with `action: "hangup"` (always self-contained, always needed).
- **Escalation / "transfer to a human"** → scaffold a `transferToHuman` group draft (switched off, blank
  target) by default, or wire a complete real pair when the user gave you both halves. This one is **not**
  self-contained and has no zero-touch substitute — see below.
- **Safety rules** → put them in the `goalPrompt` `## Guardrails` prose section. **Do not emit the
  `guardrails` array — keep it empty:** it is accepted and stored but **inert at runtime** (the runtime has
  no `enabled` field for it, so guardrails are silently skipped — behavioral §2.1, schema §7.2).

Anything else that needs a company resource — a custom tool, an SMS sender number, a knowledge base,
appointment booking — is **out of default scope**; the default generator does not emit it. On explicit
request, handle it via the **reference decision tree** below.

### Transfers — scaffold a group draft by default, wire only a complete real pair

"Transfer to a human" means a **direct transfer**: `transferToHuman` with `destination: "agent"` or
`"group"`, a group being the preferred human target. Because a **group's extension can't be read
programmatically** (the MCP group list returns id and name only), the default the generator emits is a
**disabled draft the user finishes in the dashboard** — it does not wire a group target on its own. Three
shapes:

1. **Scaffold the group (default)** — ship the skill `enabled: false` with a rule carrying
   `destination: "group"` and the id/extension keys **omitted** (`groupId`/`groupExtension` absent). The
   group intent is visible; the target is the user's to complete. It saves cleanly and the dashboard shows
   the skill as *"Requires configuration"* with a locked toggle (see `examples/E9`). Say so in
   **user-facing** terms: *"the transfer skill is in place but off — finish setting up the transfer to your
   team in the dashboard and switch it on."* Never phrase it as DB internals ("add a group extension").
2. **`rules: []`** — the same disabled-draft idea when there is no specific group in mind at all
   (see `examples/E1`).
3. **Wire a complete real pair** — only when the user has given you **both** halves (`agentId` +
   `agentExtension`, or `groupId` + `groupExtension`), from what they told you, the config they pasted, or
   an `agent` pair fetched over MCP (`cloudtalk_list_agents` returns the extension; `cloudtalk_list_groups`
   does not). Then emit the rule with `enabled: true`.

In every case keep the **prompt honest** while the skill is off: the agent offers a callback, not a handoff
it can't perform (see `examples/E1`, `examples/E9`).

Non-negotiables around this:

- **Never guess an id or extension.** Nothing anywhere validates these values: they are stored exactly as
  written and dialled exactly as stored, with no ownership check on the way through. A wrong or half-set
  target on a **live** rule fails **only during a live call** — where advanced transfer is enabled the AI
  announces the failure and resumes, but on a cold fallback the caller is dropped silently.
- **On a draft, OMIT the id/extension keys — never blank them to `""`.** `agentId`/`groupId` are integers,
  so `"groupId": ""` is an **INVALID_TYPE** the save rejects even on a disabled skill; a draft leaves the
  keys absent. And on an *enabled* rule an empty extension satisfies every structural check, so the skill
  saves as *enabled* and the agent is told it can transfer — it then promises the caller a handoff, dials
  nothing, and fails mid-call (dead air on a cold fallback). So a draft omits the keys, and an enabled rule
  always carries a complete real pair.
- **Structure:** whenever the skill object is present, the `rules` key must be too (`[]` is fine; omitting
  it is a `422`), and every rule needs `condition` + `destination`.
- **`call_flow` only on explicit request** — when the user asks for it or says the agent runs inside a Call
  Flow. It is a hangup-and-continue: the agent ends its own step and the flow routes next, which does
  nothing for a standalone agent. When you do use it, pair it with an `extractData` routing signal for the
  flow's splitter (behavioral §3.4) and tell the user the flow must exist.
- **`answerQuestions`:** don't wire a group target under `action: "transferToHuman"` either — scaffold
  `transferToHuman` as a disabled draft (`destination: "group"`, id/extension omitted), or use
  `admitUncertainty`/`offerAlternative` (behavioral §3.2).

## When a referenced feature is requested (explicit user intent)

A *reference* field points to a company-scoped resource (ring group, agent, knowledge base, custom
tool, calendar integration, SMS sender, or a specific outbound number). **Never invent a real ID and
never leave a placeholder/sentinel ID in the body** — both produce a config that fails to save or
silently doesn't work. The config you hand over must save cleanly *and* run as-is. So, in priority
order (**connected mode inserts a *fetch* step at position 2**, which turns most *asks* into a
*confirm* — *Connected mode* below):

1. **Reuse a real ID the agent already has** — if the user's current config (or their paste) already
   contains an ID that fits the intent (a `groupId`, a `knowledgeBaseId`, a calendar `integrationId`, …),
   use it verbatim. This is the edit-flow default: the agent already exists, so its wiring often does too.

2. **Prefer a zero-touch substitute** that meets the intent with no ID:
   - "answer questions / knowledge" → put the facts in `goalPrompt` or a `custom` skill (a small FAQ
     is *better* in-prompt — lower latency); reserve a KB for a large corpus;
   - "end the call" → a `hangup` scenario.
   This is the default for most knowledge asks and stays fully zero-touch. **Transfers have no zero-touch
   substitute** — reaching a human means a real target, so they follow the two paths in *Transfers* above.

3. **Ask for the real ID and put it in** — for a resource that already exists but isn't in the current
   config (a ring group, an agent, a specific outbound number). Explain *why* you need it and say what
   happens meanwhile in the same breath, e.g. *"the transfer skill is in place but switched off — give me
   your sales group's ID and extension (Dashboard → Settings → Groups) and I'll wire it in, or pick the
   group on the skill in the dashboard and switch it on."* If the user supplies real values, use them
   verbatim — never a placeholder, never one half of a pair.

4. **Ship the working config without the feature + tell the user how to add it** — for a resource
   that must be *created* first (knowledge base, custom tool, calendar integration), or when the user
   can't or won't supply an ID. Omit that one feature so the rest still saves and runs, and put the
   "how to add it in the dashboard" step in your chat checklist (output shape below), pointing at
   [`referenced-resources.md`](./referenced-resources.md). For a **transfer** the equivalent is the
   switched-off skill: present-but-off is more useful than absent, because the dashboard then walks the
   user to the one field it needs.

**How to converse (keep it organic):** the *ship-a-working-config-first, then offer the upgrade*
default applies to **optional referenced features only** — don't interrogate the user for feature IDs
before producing anything; ask up front only when there is no substitute and the feature is the whole
point (e.g. appointment booking needs a connected calendar — say so and ask whether to include it). It
does **not** apply to **ground truth** — the business's real name, the outbound-number wiring, and IDs
for a feature the user explicitly asked for have **no sensible default**, so obtain them up front and
never invent or default them (see `SKILL.md` "Two kinds of input" / step 1). Always explain the *why*
in a sentence; never block on a question whose answer you can sensibly default (a *Design* choice);
**never hand over JSON that needs editing or wiring before it works.**

> **Cross-account caveat (when a real custom tool / SMS sender *is* supplied):** this applies **only**
> when the config came from a *different* account (its `companyId`/`environmentName` ≠ the target) —
> **not** when you're editing the user's own agent (the normal case), where the account matches and
> nothing is stripped. On a genuine cross-account paste the editor silently strips `toolCall`/`sendSms`
> actions down to plain replies, so those must be re-added in the UI. Call it out in the checklist only
> when it actually applies.
>
> **Connected mode doesn't change either half of that.** Anything you read from **this** account via MCP —
> a tool, a number, a group, a KB — belongs to the target account by construction, so it is **never
> stripped**; there is nothing to warn about. A config the user **pasted from another account** still
> loses its `toolCall`/`sendSms` references the same way, and reading real IDs over MCP doesn't rescue
> them: re-wire those actions against IDs fetched from this account, then save.

## Connected mode (CloudTalk MCP)

Everything above is the **offline** contract: you emit JSON, the user pastes it into Expert Mode. With the
**CloudTalk MCP** (voice-agents profile) connected you can read the account's real IDs and save the config
yourself. None of the emit rules relax — they tighten, because a mistake now lands in a live agent instead
of a chat message. The tool surface and its per-tool caveats live in [`mcp-tools.md`](./mcp-tools.md); what
follows is the **contract**.

**1. Round-trip or don't write.** Every update begins with `cloudtalk_get_voice_agent`, which returns the
agent's **complete config document**. Modify *that document* and send **the whole thing** back through
`cloudtalk_update_voice_agent`. **Never synthesize an update payload from the conversation** — the update
replaces the stored document with exactly what you send, so any field you didn't carry across is a field
you just deleted. No `get`, no write.

**2. Carry the two preserve/replace fields deliberately.**
- `knowledgeBaseIds` — **omitting it unlinks every knowledge base** on the agent. Carry forward the list
  you read, even when the task has nothing to do with knowledge.
- `elevenLabsSettings` — **omitted preserves** the stored object; **present replaces it wholesale**. To
  change one knob, send back the whole object with that knob changed (behavioral §9).
- **Cloning is `get` → `create`, and the copy is not the original.** There is no clone tool: whatever you
  copy is what the new agent gets. Decide **deliberately** whether `knowledgeBaseIds` should carry over
  (two agents sharing a KB is a choice, not a default), and remember that **tool assignments do not
  copy** — re-assign every custom tool the source agent had.
`optimizeStreamingLatency` behaves the opposite way to `dialTime`: omitted on a write it **resets
to `0`** rather than preserving — one more reason the update body is always the fetched document.

**3. The write is the user's decision, not yours.** Every write tool is confirm-gated (one no-op
exception: an assign/unassign that changes nothing). Called without
confirmation it returns `status: "confirmation_required"` **plus a preview of the change, as a successful
result** — that is a **success state, not an error and not a rejection**. Present the preview, say plainly
what will change on which agent, and **wait**. Never self-approve, never re-invoke with confirmation on
your own initiative, and never report the preview as a completed save. `cloudtalk_trigger_aiva_call` places
a **real outbound phone call** — same rule, and only to a number the user names.

**4. Validate locally first.** There is no validate tool, so
[`scripts/validate_config.py`](./scripts/validate_config.py) **is** the pre-save gate: run it on the
modified document before every write. Keep the body schema-only — omit the export-wrapper tags `companyId`
and `environmentName` (FE provenance the API and the validator tolerate as INFO `export-tag`, used only for
cross-account-import detection, never rejected as `unknown-field`) along with the rest of the `forbidden`
tier, none of which belong in an authored write payload.

**5. Read the status, not the transport.** Results publish no output schema, so parse tolerantly: look for
the status rather than assuming a shape, and treat a **`"validation_failed"` status inside an
otherwise-successful result as a failure**. And don't verify a write by re-listing: the `list_*` reads are
**cached for minutes and a create does not refresh them**, so a missing row after a successful create means
nothing — **wire the id the write itself returned**, and **never re-create on a miss** (that is how
duplicate agents, KBs, and tools get made).

**6. The resolution tree, connected.** The offline order (reuse → substitute → ask → omit) gains a **fetch**
step in second place, because most IDs the user would otherwise look up by hand you can now read:

| Referenced resource | Connected resolution |
|---|---|
| Outbound number / SMS sender | `cloudtalk_list_numbers` — ids, E.164, and **per-channel flags**; confirm the SMS flag before wiring a `sendSms` `senderNumber` |
| Transfer target | `cloudtalk_list_groups` (preferred) returns the **id and name only — the group's extension is not readable here**, so the default is to **scaffold the group as a disabled draft (`destination: "group"`, id/extension omitted)** (§ Transfers) for the user to finish in the dashboard. Wire the group live only if the user supplies the extension (paste, current config, or ask — Dashboard → Settings → Groups). `cloudtalk_list_agents` returns id **and** extension. Don't downgrade to an `agent` target just because its pair is complete — with a group more targets can answer before an attended transfer falls back, and a lone unavailable agent is a cold drop where advanced transfer is not enabled |
| Knowledge base | `cloudtalk_list_knowledge_bases`, linking only `ACTIVE` ones; `cloudtalk_create_knowledge_base` (`custom` or `url`) when the content is new — its **content cannot be edited after creation**, so get the text right before the write |
| Custom tool | `cloudtalk_list_voice_agent_tools` → `create` / `update`. **Create attaches**: `cloudtalk_create_voice_agent_tool` takes `voice_agent_config_ids`, so creating a tool for an agent is **one** confirm-gated write, not create-then-assign. `assign`/`unassign` are for wiring a tool that **already exists** — including after a clone, where tool assignments don't copy. The list **never returns header or parameter values**, so a stored secret can't be read back |
| Voice | **No MCP/plugin voice-list tool exists** — reuse the `voice` from a `cloudtalk_get_voice_agent` document (this agent's or another agent's), or pick from the four documented default voices (`schema.md` §4.4 — default `cgSgspJ2msm6clMCkdW9` Jessica; all four work on both providers). Always advise the user to pick their preferred voice in the dashboard voice picker (the full catalog lives there) |
| Calendar integration | **No read exists** — `appointmentBooking` stays ask-or-omit with the **disabled-draft** shape (behavioral §9) until the user supplies real IDs from the Dashboard |
| Inbound number routing | Not settable here — Dashboard only; say so instead of implying the save covers it |

Fetching is not deciding. A list with three ring groups on it is a **question for the user**, not a pick
for you — fetch to remove the lookup burden, then confirm which one. Where a resource genuinely doesn't
exist and can't be created, fall back to the offline endings: **ask**, or **omit-and-instruct**.

**7. Output shape, connected.** *Before* the write, the confirmation preview is your output: what changes,
on which agent, and what is still unwired. *After a confirmed save*, report

- **what was written and where** — the agent's **name and id**, plus the fields that changed, and the
  **`dashboard_url`** *when the write returned one*: the voice-agent create/update and a KB create do,
  the tool and assignment writes and `cloudtalk_trigger_aiva_call` do not — hand over the link where
  there is one rather than describing the navigation, and don't promise it where there isn't;
- **the platform's own diagnostics** — a **successful** write can still carry
  `voice_agent.error_codes[]` (a saved-but-degraded reference, e.g. a voice or number the company can't
  use). Read them and surface them in plain language; *saved* is not *clean*;
- **what remains** — the same setup checklist as offline, minus everything the write just handled;
- **how to verify** — a test call (inbound: the user calls the agent's number; outbound:
  `cloudtalk_trigger_aiva_call` to a number they name), then `cloudtalk_search_calls` filtered by the
  agent's **numeric** `voice_agent_id` to find the call, then `cloudtalk_get_call_transcript` /
  `cloudtalk_get_call_insights` to see what actually happened.

The offline **save smoke-test** reminder (*Output shape*, item 5) does not apply in connected mode: the
write returns its own structured result, which already tells you whether the save stuck. Re-saving to find
out is another live-agent write.

## Output shape

The offline shape — you are handing over JSON for the user to paste. In connected mode items 1–2 are
replaced by the confirmation preview and the post-save report (*Connected mode*, item 7); items 3–4 stand
unchanged. Return:

1. **The importable JSON** — pure, valid, **schema-only** v2 JSON that saves cleanly *and* runs as-is,
   reusing the agent's existing setup. No comments, no `_requiredResources`, no placeholder IDs, no
   forbidden fields — nothing the user has to remove or fix before pasting.
2. **A one-line status headline** — either
   `✅ Ready to save — nothing else to wire`, or
   `⚠️ Saves as-is, but <feature> needs <N> setup step(s) before it works`.
   An ID the user gave you is wiring already done, so it keeps the clean headline — say you carried it
   over and that it's worth confirming, but don't count it as a step. Only a resource nobody has picked
   yet earns the warning. A config on Automatic (`1`) with no real `failoverOutboundNumberId` is **not**
   ready — it will `400` in both directions — so the outbound number is a setup step until a real owned id
   (default or failover) is in place. `validate_config.py --json` draws the same line: `nothingElseToWire` follows the
   `pending` references, not the ones you merely echo back — and a sibling `saveBlocking` boolean states
   outright whether a save-refusing finding is present, so nothing has to re-derive that from the issue
   list.
3. **A short setup checklist — only when step 2 flags something.** One line per action, specific, with
   the dashboard path, pointing at [`referenced-resources.md`](./referenced-resources.md): e.g. create
   a knowledge base and add its ID; pick the ring group on the switched-off transfer skill and switch it
   on; place the agent in a Call Flow if you asked for a `call_flow` handoff. An inbound agent with no
   transfer and no new resource gets the clean headline and **no checklist** — keep the warning rare so
   it gets read. When a transfer *is* switched off, also warn plainly that a **wrong** id/extension is
   validated nowhere and fails only during a live call — which is why the values come from the user, not
   from you.
4. **The `extractData` rationale** — list each proposed `extractData` property with a one-line *why
   it's useful*, inviting the user to add or drop any (don't embed a data-collection schema silently).
5. **The save smoke-test reminder** — tell the user to save once to confirm it sticks; if the dashboard
   errors with *"Failed to update VoiceAgent,"* a referenced resource isn't provisioned in their company
   (deprecated voice, unowned `sendSms` number, custom tool missing its ElevenLabs ID, or a
   provider/language mismatch) — fix the reference, don't re-save (`referenced-resources.md`).
   **Offline only** — in connected mode the write's own result is the smoke test (*Connected mode*, item 7).

## Before returning — run the self-check

Validate against [`behavioral-guidance.md`](./behavioral-guidance.md) §8 (quality) and `schema.md`
§3/§6/§7 (structure). A config that is structurally valid but talks over callers, never hangs up, or
switches language mid-call is a failure. **In connected mode the self-check runs before the *write*, not
before the reply** — once the save lands, the fix is another live-agent write.

**For non-trivial configs** (multilingual, any transfer, data capture, appointment booking, or a
referenced resource), also run an **independent critique pass** before presenting — prefer a subagent
with fresh context, else a deliberate adversarial self-review against the §8 lenses (language consistency
incl. every `when`, greeting realism, prose coherence in the target language, scenario coverage,
`extractData` justification, schema + reuse/nothing-to-wire). Reconcile the findings and briefly note any you
deliberately override. Trivial single-purpose agents can skip it.

## Canonical few-shots

All bundled examples are **clean, schema-only, save-ready** configs — the model for default output. Every
non-E2 example carries `defaultOutboundNumberId: 1` (Automatic) **with a placeholder
`failoverOutboundNumberId`** you replace with a real owned number ID (Automatic requires a real failover in
both directions); E2 shows the failover gate by omitting it.
[`examples/E1`](./examples/E1-inbound-receptionist.jsonc) (auto-ElevenLabs receptionist — knowledge
folded into the prompt, and the **switched-off transfer** pattern) and
[`examples/E6`](./examples/E6-inbound-frontdesk-enus.jsonc) (auto-Deepgram via `en-US`, callback instead of
a handoff) are the canonical archetypes;
[`examples/E3`](./examples/E3-inbound-qualification-cfd.jsonc) is the **explicit-CFD exception** (the user
runs the agent inside a Call Flow); E2 (German outbound), E4 (Deepgram-pinned support intake),
E5 (multilingual ElevenLabs), E7 (`takeMessage`), E8 (the **identity presets** — `tone`/`verbosity` with
ElevenLabs turn-taking and background-sound knobs), E9 (a **group transfer shipped as a disabled draft with
the id/extension omitted** plus an SMS confirmation) and
[`examples/E10`](./examples/E10-inbound-booking-confirmation.jsonc) (**appointment booking** with a
`booking_confirmed` → `sendSms` confirmation) add language, provider, and skill variations.
**No example invents a transfer target.**

> **The few-shots illustrate STRUCTURE, not ground truth.** Their environment/reference values are
> placeholders, not real owned IDs: the `failoverOutboundNumberId` (`202`, on every non-E2 example, incl.
> E3), and E9's `sendSms` `senderNumber` (`+15555550100`, on an *enabled* action). **Never copy a resource
> ID or number from an example into generated output** — obtain the real value per the ground-truth rule
> (reuse → fetch → ask → omit/disable), exactly as for any reference field.

> **E2 is the one example the validator exits `1` on, deliberately.** It is on Automatic (`1`) with **no
> failover** — the save-blocking wiring warning that now applies in **both** directions (it happens to be
> outbound) — so it teaches the both-directions failover gate by failing it. Every other example exits `0`.
> Don't "fix" E2 by inventing a number ID; set a real owned `defaultOutboundNumberId` or a real
> `failoverOutboundNumberId` when you adapt it.
