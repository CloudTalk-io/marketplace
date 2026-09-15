# Voice Agent v2 — reference example configs (E1–E10)

Ten archetype configs for the v2 Expert-Mode API, authored per the
[corpus](../README.md). Each is schema-valid ([`schema.md`](../schema.md)) and passes the
[behavioral](../behavioral-guidance.md) §8 self-check — schema-only, no non-schema keys, nothing to strip.
Every non-E2 example carries `defaultOutboundNumberId: 1` (Automatic) — the dashboard's create-time
default — **with a placeholder `failoverOutboundNumberId`** you complete with a **real owned number ID**
before saving; Automatic requires a real failover in both directions, so completing that failover (or
setting a real `defaultOutboundNumberId` instead) is the one wiring step every file leaves you.
**E4, E9 and E10** carry further account-specific values to swap for your own (see the notes below). They
double as few-shot material and as executable documentation.

Provider/LLM columns reflect **V3 auto-selection** (all new configs; `schema.md` §5): provider is
language-based, and a *trivial* ElevenLabs agent defaults to lightweight Qwen unless made complex or
overridden.

> **Filename convention:** `E<n>-<direction>-<archetype>-<teaching-tag>.jsonc`. The stable ID is the
> `E<n>` (what the other docs reference); the rest is a human mnemonic. `direction` is always present;
> the optional `teaching-tag` names what the example demonstrates beyond its archetype, and is dropped
> where the archetype says it all.

| File | Archetype | Direction | Resolved provider (V3) |
|---|---|---|---|
| `E1-inbound-receptionist.jsonc` | Receptionist; knowledge in the prompt; **switched-off transfer** | inbound | ElevenLabs (auto `en`); complex via prompt length → Haiku 4.5, with a defensive `llmOverride` |
| `E2-outbound-confirmation-de.jsonc` | Appointment confirmation, German | outbound | ElevenLabs (auto `de`); complex via scenarios → Haiku 4.5 |
| `E3-inbound-qualification-cfd.jsonc` | Lead qualification → CFD routing (**explicit-Call-Flow exception**) | inbound | ElevenLabs (auto `en`); trivial-tier, `llmOverride` → Haiku 4.5 |
| `E4-inbound-support.jsonc` | Support intake, Deepgram-pinned, no transfer; **`toolCall` scenario + `extractData` webhook**, `tone`/`verbosity` on a Deepgram agent | inbound | Deepgram (`providerOverride` on plain `en`) → Haiku 4.5 |
| `E5-inbound-multilingual.jsonc` | Multilingual appointment-request intake | inbound | ElevenLabs (pinned via `providerOverride`; multilingual) → Haiku 4.5 |
| `E6-inbound-frontdesk-enus.jsonc` | US-English front desk; callback instead of a handoff | inbound | Deepgram (auto `en-US` — Deepgram-exclusive) → Haiku 4.5 |
| `E7-inbound-afterhours-message.jsonc` | After-hours message taker (`takeMessage`) | inbound | ElevenLabs (auto `en`); trivial-tier, `llmOverride` → Haiku 4.5 |
| `E8-inbound-frontdesk-identity.jsonc` | Hotel front desk; **`tone`/`verbosity` + `elevenLabsSettings` showcase** | inbound | ElevenLabs (auto `en`); complex via prompt length → Haiku 4.5 |
| `E9-inbound-support-transfer-sms.jsonc` | Support line; **group transfer as a disabled draft (id/extension omitted) + `sendSms`** (the default scaffold), a `## Known facts` variables section, a switched-off scenario | inbound | ElevenLabs (auto `en`); complex via scenarios → Haiku 4.5 |
| `E10-inbound-booking-confirmation.jsonc` | Appointment booking; **`appointmentBooking` + `booking_confirmed` → `sendSms`** with `{{appointment.*}}` | inbound | ElevenLabs (auto `en`); complex via scenarios → Haiku 4.5 |

## Self-contained — references handled without new resources

Every example needs a real owned outbound number ID of yours (the placeholder `failoverOutboundNumberId` to
replace, per Conventions), but no example needs any *other* company resource by default. Where an archetype
would classically need one, most of these configs invent nothing and take the **substitute-first** path from
[`generator-contract.md`](../generator-contract.md). Three capabilities have no zero-touch substitute —
reaching a human, calling a custom tool, and booking into a calendar — so **E4** and **E10** ship the tool
and calendar wired (each with the values to replace named in its header), while **E9** ships its human
handoff as a **disabled group draft** the user finishes in the dashboard:

- **E1** — the receptionist's FAQ lives in the `goalPrompt` (a screenful of facts is lower-latency than a
  KB). Its `transferToHuman` ships **switched off** (`enabled: false`, `rules: []`) because a live transfer
  needs a real agent/group **id + extension**: the prompt therefore offers a callback, and `routingDecision`
  records who should follow up. This is one draft shape; **E9** shows the other — a group scaffolded with the
  id/extension **omitted**. Give a complete real pair and either ships wired (`enabled: true`) instead. For a
  large FAQ, create a KB in the UI and add its ID.
- **E3** — the **only** example using `destination: "call_flow"`, and only because its user runs the agent
  as a step inside a Call Flow. Read it as the exception; E9 is the default and E1 the no-target fallback.
- **E4** — a Deepgram-pinned support line that is **intake only** as far as humans go: it gathers
  order/issue details and a callback number, with no transfer skill at all. It does show the two shapes
  that reach *systems*: a `toolCall` scenario firing a company custom tool (`toolReferenceId` — replace
  it), and `extractData.endpoint`, the optional webhook the platform posts the captured properties to —
  shipped **commented out**, so as saved the example keeps what it captures in CloudTalk; uncomment the
  key and point it at a receiver you control to forward the data. It also carries `tone`/`verbosity`,
  which are provider-agnostic and so work here despite
  Deepgram ignoring `elevenLabsSettings`.
- **E6** — a front desk that answers what it knows and takes details for a callback, with no transfer skill.
- **E5** — a multilingual agent that **takes the appointment request** and hands it to the studio, so it
  stays self-contained. **E10** is the other half of that choice: booking straight into a connected
  calendar, which costs a calendar integration. E5's three hangup scenarios carry an **empty `reply`** on
  purpose: a scenario reply is spoken verbatim, so the closings live in the `goalPrompt` and reach a German
  or French caller in their language rather than as a fixed English line (behavioral §4.2).
- **E2** — outbound confirmation; it confirms verbally. To text a confirmation, add a `sendSms` scenario
  with a company-owned sender (**E9** shows the caller-gated shape, **E10** the booking-triggered one).
  Any URL in the message must be a **static user-supplied link, copied verbatim** — AIVA can't generate a
  booking/calendar link (behavioral §6).
- **E8** — a hotel front desk carrying the **structured identity presets** (`tone`, `verbosity`) and the
  ElevenLabs conversation knobs (`turnEagerness`, the `interruptionIgnoreTerms` /
  `interruptionIgnoreTermLanguages` pair, a low-volume `backgroundSound` bed). Fully self-contained: no
  transfer skill, so the prompt offers a callback like E6. It also shows another route to Haiku **without
  an `llmOverride`**: its `goalPrompt` is over 1500 characters, which on its own marks the agent complex
  (E2/E9/E10 get there on scenario count and E5 on `secondaryLanguages` — among other routes: E9 and E10
  are long-prompted too, and E5 also runs several scenarios). Note what the presets *replace*: the
  prompt's style section covers only one-question-per-turn and speech formatting, and never restates "be
  professional and calm" in prose.
- **E9** — the **default transfer scaffold**: `transferToHuman` shipped `enabled: false` with a group rule
  whose intent is visible (`destination: "group"`, one specific `condition`) but whose target keys are
  **omitted** (no `groupId`/`groupExtension`), for the user to finish in the dashboard — a group's extension
  can't be read programmatically, and `groupId` is an integer so it is omitted, never blanked to `""`. It also scaffolds `confirmationRequired` and `includeProperties`/`customProperties`
  (the data handed to the human who picks up the transfer). While the skill is off the prompt offers a
  callback, not a handoff. It pairs that with a `sendSms` scenario whose `params.message` is **fixed config
  text** — the LLM only decides *whether* to send — and which contains no link at all, since AIVA cannot
  generate one. It also shows a `## Known facts` section handing the agent `{{contact.*}}` /
  `{{caller_number}}` values (with the empty-string trap spelled out) and one scenario shipped
  `enabled: false`. **One account value to replace** (`params.senderNumber`), plus the transfer to finish in
  the dashboard: see the note in Conventions.
- **E10** — the booking archetype: `appointmentBooking` switched on against a connected calendar, plus
  the `triggerType: "booking_confirmed"` + `sendSms` pair that texts the caller what they just booked.
  It teaches the `{{appointment.*}}` split — `event_name` / `service_description` / `duration_minutes`
  resolve from the config, while `start` / `start_pretty` / `end` / `event_id` / `caller_name` / `reason`
  are empty until a booking actually succeeds — and why the message carries no link: there is no
  booking/calendar-link variable to put in one. `when` is omitted on that scenario because the platform
  overwrites it. Replace the calendar `integrationId`/`calendarId` and the SMS `senderNumber`.

> **Provider coverage:** E4 *forces* Deepgram via `providerOverride` (on a language that would otherwise
> auto-pick ElevenLabs); E5 pins ElevenLabs via `providerOverride` for its multilingual config; E6 shows
> Deepgram *auto-selected* via the Deepgram-exclusive `en-US`.

## Conventions

- **`.jsonc`** — the `//` comments are teaching notes; strip them for a pure-JSON paste. The body has no
  `_requiredResources` and no placeholder resource IDs inside a live reference, but every non-E2 file carries
  a **placeholder `failoverOutboundNumberId`** to replace, and E4/E9/E10 carry further illustrative values.
  **Outbound numbers:** completing the outbound number is a **setup step**. Every non-E2 example is
  `defaultOutboundNumberId: 1` (Automatic) — the dashboard's create-time default — with a placeholder
  `failoverOutboundNumberId`; complete it with a real owned number ID (Automatic requires a real failover
  in both directions), or set a real owned `defaultOutboundNumberId` instead. When editing an existing agent, keep that agent's own two values. E2
  omits the failover on purpose to demonstrate the save-blocking gate.
- **The illustrative account values** — the places the corpus ships account-specific data (besides the
  `failoverOutboundNumberId` placeholder every file carries), each named in its file's header:
  - **E9** — `params.senderNumber: "+15555550100"` (the SMS sender). The transfer ships as a disabled group
    draft with the id/extension **omitted** — finish it in the dashboard rather than substituting an ID here.
  - **E10** — `skills.appointmentBooking.integrationId` + `calendarId` (the connected calendar) and
    `params.senderNumber: "+15555550188"`.
  - **E4** — `scenarios[0].toolReferenceId` (the custom tool). Its `skills.extractData.endpoint` ships
    commented out, so there is nothing to replace unless you enable the webhook.

  Replace them all before saving. Nothing validates a transfer id/extension, so a wrong pair fails only
  mid-call — the AI resumes where advanced transfer is enabled, but on a cold fallback the caller is
  dropped; an unowned sender number is refused at save; a wrong
  calendar ID fails when the agent tries to book. In connected mode read groups and numbers with
  `cloudtalk_list_groups` and `cloudtalk_list_numbers` (SMS-capable numbers only —
  [`mcp-tools.md`](../mcp-tools.md)) and create tools with `cloudtalk_create_voice_agent_tool`; calendar
  integrations have no MCP read at all. Offline, copy every one of them from the Dashboard
  ([`referenced-resources.md`](../referenced-resources.md)). The validator lists supplied IDs as
  *already wired* rather than as pending work — a supplied ID counts as wiring done, so confirming the
  values are real is on you.
- **`enabled` everywhere:** every scenario and every skill object carries an explicit `enabled` bool.
  Nothing defaults it — a missing one fails the import with `422`, and a stored unit without it never fires
  (`schema.md` §6/§7).
- **`guardrails` empty:** every example ships `"guardrails": []`. The array is accepted but **inert at
  runtime** (the runtime has no `enabled` field for it, so guardrails are silently skipped), so always-on
  safety rules live in the `goalPrompt` `## Guardrails` prose section instead (`schema.md` §7.2).
- **Language:** every `reply` **and every scenario/guardrail `when` condition** is written in the
  agent's primary `language` (behavioral §5). The English `when` clauses in E1/E3–E10 are correct only
  because those agents are English-primary; the German agent **E2** shows localized German `when`
  clauses — that is the rule for any non-English agent, not just the spoken `reply`.
- **Voices are premade and work on both providers** — every example uses one of the four default voice IDs
  (`schema.md` §4.4), which is why none of them needs a voice of yours. The same voice speaks whatever the
  agent's `language` is: **E2** is German and keeps an American-English-labelled voice (Jessica) for exactly
  that reason. Only Jessica is female in this default set; **always advise the user to pick their preferred
  voice in the dashboard voice picker**, which holds the full language-filtered catalog. In connected mode
  you can also reuse a voice from an existing agent via `cloudtalk_get_voice_agent` rather than guessing an ID.
- **Identity presets and ElevenLabs tuning:** `tone` and `verbosity` are **provider-agnostic** — **E8**
  pairs `["professional","calm"]` with `concise`, **E4** sits at the other end with `["empathetic"]` and
  `thorough` on a *Deepgram* agent. The `elevenLabsSettings` block is ElevenLabs-only (ignored on
  Deepgram) and **no single file carries all of it**: coverage is **E5 ∪ E8**. E5 shows the turn-taking
  subset tuned for data collection — `turnEagerness: "patient"`, `speculativeTurn`, `turnModel:
  "turn_v3"`, `vad`, `asrKeywords`; E8 adds the remaining five — the `interruptionIgnoreTerms` /
  `interruptionIgnoreTermLanguages` pair and `backgroundSound` with its `preset`, `volume` and
  `crossfadeLoop` — plus `turnEagerness: "normal"`, the one leaf both files carry.
- **Create-shaped, so preserve-on-omit is invisible here.** Every file is a complete document, which is
  what you want for a create or a full-document paste. On the connected **get → modify → update** path
  the same completeness is a *requirement*, because omission is not neutral and not uniform:
  `knowledgeBaseIds` omitted **unlinks every KB**, `optimizeStreamingLatency` omitted **resets to `0`**,
  `elevenLabsSettings` present **replaces the whole object** (omitted preserves it), and `dialTime`
  omitted preserves. No example can demonstrate that — it only shows up on the second write — so it is
  stated here: send back the document `cloudtalk_get_voice_agent` gave you, modified
  ([`mcp-tools.md`](../mcp-tools.md)).
- **Validator expectations:** `python3 ../scripts/validate_config.py <file>` exits `0` on every example
  except **E2**, which exits `1` on one warning: Automatic (`1`) with no `failoverOutboundNumberId`. That is
  deliberate and expected — the warning is the validator refusing to call a config save-ready under Automatic
  without a real failover, which is now required in **both** directions (no self-heal). It teaches the gate by
  failing it; set a real owned `defaultOutboundNumberId` or `failoverOutboundNumberId` when you adapt it.
- After saving, a **"Failed to update VoiceAgent"** error means a referenced resource isn't provisioned in
  your company (deprecated voice, unowned `sendSms` number, custom tool missing its ElevenLabs ID, or a
  provider/language mismatch) — fix the reference; re-saving won't clear it (`referenced-resources.md`).
