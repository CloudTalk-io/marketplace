# Voice Agent v2 — template variables (`{{…}}`)

The consolidated reference for every `{{variable}}` the platform resolves in a voice-agent config — what each contains, when it resolves, and what an unset one does.

One template engine resolves variables **at call time** over the config's prompt text — `goalPrompt`,
`greeting`, and the scenario lines assembled into the same system prompt (behavioral §1) — and
over `sendSms` message bodies. An **unset or unknown variable renders as an empty string, silently** — no
error, no visible braces: a typo'd variable never fails, it just vanishes.

## The resolvable sets

| Variable | Resolves when | Contains | If unset |
|---|---|---|---|
| `{{contact.*}}` — `{{contact.name}}`, `{{contact.company}}`, emails, …; `{{contact.custom.<title>}}` | the call has a matching CRM contact | the contact's CRM fields; `custom.<title>` reads a custom field by its title | empty string — a field the contact doesn't carry (or a mistyped `<title>`) vanishes |
| `{{caller_number}}` | at call time | the caller's number | empty string, like any unresolved variable |
| `{{appointment.event_name}}` · `{{appointment.service_description}}` · `{{appointment.duration_minutes}}` | from config — as soon as the `appointmentBooking` skill defines them, before any booking | the skill's `eventName` / `serviceDescription` / `durationMinutes` | empty string — e.g. `service_description` when that optional config field wasn't set |
| `{{appointment.start}}` · `{{appointment.start_pretty}}` · `{{appointment.end}}` · `{{appointment.event_id}}` · `{{appointment.caller_name}}` · `{{appointment.reason}}` | once a booking **succeeds in-call** (the `booking_confirmed` trigger context) | the confirmed booking: start/end (`start_pretty` is the human-readable start), event id, the caller's name and stated reason | empty string until a booking succeeds — don't use these outside a post-booking context |
| user-declared call-property variables — any `{{key}}` you declare | the outbound call's trigger (a campaign, the public API, or a Call Flow) passes a `call_properties` key with the **exact same name** | whatever value the trigger supplied (callee name, order number, …) | empty string — declared but not wired leaves a silently broken line (`calling about ` with nothing after) |

## Authoring rules

- **Only emit a variable something in the config actually wires.** The platform families above resolve on
  their own; a user-declared variable resolves **only** when the trigger passes a matching
  `call_properties` key — declared + wired is fine, undeclared is an empty string. Say plainly in your
  reply that the trigger must supply the values: the config alone cannot.
- **Declare injected facts in a dedicated facts section of `goalPrompt`** (behavioral §2.2, §6).
  Substitution happens before the agent reads the prompt, and an unset variable collapses silently — it
  never surfaces as braces or as a cue for the agent to ask. The facts section is what gives the resolved
  value a role the agent can act on.
- **Never invent a `{{placeholder}}`** hoping the platform fills it — it renders as an empty string and
  corrupts the line it sits in.
- **Any URL must be user-supplied and copied verbatim.** There is **no booking/calendar-link variable** —
  the runtime discards the calendar's event link. To text a booking link or confirmation, the two real
  paths: a `triggerType: "booking_confirmed"` + `sendSms` scenario carrying `{{appointment.*}}` fields
  (needs a company-owned SMS sender — [`referenced-resources.md`](./referenced-resources.md)), or a
  **static user-provided URL** pasted verbatim (behavioral §6; schema §7.1).
- **Current date/time is not a variable.** The platform auto-injects it (UTC) as prompt text — nothing to
  write, and no timezone arithmetic to add (behavioral §7c).
- **A custom tool's `{{param}}` is a different mechanism.** A tool's URL or header value may embed
  `{{param}}` placeholders, filled from that tool's **own declared parameters** when the agent invokes it
  ([`mcp-tools.md`](./mcp-tools.md)) — they are not the call-time variables in the table above, and the two
  name spaces do not mix.
