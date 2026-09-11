# Voice Agent v2 — referenced & environment resources (wiring guide)

> **Audience:** anyone finishing a config that references company resources. **This doc owns the "how do
> I make this real" knowledge** — what each `reference` / `environment` field needs, where the resource
> lives, and how to wire its ID: via the **CloudTalk MCP** when connected, or the **Dashboard** when not.
> Field shapes live in [`schema.md`](./schema.md); this doc does not restate them.

## When you need this

A generated config is self-contained: an inbound agent that answers, captures details, and hangs up has
**nothing for you to wire**. You come here when the config touches something that lives in your company —
a knowledge base, a custom tool, a calendar, an SMS sender, a **transfer target** — or when you're editing
in Expert Mode and want to keep the real values the agent already has. In those cases the generator reuses
an ID already on the agent, looks the real one up over the MCP (connected mode), asks you for it and bakes
it in, ships the feature **switched off** (transfers), or omits it and lists the setup step in its chat
reply (see [`generator-contract.md`](./generator-contract.md)). This doc is what those steps point at —
find the resource kind below.

**Every resource kind below has two wiring paths — both end with a real, company-owned ID in the JSON:**

- **Connected** — the CloudTalk MCP is set up: the named tool reads the real ID straight from your
  account, so nothing is guessed or hand-copied. Tool mechanics, write safety, and what the MCP *can't*
  do yet live in [`mcp-tools.md`](./mcp-tools.md).
- **Dashboard** — offline mode: copy the ID out of the CloudTalk Dashboard by hand and paste the finished
  JSON into Expert Mode yourself.

> Realities to know:
> - **Editing your own agent is same-account** — nothing is stripped. The **cross-account** caveat below
>   applies only to a config exported from a *different* account.
> - On a **cross-account** paste (the config's `companyId`/`environmentName` ≠ your account), the dashboard
>   **silently strips** `toolCall` and `sendSms` scenario actions down to plain replies. Those features
>   must be **re-added in the UI** after saving; substituting an ID in the JSON is not enough for them.
> - `knowledgeBaseIds` and the appointment `integrationId`/`calendarId` are **left intact** and **rejected
>   by the platform** if they don't exist in your account. Use real IDs (or remove the feature) before saving.
> - Transfer targets (`agentId`/`agentExtension`, `groupId`/`groupExtension`) are **not checked anywhere** —
>   a wrong one saves fine and fails **during a live call**. See *Direct transfers* below.
> - After saving, if the dashboard errors with **"Failed to update VoiceAgent,"** the config points at a
>   resource not fully provisioned in your company — a deprecated voice, an unowned `sendSms` number, a
>   custom tool missing its ElevenLabs ID, or a provider/language mismatch. **Fix that reference; re-saving
>   won't clear it** (there is no "save twice" fix — a save either takes or names a real problem).

---

## `environment` — outbound phone numbers

`defaultOutboundNumberId`, `failoverOutboundNumberId`.

- **What:** which company-owned phone number the agent calls *from* (outbound). **The only magic value is
  `1` = Automatic** (pick a number in the contact's country, falling back to `failoverOutboundNumberId`).
  **Every other value, including `2`, is a literal phone-number ID your company must own** — the platform
  has no "Random" (a `2` only ever "worked" if a company happened to own number id `2`).
- **It defaults to `1` (Automatic), exactly as the dashboard seeds it — never invent or copy a specific id
  from an example.** With `1` the save is not ready until a real owned `failoverOutboundNumberId` completes
  it (below); setting a real owned `defaultOutboundNumberId` directly — reused from the agent's current
  config, fetched (`cloudtalk_list_numbers`), or asked for — is the alternative. A bare `1` with no failover
  is not save-ready. For an **inbound** agent the outbound number is irrelevant to how it runs, but the field
  is still required, so it still needs either Automatic + a real failover or a real owned id.
- **If you use Automatic (`1`), `failoverOutboundNumberId` is required in BOTH directions** and must be a
  real owned id — the save `400`s without it, nothing self-heals, and `null` is never valid. Omit the
  failover key only when `defaultOutboundNumberId` is a real non-`1` id.
- **The config save stores exactly what you send and does not auto-pick a number.** Whichever path you use,
  keep the agent's current `defaultOutboundNumberId` + `failoverOutboundNumberId` when editing (the editor
  shows both), or set real owned ids before importing. A guessed `2` overwrites a working number and is
  refused **by name**: *"outbound number 2 does not exist or does not belong to the company"* (a `400`, not
  a mystery 500); a bare `1` with no failover `400`s the same way.
- **If you need a specific number:**
  - **Connected:** `cloudtalk_list_numbers` — every company number with its ID, name, country/area code,
    and E.164. Pick the real ID by its label or E.164; never by position or habit.
  - **Dashboard:** copy the number's ID from the numbers list.
- **Portability:** number IDs are environment-specific — never reuse one across companies.
- **Can't be omitted:** `defaultOutboundNumberId` is required and rejected if missing (no preserve-on-omit);
  it carries Automatic (`1`, the default) with a real owned `failoverOutboundNumberId` behind it, or a real
  owned number id set directly.

---

## `reference` — company resources

### Knowledge bases — `knowledgeBaseIds`  *(action: usually create)*

- **What:** documents the agent can consult. A config can only **reference** a KB by ID; it cannot
  create one inline. `type` ∈ `FILE | URL | CUSTOM`.
- **Connected:** `cloudtalk_list_knowledge_bases` (ID, name, type, status, attached agents) to find an
  existing KB; `cloudtalk_create_knowledge_base` to make one — `custom` (you supply the text) or `url`
  (the page is ingested asynchronously). **Wire the ID the create call returns**; the KB list is cached for
  a few minutes, so a brand-new KB may not appear there yet. **KB text cannot be edited after creation:**
  to change it, create a replacement KB and re-link the agent (the old KB remains — clean it up in the
  Dashboard). **File KBs are Dashboard-only.**
- **Dashboard:** create it in the knowledge-base UI (any type, including file uploads).
- **Wire:** copy the KB's ID into `knowledgeBaseIds`.
- **Gotchas:**
  - **Only `ACTIVE` KBs are usable.** A `url` KB starts `SYNCHRONIZING` and stays there until its page
    is ingested — wait for `ACTIVE` before linking it to an agent. A `custom` KB is `ACTIVE` at once.
  - URL-type KBs scrape a **single page** (no link-following, no re-scraping) — one KB entry per page
    that matters.
  - Tiny KBs (≈ a screenful) are better folded into a custom skill (lower latency); content > ~500
    words belongs in a KB. (Behavioral §7.)
  - Under V3 routing a KB does **not** change the provider; it marks the agent "complex", upgrading
    the ElevenLabs auto LLM from Qwen to Haiku 4.5 (`schema.md` §5).

### Custom tools — `scenarios[].toolReferenceId` (with `action: "toolCall"`)  *(action: create)*

- **What:** a user-defined HTTP tool the agent can call mid-conversation. Referenced by ID only;
  cannot be defined inline.
- **Connected:** `cloudtalk_list_voice_agent_tools` to find an existing tool (optionally filtered by
  agent); `cloudtalk_create_voice_agent_tool` to author one — pass `voice_agent_config_ids` and the
  create **attaches the tool to those agents in the same confirm-gated write**, so a new tool is one
  write, not create-then-assign; `cloudtalk_update_voice_agent_tool` to edit one.
  `cloudtalk_assign_tool_to_voice_agent` / `cloudtalk_unassign_tool_from_voice_agent` are for a tool that
  **already exists** — wiring it to another agent, or re-attaching after a clone (tool assignments don't
  copy). Reads **never return header or parameter values** — a secret goes in at create/update time and
  never comes back out.
- **Dashboard:** create it in the tools/secrets UI.
- Either way, the tool's **`description` is what the LLM uses to decide when to invoke it** — write it
  clearly (analogous to a scenario's `when`).
- **Wire:** copy the tool ID into `toolReferenceId`. **Re-add the `toolCall` action in the UI** only if the
  config was pasted cross-account (the dashboard stripped it); editing your own agent leaves it intact.
- **Not to be confused with built-in tools** (below), which need no resource.

### Direct transfers — `transferToHuman.rules[].agentId`/`groupId`, `answerQuestions.transferConfig`  *(action: select)*

- **What:** a live in-call transfer to a specific agent or ring group — the **default** way an agent reaches
  a human.
- **Connected:** `cloudtalk_list_agents` returns each agent's **id and extension** — both halves of an
  `agent` pair, straight from your account. `cloudtalk_list_groups` returns a group's **id and name only**:
  the `groupExtension` half is not in that response, so take it from the Dashboard, from the user, or from
  the agent's current config. Connected mode narrows the guesswork here; for a group it does not remove it.
- **Dashboard:** copy the ID and the extension from the agent's or group's settings.
- **Wire:** a real target needs **both** halves of its pair — `agentId` **+** `agentExtension`, or `groupId`
  **+** `groupExtension`. Half a pair is not a transfer.
- **Prefer `group` over `agent`:** more targets can answer before an attended transfer falls back, and a
  lone unavailable agent is a cold drop for any company not on advanced transfer. Where advanced transfer
  is enabled, a leg that goes busy, declined, timed-out, or dropped is torn down and the AI announces the
  failure and resumes — the caller is not stranded. **Don't switch to an `agent` target just because its
  pair is easier to read** — the group is still the right destination; its extension is one extra lookup,
  not a reason.
- **These values are verified nowhere at save time.** The import forwards them verbatim, ownership is not
  checked, and the runtime dials them raw — so a nonexistent, foreign, or half-set pair on a **live** skill
  **saves fine and fails mid-call**. Where advanced transfer is enabled the AI announces the failure and
  resumes; on a cold fallback the caller is dropped silently. Wire values that came from the MCP lists, the
  Dashboard, or the user — never a guess. On a switched-off draft **OMIT the id/extension keys** — never
  blank an integer id to `""` (`agentId`/`groupId` are integers, so `""` is an INVALID_TYPE the save rejects
  even when the skill is off); and on an enabled rule `""` passes every check *and* gets offered to the agent
  as a working transfer, then dials nothing.
- **When you don't have the target yet:** the generated config ships the skill **switched off** as a draft.
  The default **scaffolds the group** — a rule with `destination: "group"` and the id/extension keys
  **omitted** (`groupId`/`groupExtension` absent), so the intent stays visible and the user completes it;
  `rules: []` is the alternative when no group is in mind. Both save, and the dashboard shows the skill as
  *"Requires configuration"* with a locked toggle: open it, pick the ring group with the real pickers, and
  switch it on. Tell the user in plain terms — *"finish setting up the transfer to your team in the
  dashboard"* — not in DB terms. (Product templates ship the same way.)
- **`destination: "call_flow"`** needs no ID: the agent hangs up and the Call Flow Designer routes next —
  **always a cold hand-off with no resume**. That is only useful when the agent **runs as a step inside a
  Call Flow** — for a standalone agent it just ends the call — so it is used on request, not as a stand-in
  for a missing target.

### Appointment booking — `appointmentBooking.integrationId` / `calendarId`  *(action: create)*

- **What:** lets the agent book against a connected Google Calendar / Outlook integration.
- **Connected:** **no MCP read exists for calendar integrations** — the connection and its IDs live in the
  Dashboard only. Until the integration exists, the config ships the skill as a **disabled draft**
  (`enabled: false`) or omits it, and the setup step goes in the chat checklist. A draft keeps every
  required key **present**: `integrationId` and `calendarId` stay **empty strings**, never absent — an
  empty value reads as *not chosen yet* and saves cleanly, while dropping a required key is what breaks
  the import (behavioral §9).
- **Dashboard:** connect the calendar in the Integrations area (OAuth), then read the integration's ID and
  the target calendar from it. What CloudTalk accesses in a connected calendar is covered in CloudTalk's
  Help Center documentation on calendar integrations.
- **Wire:** use the connected integration's ID in `integrationId` and the target calendar within it in
  `calendarId`. Leave the server-managed fields (`integrationType`,
  `availabilityToolId`, `bookingToolId`, `errorCode`) **out** — the server fills them on save.
- **No customer-facing link or invite:** the booked event lands **only** in the company's connected calendar
  — **no email invite, no attendees, and the event is not added to the customer's calendar.** The runtime
  discards the calendar's event link, so there is **no `{{appointment.link}}`-style variable.** To text the
  customer a confirmation, use a `booking_confirmed` `sendSms` scenario with `{{appointment.*}}` details
  (schema §7.1; [`variables.md`](./variables.md)) — not a per-appointment link.

### Send SMS — `scenarios[].params.senderNumber` (with `action: "sendSms"`)  *(action: select)*

- **What:** the agent sends an SMS mid-call from a company-owned number.
- **Connected:** `cloudtalk_list_numbers` — each number carries per-channel support flags; pick a sender
  with **`sms_supported: true`**. Two separate gates: **the config save checks OWNERSHIP only** (an unowned
  sender is refused at save), while **SMS-capability is a send-time requirement** — an owned-but-not-SMS
  number saves fine, then the actual send fails. So pick an owned *and* SMS-capable number.
- **Dashboard:** pick an SMS-capable number from the numbers list.
- **Wire:** use that number's **E.164** as `senderNumber` (the save rejects an unowned sender; an owned but
  non-SMS number saves but can't actually send). **Re-add the `sendSms` action in the UI** only if pasted
  cross-account (the dashboard stripped it).
- **Message content:** `params.message` is **fixed config text** (the LLM only decides *whether* to send, not
  what it says). It is **templated** — `{{…}}` variables resolve (call-placement vars, `{{caller_number}}`,
  `{{contact.*}}`, `{{appointment.*}}`; [`variables.md`](./variables.md)) and an **unknown variable becomes
  an empty string.** Any URL must be **user-supplied and copied verbatim** — never invented, and there is
  no booking/calendar-link variable.

---

## Built-in tools — no resource needed (reference only for clarity)

These are **auto-provisioned** by the platform from what the config enables — you do **not** create
or wire them; enabling the skill/scenario *is* the activation. They are not `reference` fields.

| Built-in tool | Auto-enabled by | Configured via |
|---|---|---|
| `transfer_to_human` | `transferToHuman` enabled, or `answerQuestions.action == "transferToHuman"` | the skill's `rules` / `transferConfig` |
| `end_call` | a scenario with `action: "hangup"` | the scenario's `when` / `reply` |
| `send_sms` | a scenario with `action: "sendSms"` | the scenario's `params` |
| `check_availability` | `appointmentBooking` enabled | the skill's calendar/event fields |
| `book_appointment` | `appointmentBooking` enabled | the skill's calendar/event fields |

So the config JSON can fully activate `end_call` with **no external resource** — that's the backbone of a
self-contained agent. `transfer_to_human` is the exception: the *tool* needs nothing, but pointing it at a
person needs a real agent/group id + extension (or a Call Flow around the agent), which is why an
unfinished transfer ships switched off.
