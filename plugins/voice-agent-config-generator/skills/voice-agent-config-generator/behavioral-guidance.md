# Voice Agent v2 — behavioral guidance (what performs well)

> Companion to [`schema.md`](./schema.md). The schema tells you what is **valid**; this doc tells
> you what **performs well**. A config can pass every validation rule and still talk over callers,
> never hang up, transfer everything, or switch language mid-call. These rules prevent that.
>
> **Scope & emit mechanics** (edit-an-existing-agent default, the reference decision tree — reuse /
> fetch / substitute / ask / omit — and the connected-mode write contract) live in
> [`generator-contract.md`](./generator-contract.md); the rules below are provider-agnostic *quality*.

**The platform mediates everything.** The config is consumed by **the platform**, which builds the
speech-provider payloads for you. ElevenLabs/Deepgram guidance here applies **only through the fields
the v2 schema exposes**; the knobs the platform pins or manages on your behalf (ElevenLabs `style`,
`speed`, TTS model, RAG `usage_mode`/chunk counts, turn timeouts, ASR provider) are **not**
user-actionable — they are not settings you own, and changing anything in the speech provider's own
console has no effect on your agent, so never point anyone there. Where the schema leaves an
`elevenLabsSettings` field unset the provider's own default applies, **and those defaults drift** — so
set a field explicitly when its value matters.

---

## 1. Mental model — how the config becomes a prompt

Everything you write is **assembled into one system prompt** at call time. There is no separate
"scenario engine" — scenarios, guardrails, skills, and language all become prompt text a single LLM
interprets. Consequences:

- **Scenario `when`/`reply` text is injected near-verbatim** — the `reply` is presented to the LLM as
  the thing to say, and the `when` as the condition to watch for. Because **both** sit in the prompt the
  model reads every turn, both belong in the agent's `language` (§5): an English `when` on a non-English
  agent is foreign text in the live prompt.
- **The runtime injects a language directive** (`Communicate in <language>`). Text in another
  language fights it.
- **Built-in tools become callable functions** with protocol sections (TRANSFER/HANGUP/SMS/BOOKING)
  appended.
- **`greeting` is injected** as a greet-the-caller instruction — so if `goalPrompt` *also* contains
  the greeting, the agent may say it twice.
- **`extractData` is NOT in the prompt** — it runs post-call on the transcript.

---

## 2. Prompt architecture — `goalPrompt` and `skills.custom`

### 2.1 The five prompt components

Every well-performing agent's prompt material (across `goalPrompt` + custom skills) covers all five.
Missing two or more reliably produces inconsistent behavior:

1. **Identity** — clear role and context, so tone/intent/priorities stay consistent.
2. **Style guardrails** — how it should sound: brevity, clarity, conversational behavior.
3. **Response guidelines** — handling mishearing/repetition, staying in character (no
   hallucinations), and off-topic questions without losing the task.
4. **Task flow with branching logic** — what to ask, in what order, what to do per answer.
   **One question per turn**; make decision criteria explicit so the agent never concludes (e.g.
   "qualified") without the minimum required answers.
5. **Hang-up instructions** — how/when to end cleanly, including negative paths (unqualified,
   uninterested, needs human) — paired with hangup scenarios (§4).

**Generation rule:** draft `goalPrompt` as a structured document covering 1–5 (short markdown headers
inside the prompt help the LLM). It can be substantial — a **soft target of up to ~250 words**; length
itself is not a problem. The bundled validator flags only a genuinely empty or one-line prompt as thin.

**ElevenLabs' six-block guide** (Personality, Environment, Tone, Goal, Guardrails, Tools) maps onto
the same five. Worth adopting:
- Write the task flow as a **numbered step-by-step workflow**.
- Put non-negotiable rules under one **`# Guardrails`** heading (models pay extra attention); don't
  scatter them. This is prose inside `goalPrompt` — *always-on* behavioral constraints — and it is where
  safety rules belong, because the v2 **`guardrails` array is currently inert**: the runtime has no
  `enabled` field for it, so stored guardrails deserialize to disabled and are silently skipped (they do
  not take effect end-to-end — schema §7.2). **Do not populate the `guardrails` array; keep it empty**
  and express every constant rule in this prose section instead.
- Keep instructions **short, clear, action-based**; verbose wording is an anti-pattern.
- **Repeat the 1–2 most critical rules twice** (recency-bias counter) — only those.
- Target **2–3 sentence responses** unless detail is requested.

#### `tone` and `verbosity` — the identity presets (schema §11)

Two structured knobs back the Identity/Style components; they steer the agent without prose. **Emit
either one only when the use case wants a non-default** — an unset key takes the platform default, which
is the right answer for most agents.
- **`tone`** — **one or two** labels drawn from the closed set (`professional`, `friendly`, `casual`,
  `calm`, `empathetic`, `direct`): a blend expresses each preset more weakly than a single label, and
  only one- and two-label combinations have been validated (schema §11). It is an allowlist, **not free
  text** — nuance beyond the six labels goes
  in `goalPrompt` style guardrails, described as intent in the caller's language. Unset (omitted or `[]`)
  means the platform applies `["friendly", "direct"]`.
- **`verbosity`** — `concise` for quick transactional agents (booking, confirmations), `standard` for
  the common case, `thorough` only when callers genuinely need detail. Unset (omitted or `""`) means the
  platform applies `standard`. It is a length dial, not a replacement for the Response-guidelines prose.
- These presets **complement** `goalPrompt`; keep them consistent with it rather than contradicting the
  style you already wrote there. Neither one replaces the platform's own safety and style baseline (§9).

### 2.2 Custom skills: few, substantial, behavioral

- **DO** keep custom skills to a recommended **2–4**; up to **6** is tolerated, and the validator warns
  only **above 6**. Each one a genuinely separate *capability*.
- **DON'T** create trivial skills (< 50 words) — short rules go in `goalPrompt`.
- **DON'T** exceed ~2000 words in any skill; factual content > ~500 words → a knowledge base.
- **DON'T** put URLs as knowledge sources in skill prompts (the agent can't browse) — use a URL-type
  KB. A URL is fine only as **literal text to read out or send, and only when the user supplied the exact
  URL** — copy it verbatim; never invent, guess, or shorten one. There is **no per-call/dynamic link** (no
  booking/calendar-link variable — §6).
- **DON'T** mention any business/product/URL other than the one this agent serves (copy-paste defect).
- **DO** include a grounding instruction: *"use only information from this prompt and the knowledge
  base; do not infer or add anything else."* Add channel guardrails when needed ("Only offer SMS;
  never mention WhatsApp/email").
- **DO** declare injected facts in a dedicated section ("## Contact: You are calling {{name}}…"). Each
  `{{variable}}` is substituted inline before the agent reads the prompt — an unset one collapses to an
  empty string (never visible braces, and no cue for the agent to ask). So one dropped only inside an
  example line resolves to a bare, unframed value (or nothing); the facts section is what gives the
  resolved value a role the agent can act on.

### 2.3 Prompting for custom tools (`toolCall` scenarios)

Follow the per-tool template: **when to use** (explicit triggers), **parameters** (format spec *with a
concrete example*), **usage sequence**, **error handling**. Key rules:
- Speech is spoken-style ("john at gmail dot com") but **tool parameters must stay machine-formatted**
  — without a format example the LLM passes spoken-style values.
- Before **irreversible actions** (booking, refund, sending data): state the details, get explicit
  confirmation, then call the tool.
- Define failure behavior: acknowledge, **never invent a result**, offer an alternative, escalate
  after 2 failed attempts.

---

## 3. Skills — behavioral rules per skill

**An enabled unit that isn't fully wired is dropped at call time — silently.** A `transferToHuman` rule
missing a complete target, a `sendSms` action missing its sender number or its message: the save
succeeds, nothing warns, and the capability simply isn't there while the rest of the config still behaves
as though it is. So every enabled unit gets **explicit, complete wiring**, or it ships `enabled: false`
(§9) — never enabled-and-half-filled.

### 3.1 `extractData` — post-call, passive, atomic

- **It does not steer the live conversation.** It runs **after the call, against the transcript** (a
  runtime code comment confirms extract-data is handled post-call, not injected into the prompt), so
  declaring a property does **not** make the agent ask for it. To actively *collect* a value, write the
  ask into `goalPrompt`/a custom skill **and** define the matching `extractData` property — the two
  together.
- **DO** make each property **atomic** — one fact per property; split "name and phone number".
- **DO** write `description`s as extraction instructions ("order number, digits only"), not questions.
- **DON'T** put conditional logic or `{{contact.x}}` masks in descriptions — both degrade extraction.
- **DO** have the agent **restate key facts aloud** — extraction works on the transcript.
- **DO present your proposed properties to the user** — list each with a one-line *why it's useful* and
  invite them to add or drop fields. Don't embed a data-collection schema silently; the user owns what
  gets captured.
- If extracted values drive **CFD routing**, tell the user to test extraction before going live —
  splitter mismatches silently drop calls.

### 3.2 `answerQuestions` — don't default to transfer

- **DON'T** set `action: "transferToHuman"` unless the agent has a KB or substantial skills to answer
  from first — auto-transfer on every unanswered question produces excessive transfers. Prefer
  `admitUncertainty` or `offerAlternative` (the two self-contained actions, `schema.md` §6.5); reserve
  `transferToHuman` for explicit transfer intents — with a real id + extension for a direct agent/group
  target; `call_flow` (CFD-embedded only) needs neither (§3.4).
- **`action` sets a global conversation style, not this skill's local behavior.** It shapes how the agent
  carries itself whenever it is short of an answer *anywhere* in the call — not only inside the
  answer-questions block. Pick it for the whole conversation: `admitUncertainty` reads as careful,
  `offerAlternative` as helpful-and-redirecting, `transferToHuman` as escalation-first.

### 3.3 `takeMessage` — inbound only

- **DON'T** enable on an outbound agent — the agent initiated the call.
- **Present-but-disabled renders differently from absent.** `takeMessage` with `enabled: false` puts an
  explicit *cannot take messages* instruction in the prompt, so the agent will state that limitation when
  a caller asks; leaving the skill out entirely says nothing, and the agent handles the request from its
  general instructions. Emit the disabled skill **only when you want that refusal spoken** — otherwise
  omit the key.

### 3.4 `transferToHuman` — specific conditions, right destination

- **DO** write each `condition` as a **specific, enumerable trigger** under **120 characters** ("caller
  asks about billing or invoices") — past 120 the validator warns. Vague conditions ("anything the agent
  can't handle") fire constantly.
- **The destinations, in order of use:**
  - `group` / `agent` — the **default**: a live in-call transfer to a real target (`reference` —
    [referenced-resources](./referenced-resources.md)). Needs **both** the id and the extension.
    Where advanced transfer is enabled for the company these run **attended**: the second leg is placed
    while the caller stays with the AI, and on busy, decline, timeout, or a dropped leg the AI announces
    the failure and **resumes the conversation** — the caller is not stranded. Where it is not enabled
    they fall back to a **cold** transfer with no resume. **Prefer `group`**: more targets can answer
    before an attended transfer has to fall back, and a lone unavailable agent is a cold drop for any
    company not on advanced transfer.
  - `call_flow` — **only when the agent runs as a step inside a Call Flow** (the user says so or asks for
    it). The agent hangs up and the flow routes next; for a standalone agent it is just a hangup. In a
    CFD-embedded agent, expressing transfer intent this way — or as plain `action: "hangup"` scenarios —
    is **correct and intended**; give the CFD a routing signal via an `extractData` property. **Inbound**
    only (no flow to return to on outbound).
- **No real target? Ship the skill off as a draft.** The default is to **scaffold the group**:
  `enabled: false` with a rule carrying `destination: "group"` and the id/extension keys **omitted**
  (`groupId`/`groupExtension` absent — never blanked to `""`, an INVALID_TYPE on the integer id) — the group
  intent stays visible and the user completes the destination in the dashboard (a group's extension can't be
  read programmatically, so the target is theirs to finish).
  When there is no group in mind at all, `enabled: false` + `rules: []` is the other draft shape. Both save
  cleanly, the dashboard shows the skill as *"Requires configuration,"* and you tell the user in plain,
  user-facing terms — *"finish setting up the transfer to your team in the dashboard"* — never in DB terms
  like "add a group extension." Keep the prompt honest while it's off: the agent offers a **callback**, not
  a handoff it can't perform — a promise it can't keep is the defect the config would otherwise ship. Never
  guess an id/extension for a live rule: nothing validates them, so a wrong one fails only mid-call — where
  advanced transfer is enabled the AI announces the failure and resumes, but on a cold fallback the caller
  is dropped.
- ElevenLabs agents add an ask-before-transfer step when `confirmationRequired: true` — the scaffold
  defaults it to `true` (the dashboard's create-time default), so the agent announces the handoff before
  moving the caller; leave it off only where speed matters more than the announcement, such as a pure
  routing or triage line.

---

## 4. Scenarios, hangup, and call duration

### 4.1 The agent MUST be given a way to end calls

The v2 API has **no `hangup` field** — ending calls is expressed only through a scenario carrying an
**explicit `action: "hangup"` *and* `enabled: true`**. Both halves count: an omitted `action` is a plain
reply, not a hangup, and a hangup scenario shipped switched off — or missing its `enabled` key, which
decodes to disabled — grants nothing. The runtime exposes `end_call` only when at least one such
scenario exists; otherwise it injects *"You are unable to end the call yourself."* An agent with no
enabled hangup scenario cannot end a call.

**Generation rule:** always include hangup scenarios for at least:
- (a) **normal completion**; (b) **prolonged silence / unresponsive caller**; (c) **voicemail
  detection** for outbound — written as **positive instructions** ("leave this message, then end the
  call"), not negatives ("DO NOT say you'll leave a voicemail").

Platform facts: the agent **cannot navigate IVR menus** (detection only, no DTMF) and **cannot
measure silence duration** ("hang up after 30s of silence" is not implementable). A 30-second *audio*
inactivity disconnect exists but is a transport safety net, not graceful ending.

### 4.2 Scenario `reply` = exact spoken text, in the agent's language

- **DO** write `reply` as the **literal sentence to speak**, in the agent's `language`.
- **DON'T** write meta-instructions (`Say:"Goodbye." And proceed to end the call.`), `"."`,
  `"Nothing"`, `"Say nothing"` — the quoted/literal fragment is spoken verbatim, word for word.
- **DON'T** embed conditional logic (`"(if confirmed) X, (if not) Y"`) — parentheticals get read aloud.
  One scenario per branch.
- **AVOID** instructional replies (`"Politely end the call."`) — in a **non-English agent** an English
  instruction causes **language bleed**. Prefer an empty `reply` over an English instruction.
- **The sibling `when` follows the same language rule** — write it in the agent's `language` too (§5);
  it is injected into the prompt, not an internal English matcher.

### 4.3 One owner per behavior

- **DON'T** handle the same trigger in both `goalPrompt` and a scenario with different outcomes.
- **DON'T** create a call-start scenario (`when: "the call is picked up"`) alongside a non-empty
  `greeting` — it can override the greeting and stop the goal flow.
- **DON'T** repeat the `greeting` text in `goalPrompt` — the runtime already injects it (double-say).
- **DON'T** give contradictory capability statements across skills.

### 4.4 `maxCallDuration` — a generous safety cap, not a conversation timer

A **hard ceiling in minutes**: when reached the call is **cut off mid-conversation** (on ElevenLabs it
is passed as the conversation's max duration; `value × 60` seconds). It is the **last line of defense**
when hangup/silence handling fails — **not** the graceful length control (that's your hangup scenarios
and prompt). So set it with **generous headroom above the expected call length** — too tight and it
truncates a legitimate call.
- The platform **requires** the field and applies **no default of its own** (there is no "240"); if you
  omit it the dashboard fills **30**. Always emit it deliberately.
- **Inbound** (receptionist, intake): **~20–30 min**. **Outbound** (cold call, confirmation, survey):
  **~10–15 min** (headroom over the ~2–3 min a short call actually takes).
- **The documented edges the validator warns at:** **≤ 2 min** is too tight (it truncates legitimate
  calls), **> 30 min on an outbound** agent and **> 60 min on an inbound** one are more headroom than any
  real call needs. The recommendations above sit comfortably inside all three. **There is no hard API cap**,
  but keep it **≤ 120**: a value above that is a recommendation warning, not a save refusal — a ceiling that
  high is a safety net nobody needs.
- Only set a **tight** cap (e.g. 3–5 min) when the user explicitly wants calls hard-stopped at that
  length and accepts that a longer legitimate call will be cut off.

---

## 5. Language consistency

- **Defaulting the `language` field.** When the user does not specify the agent's language and states no
  caller-language requirement, default `language` to the language the user is writing in during setup,
  resolved to a supported code (`schema.md` §4.3); provider auto-selection then follows `schema.md` §5.
  Name it as an overridable default the user can change in one word. If the setup conversation's language
  is not a supported agent language, fall back to a supported one and say so. This decides which language
  the content rules below are written in; it is a default, not a new field.
- **DO** write `goalPrompt`, custom skills, `greeting`, all scenario/guardrail `reply` fields, **and all
  scenario/guardrail `when` conditions** in the agent's **`language`**. The runtime injects
  `Communicate in <language>`; substantial content in another language causes mid-call switching. The
  `when` is injected near-verbatim (§1), so it is in-prompt content too — an English `when` on a Czech or
  German agent is exactly the kind of foreign text that triggers switching. (See `examples/E2` — German
  agent, German `when`.)
- For **multilingual** (ElevenLabs + `secondaryLanguages`), the runtime adds auto language detection
 — keep prompt material in the primary language; don't write mixed-language prompts.
- Structural English (markdown headers, field names) is fine; **sentences the model might echo** are not.
- When several languages are needed but not in the *same* call, prefer **one agent per language**.

---

## 6. Direction-specific rules

### Inbound
- `startSpeakingFirst: true` (enforced) **paired with a concrete non-empty `greeting`** — the two always
  travel together. `true` with an empty greeting doesn't open on silence, but it does fall back to a
  generic default line that names no business; never ship that as the opener.
- Cover business-hours/identity questions via KB or skills before enabling
  `answerQuestions → transferToHuman` (§3.2).
- **After-hours:** use **two agents** routed by the CFD time condition, not time-based scenario logic.

### Outbound
- **DO** set `startSpeakingFirst: true` + non-empty identifying `greeting` — the agent is the caller;
  waiting for the callee opens with dead air. **The two go together:** `startSpeakingFirst: true` **and**
  a concrete greeting. `false` with an empty greeting is the trap — the call connects to silence and the
  person on the other end hangs up before the agent has said anything.
- Greeting should identify the business **by its real name** and the reason for calling immediately
  (compliance + answer-machine). If you don't know the name, **ask the user** — it's ground truth
  (`SKILL.md` step 1), never coined from the use case — or, only if they want a template, use a clearly-marked placeholder (`[Company Name]`)
  and say so. **Never** ship a nameless opener ("…calling from a company that sells air conditioning"):
  it is unrealistic, non-compliant, and the most visible tell of an auto-generated config. A good greeting
  names a real business and reads like a person would actually say it aloud.
- Include a **voicemail-detection hangup scenario** (§4.1) and a short `maxCallDuration` (§4.4).
- `takeMessage` off (§3.3).

### Outbound dynamic variables (`{{…}}`)

> The full variable reference — every family the platform resolves, when, and with what — is
> [`variables.md`](./variables.md). This section covers the outbound authoring rules only.

Outbound personalization values — the callee's name, appointment date/time, order number, etc. — are
**not auto-injected**. They arrive as **`call_properties`** set by whatever triggers the call (a campaign,
the public API, or a Call Flow), and the runtime substitutes them into the prompt at call time. So when an
outbound agent personalizes:

- **Declare every `{{variable}}` in a dedicated facts section** of `goalPrompt` (§2.2) — e.g.
  `## Contact\nYou are calling {{customer_name}} about the appointment on {{appointment_date}}.` A variable
  is substituted inline before the agent reads the prompt, so one dropped only inside an example line has no
  framing — and if it's unset it collapses to an empty string (see next point), never surfacing as braces or
  a cue to ask. (See `examples/E2`.)
- **The user must wire matching `call_properties` keys at the trigger** — the names must match exactly. Say
  this plainly in your output: the config alone cannot supply the values. An **unset/unknown variable
  resolves to an empty string** — silently deleted, no error, no visible braces (this holds **everywhere**
  the engine runs: `goalPrompt`, `greeting`, `sendSms` message). So **declare only variables the trigger
  will actually supply**, and **never rely on an undeclared variable being visible as a cue** — it vanishes,
  leaving a broken line (e.g. `calling about ` with nothing after).
- The platform **does** auto-inject the current date/time in UTC (§7c) — but **not** contact/campaign data.

(Inbound agents rarely need this — they have no pre-call context beyond the caller's number.)

### Template variables — the same substitution runs on `goalPrompt`, `greeting`, and `sendSms` messages

One `{{…}}` template engine resolves variables in **all three** places. The resolvable sets:

- **Call-placement dynamic variables** — any key the caller passes when placing an outbound call (above).
- **`{{caller_number}}`** — the caller's number.
- **`{{contact.*}}`** — CRM contact fields (`{{contact.name}}`, `{{contact.company}}`, emails, …) plus
  `{{contact.custom.<title>}}` for a custom field.
- **`{{appointment.*}}`** — from the `appointmentBooking` skill. Known from config even before booking:
  `{{appointment.event_name}}`, `{{appointment.service_description}}`, `{{appointment.duration_minutes}}`.
  Filled once a booking succeeds in-call: `{{appointment.start}}`, `{{appointment.start_pretty}}`,
  `{{appointment.end}}`, `{{appointment.event_id}}`, `{{appointment.caller_name}}`, `{{appointment.reason}}`.

An **unknown/unset variable resolves to an empty string** (no error, no braces) — so never invent a
`{{placeholder}}` hoping the platform fills it, and **never inject a URL as a variable**: URLs must be
**user-supplied literal text, copied verbatim** (no per-call/booking-link variable exists).

### Booking confirmation by SMS — the one supported recipe

To text a customer after they book **during the call**: a scenario with `triggerType: "booking_confirmed"`
+ `action: "sendSms"`, whose `params.message` uses real `{{appointment.*}}` variables (e.g. *"You're booked
for {{appointment.event_name}} on {{appointment.start_pretty}}."*). It fires automatically once the booking
succeeds; `when` may be omitted (the API auto-fills it). Needs a company-owned `senderNumber` (reference
tier — `referenced-resources.md`). What this **cannot** do:

- **No booking/calendar link** — there is no such variable; the calendar event link is discarded by the
  runtime. Offer a **static user-provided URL** (the company's public booking page, verbatim) if they want a
  link at all.
- **No email invite**, and the event is **not added to the customer's calendar** — the booked event lands
  only in the company's connected calendar (Google Calendar or Outlook), with no attendees.

---

## 7. Knowledge bases vs. prompts

- **DO** move factual/reference content (FAQ answers, product details, changing policies/hours) into a
  **knowledge base**; keep skills/goal focused on *behavior*. Threshold: > ~500 words → KB.
- KBs are **referenced company resources** — a config only references existing `ACTIVE` KBs; the user
  creates them first ([referenced-resources](./referenced-resources.md)).
- Under V3 a KB does **not** change the provider; it marks the agent "complex", upgrading the
  ElevenLabs auto LLM from Qwen to Haiku 4.5 (`schema.md` §5).
- **Provider mechanics differ:** ElevenLabs uses RAG (long docs; retrieved chunks appended each turn);
  Deepgram puts whole docs in context (keep each doc small — well under 10 pages — many small files).
  Text-only, simple layout.
- **Tiny KBs (~a screenful) are better as a custom skill** (lower latency).
- ElevenLabs RAG: ~250 ms/turn added latency; ~20 chunks/turn; **URL KBs scrape one page only**.

### 7a-bis. ElevenLabs numeric settings — what values to pick

Voice fields (`stability`/`similarity`/`optimizeStreamingLatency`) and `elevenLabsSettings` take
effect **only when the resolved provider is ElevenLabs**. *When* to reach for each `elevenLabsSettings`
knob at all — and its preserve/replace mechanics on an update — is §9.

**The three voice numbers are authoring-set and pass straight through to ElevenLabs — the API applies no
default and does NOT backfill them.** `stability` and `similarity` are **required** (omitting either fails
the save); omitting `optimizeStreamingLatency` on a write **resets it to 0** rather than preserving it. So
always emit all three deliberately, at the baselines below. This is the **opposite** of `elevenLabsSettings`,
where an omitted knob simply lets the provider's own default apply.

| Field | Recommendation |
|---|---|
| `stability` | **0.3 baseline** (a single hardcoded constant, not derived from the voice). 0.30–0.50 = dynamic but may sound unstable; 0.60–0.85 = consistent but can go monotone. Raise to 0.7–0.8 for non-English agents or pitch drift. Too low → mispronunciations. |
| `similarity` | **0.7 baseline.** Raise to ~0.8 to fix mumbling; very high distorts + adds latency. |
| `temperature` | **0.5 baseline.** Highly structured/deterministic flows may go lower (~0.1–0.3); up to **0.7** for a deliberately conversational agent. **Above 0.7 the validator warns:** phrasing drifts and instruction-following degrades, which shows up first on the steps that matter (transfers, data capture). |
| `optimizeStreamingLatency` | **2 baseline** for realtime. **Never 4** — level 4 disables the TTS text normalizer (numbers/dates mispronounced; defeats §7c). |
| `elevenLabsSettings.turnEagerness` | `normal` default. `patient` for **data-collection/forms** (numbers/emails/spelling) so the agent doesn't cut callers off; `eager` for **snappy Q&A** / short-turn support. |
| `elevenLabsSettings.speculativeTurn` | Cuts perceived latency; costs extra LLM tokens (discarded when the caller keeps talking) and carries a **small risk on interruption-heavy calls**. Leave unset to accept the provider default. |
| `elevenLabsSettings.asrKeywords` | Niche brand/product/person names the STT mishears. Short terms (~50 keyterms ≤20 chars). Pair with the canonical-name list in the prompt (§7c). |
| `elevenLabsSettings.turnModel` | `turn_v3` is safe through the platform (the ASR model is pinned for you); it is also the provider's own default. |
| `elevenLabsSettings.vad` | `vad.background_voice_detection` — filters background **voices** (TV, bystanders). Enable for consumer/home calls; leave unset for quiet office. |
| `elevenLabsSettings.interruptionIgnoreTerms` | Short caller acknowledgements/backchannel (in the caller's language) that shouldn't cut the agent off mid-sentence. Use when the agent gives longer explanations and callers tend to interject brief affirmations. |
| `elevenLabsSettings.interruptionIgnoreTermLanguages` | The languages the ignore-terms are matched in — set alongside `interruptionIgnoreTerms`, especially on multilingual agents. |
| `elevenLabsSettings.backgroundSound` | Ambient bed under the agent (`preset` required when present; `volume` 0–1; `crossfadeLoop`). Use only when a subtle environment adds realism; keep `volume` low (~0.1–0.3) so it never masks speech. Omit for a clean line. |

### 7b. Model, provider & latency

How the platform picks provider and model, and what a "trivial" agent costs you. **When** to overrule
those picks — and what each override costs — is §9.

- **Model floor — and the V3 trap** (`schema.md` §5): a **trivial** ElevenLabs agent auto-defaults to
  lightweight `qwen - qwen36-35b-a3b` ("trivial" = no KB, no secondary langs, <1 tool, <3 transfer
  rules, <3 scenarios, goalPrompt < 1500 chars). The **tool count sums enabled `skills.custom` entries and
  scenarios with `action == "toolCall"`** — either kind on its own counts toward "≥1 custom tool". A small
  agent doing real work (transfers, data
  capture) can silently land on Qwen. To **guarantee** Haiku on a small but important agent, set
  `llmOverride: "anthropic - claude-haiku-4-5"`. Small/nano-class models fail
  at transfers/tools/name-capture. Don't downgrade for cost.
- **Provider fit** (V3): language-based — plain langs → ElevenLabs; Deepgram-exclusive codes →
  Deepgram; `secondaryLanguages` → ElevenLabs. KB no longer forces ElevenLabs. Generally omit
  `providerOverride`; override only to force Deepgram on a plain language (redundant on a
  Deepgram-exclusive code). **Multilingual exception:** whenever `secondaryLanguages` is set, **always
  emit `providerOverride: "elevenlabs"`**. Multilingual requires ElevenLabs, and pinning it stops an
  edited/re-saved agent whose stored provider is Deepgram from preserving it and failing the save with
  *"deepgram does not support multilingual configurations"*. There are **two distinct multilingual
  mechanisms**: ElevenLabs via `secondaryLanguages` (the default for any multilingual agent), and Deepgram
  via the single language code `multi` (Deepgram-only, which switches its listen model to `nova-3`).
  **Never auto-route a multilingual request to Deepgram** — emit `multi` only when the user explicitly asks
  for Deepgram multilingual, and then pin `providerOverride: "deepgram"`. Deepgram + `secondaryLanguages`
  is rejected at save (schema §4.3/§5).
- **Latency levers** (by impact): shorten `goalPrompt`; instruct **short sentences, especially the
  first of each turn**; convert small KBs to skills; only then a smaller LLM. 1–2 s/turn normal,
  < 3 s acceptable — don't promise less.

### 7c. Speech & TTS formatting (put in `goalPrompt` style guardrails)

- Numbers as **words**; phone/order/reference numbers in **3–4 digit blocks**.
- Dates/times in **word form in the agent's language**; spell abbreviations as letters.
- The platform **auto-injects current date/time (UTC)** — don't add timezone arithmetic; state the
  business's timezone as a plain fact if local time matters.
- For niche names the STT mishears: include a **canonical-name list** in the prompt and, on
  ElevenLabs, mirror in `asrKeywords`. On **Deepgram** the prompt list is the *only* lever.
- Barge-in is **not prompt-controllable** (platform turn-taking); the prompt can only tell the agent
  to yield gracefully when interrupted.

---

## 8. Generation self-check (condensed)

Run a generated config against this before presenting it:

| # | Check |
|---|---|
| 1 | `goalPrompt` covers all 5 components (identity, style, response guidelines, task flow, ending) |
| 1b | Task flow asks **one question per turn** with explicit decision criteria |
| 2 | Custom skills in the recommended **2–4** band (6 tolerated, validator warns above 6); none < 50 or > 2000 words; no knowledge-source URLs in skills |
| 3 | Factual content > ~500 words moved to KB (referenced; user told to create) |
| 4 | Every `extractData` property atomic; active collection instructed, not assumed |
| 5 | `answerQuestions` doesn't auto-transfer without KB/skills to try first |
| 6 | `takeMessage` not enabled on outbound |
| 7 | Transfer conditions specific, **< 120 chars**, no "anything/everything"; each **enabled** direct target carries **both** its id and extension, or the skill ships `enabled: false` as a draft — a scaffolded group rule with the id/extension **omitted** (never blanked to `""`), or `rules: []` — with the prompt offering a **callback** instead of a handoff (§3.4) |
| 8 | Hangup scenarios present with an **explicit `action: "hangup"` and `enabled: true`** (an omitted action is a plain reply, and a switched-off scenario grants nothing): normal end + silence (+ voicemail if outbound) |
| 9 | All `reply` fields literal spoken text **and all scenario/guardrail `when` conditions** in the agent's `language` (no `Say:"…"`, no English `when`/`reply` in non-English agents, no `"."`/`"Nothing"`) |
| 10 | No behavior owned twice (greeting duplication, silence handling, conflicting rules) |
| 11 | No call-start scenario competing with `greeting` |
| 12 | `maxCallDuration` set with generous headroom (hard cap that truncates the call): ~10–15 min outbound / ~20–30 min inbound; never omit (the dashboard fills 30) (§4.4) |
| 13 | Outbound: `startSpeakingFirst: true` + non-empty identifying `greeting` |
| 14 | Single consistent business identity throughout |
| 15 | All prompt/reply text **and `when` conditions** in the configured `language` (re-read each one; don't assume) |
| 16 | No nano/lite-class LLM on agents with transfers/tools/booking/data capture (§7b) |
| 17 | Speech formatting rules present (numbers as words, digit blocks, dates in words — §7c) |
| 18 | No conditional logic or negative meta-instructions in any `reply` |
| 19 | Grounding instruction present; injected `{{variables}}` declared as facts |
| 20 | No IVR-navigation or silence-timer instructions (not supported) |
| 21 | Numeric settings per §7a-bis (esp. `optimizeStreamingLatency` ≠ 4; `temperature` 0.5 baseline — ~0.1–0.3 for highly structured flows, never above 0.7; `turnEagerness: patient` for data collection) |
| 22 | Custom-tool prompts follow when/params(+format example)/usage/error-handling; confirmation before irreversible actions |
| 23 | **Self-contained unless a `reference` was explicitly requested**; outbound number completed — `defaultOutboundNumberId` defaults to `1` (Automatic, as the dashboard seeds it) with a real owned `failoverOutboundNumberId` in both directions, or a real owned `defaultOutboundNumberId` set directly (reused, fetched, or asked). Never guessed, never `2`, never `null`; a bare `1` with no failover `400`s (`generator-contract.md`) |
| 24 | `greeting` names the **real business** — **ask** for the name (it is ground truth, never coined from the use case); a clearly-marked `[placeholder]` is allowed **only** when the user explicitly wants a template. Reads like a person would say it — never a nameless/awkward opener (§6) |
| 25 | **Prose coherence:** every prose field (`greeting`, `goalPrompt`, skills, replies) re-read in the target language — grammatical, complete, no garbled or truncated text |
| 26 | `extractData` properties **presented to the user with a one-line rationale** and open to edit — not silently embedded (§3.1) |
| 27 | **Save-ready:** schema-only JSON — no `_requiredResources`, no placeholder/sentinel IDs, no forbidden fields — saves cleanly **and** runs as-is, reusing the agent's existing setup (`generator-contract.md`) |
| 28 | **Outbound `startSpeakingFirst` is a deliberate choice**, not a leftover default: `true` with a concrete identifying `greeting`, unless the user asked for an agent that waits (§6) |
| 29 | `tone`/`verbosity` emitted **only when the use case wants a non-default**, every label from the closed set — otherwise the keys are absent and the platform default applies (§2.1) |
| 30 | `dialTime` (outbound only) is `0` or **≤ 90 s** — 91–120 passes validation but the call is refused when it's dispatched (§9) |
| 31 | **Connected:** the document being saved was **round-tripped from `cloudtalk_get_voice_agent`** — not assembled from the conversation — with `knowledgeBaseIds` and `elevenLabsSettings` carried forward (`generator-contract.md`) |

---

## 9. Overriding the platform's choices

Provider, model, and most speech-side tuning are **chosen for you** from `language` and the shape of the
agent (§7b). The fields below exist to overrule those choices. Emit one **only when you can name the
reason** — an override outlives the condition that motivated it, survives every later edit, and never
re-evaluates itself. Silence (an omitted key) is a real answer here, and usually the right one.

### `llmOverride` — pin a stronger model

- **When:** the agent looks small to the automatic selector but does **real work** — live transfers,
  careful data capture (names, phone numbers, spellings), custom tool calls, booking. Those are exactly
  the steps a lightweight auto-pick fumbles (§7b), and nothing warns you at save time.
- **Safe values:** canonical model IDs only (`schema.md` §4.2), and the model **must be offered by the
  resolved provider** — a mismatch is refused at save, so decide the provider first (§7b).
  `anthropic - claude-haiku-4-5` is the general-purpose pin for a small-but-important agent.
- **Consequences:** more cost per minute and more latency per turn than the lightweight default, bought
  in exchange for instruction-following that holds under pressure. The trade only runs one way — **don't
  pin downward** to save money on an agent that transfers calls or captures data.

### `providerOverride` — required pins only

- **When:** two cases, both dictated by language, not preference.
  - **`secondaryLanguages` set ⇒ always pin `elevenlabs`.** Multilingual exists only there, and the pin
    also stops a re-saved agent whose stored provider is Deepgram from failing the save.
  - **A Deepgram-exclusive locale code ⇒ `deepgram`.** Automatic selection already lands there, so the
    pin is redundant unless you want the provider frozen against a later language edit.
- **Never pin `deepgram` on an agent with `secondaryLanguages`** — the combination is rejected outright.
- **Validate locally before saving:** an invalid `providerOverride` fails the save **without naming the
  field** — the bundled validator is what points at it.
- **Consequences:** the provider decides **which voices exist** and **which languages are available**. A
  pin that contradicts the `voice` or the `language` you also emitted fails at save; a pin that quietly
  disagrees with the use case (Deepgram on an agent that later needs a second language) fails at the
  next edit.
- Otherwise **omit it** and let the language decide.

### The outbound number pair — connected mode only

- `defaultOutboundNumberId` / `failoverOutboundNumberId` stay environment-tier: carry the agent's real
  values. When connected, changing them is legitimate **only** to an id read from
  `cloudtalk_list_numbers` — pick by label/E.164 with the user, never by guessing. `1` stays the only
  magic value (Automatic).
- **Consequences:** the default outbound number is the caller ID real callees see, and the failover is
  what Automatic falls back to — a wrong edit here breaks live dialing, which is why these two were the
  most dangerous fields to touch before account reads existed.

### `dialTime` — the outbound ring timeout

- **Outbound only** — how long the callee's phone rings before the attempt is given up. It has no
  meaning on an inbound agent.
- **Safe values:** `0` = the provider's own default; otherwise `5`–`120` seconds. Values **above 90 pass
  validation but are rejected when the call is dispatched**, so treat **≤ 90** as the real ceiling.
  20–40 s suits most campaigns; long rings mostly buy voicemail.
- **Omitted preserves the stored value** on an update — so leaving the key out is the correct way to keep
  an agent's current ring timeout, not an oversight.

### `elevenLabsSettings` — speech-side tuning

Meaningful **only when the resolved provider is ElevenLabs**. On Deepgram the object is stored and
**silently inert** — it is never a substitute for fixing the prompt. Two mechanics to keep straight on an
update: an **omitted** `elevenLabsSettings` **preserves** the stored object, while a **present** one
**replaces it wholesale**. So to change one knob, send back the whole object with that one knob changed —
a one-key object silently drops every other setting the agent had. Values: §7a-bis. Shapes: `schema.md`
§10.

| Reach for it when | Knob |
|---|---|
| Turn-taking is wrong — the agent cuts callers off, or waits too long before replying | `turnEagerness`, `turnModel`, `speculativeTurn` |
| The line is noisy — TV, bystanders, a household in the background | `vad` |
| The transcription mangles brand, product, or person names | `asrKeywords` (mirror the canonical-name list in the prompt, §7c) |
| Callers interject short acknowledgements that cut the agent off mid-sentence | `interruptionIgnoreTerms` **with** `interruptionIgnoreTermLanguages` |
| A subtle ambience adds realism | `backgroundSound`: `preset` (required whenever the object is present) + `volume` `0`–`1` kept low + `crossfadeLoop` |

**Off-limits:** streaming-latency level **4**. It disables the TTS text normalizer, so numbers, dates,
and abbreviations get mispronounced and the §7c speech-formatting rules stop working. Stay at the baseline 2.

### Disabled drafts — a deliberate shape, not an unfinished one

A skill may ship `enabled: false` as a **staged draft**: the behavior is authored, the wiring isn't
available yet, and the dashboard shows the user the one field it still needs. Two canonical drafts:

- **`transferToHuman`** — ship it `enabled: false`. The default draft **scaffolds the group**: a rule with
  `destination: "group"` and the id/extension keys **omitted** (`groupId`/`groupExtension` absent), so the
  group intent is visible and the user completes it in the dashboard (a group's extension can't be read
  programmatically); `rules: []` is the alternative when no group is in mind (§3.4). `agentId`/`groupId` are
  integers, so **omit them on a draft — never blank one to `""`**, which is an INVALID_TYPE the save rejects
  even while the skill is off. Keep the prompt honest while it is off: the agent offers a **callback**, never
  a handoff it can't perform. (Note that `appointmentBooking` below is the opposite case — its `integrationId`
  and `calendarId` are string fields, so an empty string is the right *not-chosen-yet* draft value there.)
- **`appointmentBooking`** — disabled, with the non-ID fields authored (`eventName`, `durationMinutes`,
  the descriptions) while `integrationId` and `calendarId` stay **empty strings** until a calendar is
  connected. Keep required keys **present with an empty value rather than absent**: an empty string reads
  as *not chosen yet* and saves cleanly, while dropping a required key is what breaks an import (the same
  rule as `enabled` — `generator-contract.md`). On a **switched-off** skill those empty IDs are a noted
  gap, not an error; the moment it is enabled they become required.

Draft minimums the platform requires even when disabled: every skill object carries `enabled`;
`transferToHuman` also needs its `rules` key (`[]`, or a scaffolded rule with the id/extension omitted, is
the draft shape); `answerQuestions` also needs `action` — pick `admitUncertainty`/`offerAlternative` for a
draft, or scaffold `transferToHuman` with the id/extension omitted, since a live `transferConfig` demands a
real target;
the remaining per-skill required keys are marked in `fields.json`.

The principle: **grounding is an enable-time obligation, not a write-time one.** A behavior you can't
ground yet is worth shipping switched off, because the user can finish it in one click. A *live* skill
pointing at an ID you invented is the opposite — it looks finished and fails on a real call.

### The safety floor

Underneath every agent the platform maintains its own **safety and style baseline** — the constraints
that hold whatever a config says. `tone`, `verbosity`, and your `goalPrompt` style guardrails shape
**delivery on top of** that floor; they do not replace it, relax it, or switch it off. Don't write prompt
text that tries to, and don't promise a user behavior that would require it.
