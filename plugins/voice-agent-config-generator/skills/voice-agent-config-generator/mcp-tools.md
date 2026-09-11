# Voice Agent v2 — connected mode (CloudTalk MCP tools)

> Semantics last verified against the MCP server source and live gateway: **2026-09-02**.

The connected-mode reference: the 20 tools the CloudTalk MCP's voice-agents profile exposes for reading real IDs, saving configs, and placing test calls — plus the write-safety rules and what still needs the Dashboard.

**Connected mode** is this skill working against your CloudTalk account directly, through the CloudTalk
MCP (voice-agents profile at `https://mcp.cloudtalk.io/voice-agents`; HTTP Basic auth with your company's
API keys — Dashboard → Account → Settings → API keys). Connection setup is documented in the **repo
README** — not here. **Offline mode always works:** without the MCP, you paste the generated JSON into
the dashboard's Expert Mode and copy IDs from the Dashboard
([`referenced-resources.md`](./referenced-resources.md)).

> **Never ask the user to paste their API key into the chat.** The key reaches the MCP through the
> plugin's `userConfig` prompt (masked) and lives in the OS keychain — never in a chat message or a
> settings file. If the MCP isn't connected, point the user to that prompt (or their own
> `claude mcp add` server) rather than collecting the key here.

## The tool surface

### Authoring

| Tool | Purpose | Key caveat |
|---|---|---|
| `cloudtalk_list_voice_agents` | List the company's voice agents (id, name, direction) | **Pages** (see *Reading lists*) and cached a few minutes — a just-created agent can be missing; see *Write safety* |
| `cloudtalk_get_voice_agent` | Fetch one agent's **complete config document** | The mandatory first step of every update — and the way to read a real, working `voice` ID. It does **not** pre-validate the 24-hex shape, so a numeric id fails upstream rather than at dispatch (`trigger_aiva_call` does check) |
| `cloudtalk_create_voice_agent` | Create an agent from a config | Write — confirm-gated; the result carries the new `id`, a `dashboard_url`, and possibly `error_codes` (*Write safety*) |
| `cloudtalk_update_voice_agent` | Save a config to an existing agent (`voice_agent_id`) | Write — **full-document replace**; see Write safety |
| `cloudtalk_list_knowledge_bases` | List KBs: id, name, `description`, type (`CUSTOM`/`URL`/`FILE`), status, attached agents | Link only `ACTIVE` KBs. **Pages**, and cached ~5 min — so a `SYNCHRONIZING` → `ACTIVE` flip can show up a cache TTL late |
| `cloudtalk_create_knowledge_base` | Create a KB: `custom` (you supply the text, `ACTIVE` at once) or `url` (ingested asynchronously, starts `SYNCHRONIZING`) | Write — name ≤ 50 chars; **text is frozen after creation**; **`description` is unsettable on create** — there is no input field for it, though the create response and the list read both carry it; file KBs are Dashboard-only |
| `cloudtalk_list_voice_agent_tools` | List custom tools, optionally filtered to one agent | **Never returns header/param values** — secrets go in, never come back out. **Pages** |
| `cloudtalk_create_voice_agent_tool` | Create a custom HTTP tool, optionally **attached** to agents in the same call | Write — name ≤ 64 (alnum + `-_`); method `GET/POST/PUT/DELETE/PATCH`; the URL may embed `{{param}}`; `awaiting_response_message` ≤ 4096; headers `CONST`\|`SECRET`; query/body params `CONST`\|`PARAM`\|`LLM`, each with a data type; **`voice_agent_config_ids`** attaches the new tool to those agents on create |
| `cloudtalk_update_voice_agent_tool` | Edit a custom tool | Write — **partial via read-modify-write**: the MCP fetches the tool, merges your fields, and sends a full replace upstream. **Omit** a key to preserve it; an explicit `[]` **clears** that list; **never send `null`** — the MCP rejects a null argument before the handler ever runs, so it preserves nothing. No version precondition upstream, so a concurrent Dashboard edit in that window is lost — re-read before editing a tool someone else is touching |
| `cloudtalk_assign_tool_to_voice_agent` | Attach a tool that **already exists** to an agent | Write — idempotent; an assign that changes nothing is a no-op and needs no confirmation (with the matching unassign no-op, the single exception to *Every write is confirm-gated* under Write safety). For a brand-new tool, prefer `voice_agent_config_ids` on create |
| `cloudtalk_unassign_tool_from_voice_agent` | Detach a tool from an agent | Write — idempotent; an unassign that changes nothing is the same no-op exception as assign. Other agents keep the tool |
| `cloudtalk_trigger_aiva_call` | Have an agent call a number: `voice_agent_id` (the **24-hex config id**) + `call_number` | Write — **places a real outbound phone call**. `call_number` is strict E.164: a leading `+` then digits only, no spaces or separators. The result carries a `session_id` — the correlation key for that attempt. See Test calls |

### Call reads

Read-only — useful for verifying behavior after a test call.

| Tool | Purpose | Key caveat |
|---|---|---|
| `cloudtalk_search_calls` | Find the call — this is where a test call's numeric `call_id` comes from. Its **`voice_agent_id` filter (the NUMERIC id — see *Two ids*) is the way to list one agent's calls** | **External calls only** (internal legs never appear). The window defaults to about the last 3 months and a **wider span is rejected, not silently shortened** — narrow it and repeat instead. Pagination depth is bounded, so filter rather than walking pages, and `items_count`/`page_count` are reported **on page 1 only** (they come back null on deeper pages). `country_code` here is **ISO-2** (`SK`), unlike `cloudtalk_list_numbers`. A just-ended call may need a moment to appear |
| `cloudtalk_get_call_transcript` | One call's verbatim transcript: time-coded segments, speaker, detected language | Needs the numeric `call_id` from `cloudtalk_search_calls`; page long calls with `limit`/`offset` |
| `cloudtalk_get_call_insights` | One call's post-call signals: summary, sentiment, topics, smart notes, talk-listen ratio | Same numeric `call_id`; slower than a transcript — use `include` to ask for only what you need. Legal `include` values: `summary`, `sentiment`, `topics`, `smart_notes`, `talk_listen` |

### Account reads

| Tool | Purpose | Key caveat |
|---|---|---|
| `cloudtalk_health_check` | Confirm the MCP is reachable and see which company/user the key resolved to | Run it first when a tool fails — it separates an auth/tenant problem from a data problem. Makes **no** API call of its own, so it proves the credential was accepted, not that an upstream is healthy. **Check the echoed company id is the account you meant** — and the **`role_id`**: a non-admin key can still `cloudtalk_list_voice_agents`, but fails the other config reads (`get_voice_agent`, `list_knowledge_bases`, `list_voice_agent_tools`) **and every write** with an authorization error, which is the first thing to check when one list works and nothing else does. The response also carries **`rollout_enabled`**, which tells a *tenant not enabled for MCP* 403 apart from an auth/role problem |
| `cloudtalk_list_agents` | Human agents: id, name, email, **extension**, availability | Both halves of an `agent` transfer pair come from here. Still prefer groups as targets (behavioral §3.4) |
| `cloudtalk_list_groups` | Ring groups — the preferred transfer targets | Returns **id + name only**. The `groupExtension` half is **not** in this response — take it from the Dashboard, the user, or the agent's current config |
| `cloudtalk_list_numbers` | Company numbers: id, country/area code, name, E.164, per-channel support flags | Resolves outbound-number IDs **and** SMS senders (`sms_supported: true`). `country_code` here is the **numeric calling code** (`421`), not the ISO-2 code `cloudtalk_search_calls` wants |
| `cloudtalk_list_contact_tags` | Contact tags in the account | An always-on account lookup — no voice-agent config field references a contact tag. **Pages** |

## Reading lists

- **The AIVA list reads page.** The three voice-agent-domain lists — voice agents, knowledge bases,
  custom tools — take a `limit` (**default 50**, ceiling **200**) and return `pagination.next_page`
  when more rows exist. Check any list result for that field before treating it as complete.
- **The account reads page on different numbers.** Agents, groups, numbers and contact tags default to
  **200** with a ceiling of **1000**, and return `pagination.next_page` the same way.
- **`limit` trims the response, not the upstream cost.** The page is fetched either way, so a small
  `limit` saves you context, not rate budget — narrow with a filter when the budget is what's tight.
- **Follow `next_page` before concluding something doesn't exist.** Real accounts hold more than 50
  voice agents, so "not in the list" from page one means nothing — page through, or filter.
- The call reads page differently: `cloudtalk_get_call_transcript` uses `limit`/`offset`, and
  `cloudtalk_search_calls` has a **bounded** pagination depth (narrow the filter instead of walking).

## Two ids, one name

A voice agent has **two** identifiers, and a write response carries both:

| In the response | Shape | Used by |
|---|---|---|
| `id` | 24-hex string | `cloudtalk_get_voice_agent`, `cloudtalk_update_voice_agent`, `cloudtalk_trigger_aiva_call` (`voice_agent_id`) |
| `voice_agent.voice_agent_id` | number | `cloudtalk_search_calls` (`voice_agent_id`) — the call-record side |

Same name at the call boundary, different type. Passing the 24-hex config id to `search_calls`, or the
numeric one to `get`/`update`/`trigger`, fails or returns nothing — take each from the write's own result
rather than guessing which one you are holding.

**The key name does not tell you which id you hold.** `cloudtalk_list_voice_agents` returns the **24-hex**
id under the key name `voice_agent_id`, so a value read from a list is the config id whatever it is
called. Only the get and write responses carry the numeric one, and there it is `voice_agent.voice_agent_id`.

## Write safety

- **Every write is confirm-gated** (one no-op exception below). Called without confirmation, a write
  returns `status: "confirmation_required"` **plus a preview of what would change — as a successful
  result**, not an error. Present that preview to the user and wait for their decision; **never
  self-approve** or re-invoke with confirmation on your own. *The one no-op exception:* an `assign` or an
  `unassign` that changes nothing is idempotent and needs no confirmation.
- **Never send `null` for any argument.** The MCP rejects a null argument before the handler sees it, on
  every tool — omit the argument instead of passing null.
- **Updates replace the full document.** `cloudtalk_update_voice_agent` **replaces the document you
  send** — with the per-field exceptions below, since the server's own contract preserves some omitted
  system and Expert-Mode fields. Always **get → modify → update**; never compose an update from memory
  or a stale copy.
- **Both config writes demand the full set of required scalars.** `agentName`, `direction`,
  `defaultOutboundNumberId`, `language`, `maxCallDuration`, `temperature`, `voice`, `stability`,
  `similarity`, `startSpeakingFirst` and `goalPrompt` — plus `voice_agent_id` on the update. A partial
  payload comes back as *missing required*, never as a merge onto what is stored.
- **Omission is not neutral, and not uniform** — one habit covers all three cases: send back the document
  `cloudtalk_get_voice_agent` gave you, modified.
  - `knowledgeBaseIds` **omitted = every KB unlinked** — carry the current list through each update.
  - `elevenLabsSettings` omitted = stored settings **preserved**; present = **replaced wholesale** —
    when connected, edit individual sub-fields on the fetched object rather than authoring the
    container fresh.
  - `dialTime` omitted = stored value **preserved**.
  - `optimizeStreamingLatency` omitted = **reset to `0`**, not preserved — carry it forward.
- **On the two config writes, fields beyond the declared list are forwarded, not dropped.**
  `cloudtalk_create_voice_agent` and `cloudtalk_update_voice_agent` name the common fields but pass the
  whole document through, so an Expert-Mode key their schema doesn't list still reaches the server —
  emit the config you'd paste into Expert Mode. The other six profile writes are the opposite: they
  reject an unknown argument outright and answer with the list of accepted ones.
- **Every *declared* field is enforced at the MCP layer** — enums, the `0`–`1` ranges, types, and the
  null rejection above — so a bad value there is a tool error (`invalid_args`) before the platform ever
  sees it, not a save error. `tone` and `verbosity` are simply the newest declared enums, not a special
  case. Only *undeclared* Expert-Mode keys pass through unchecked: a valid-but-undeclared v2 field is
  honored by the platform, while a truly unknown or misspelled key is **silently dropped by the save**
  (only `/validate` and the bundled validator flag it) — so run the validator to catch a typo the save
  would swallow.
- **The save is the platform's verdict.** There is no separate validate tool: run the bundled validator
  first (below), then let the confirmed write return the server's answer.
- **Read what a successful write returns.** Three writes carry a **`dashboard_url`** — create and update
  voice agent, and create knowledge base: hand that link to the user instead of describing where to
  click. The tool and assignment writes and `cloudtalk_trigger_aiva_call` return none, so don't promise a
  link there. A voice-agent write can also carry **`voice_agent.error_codes[]`** *on a save that
  succeeded*: a stored-but-degraded reference (an unusable voice, a number the company can't send from).
  Surface those in plain language — **saved is not clean**.
- **Propagation lag is minutes, not seconds.** The list reads are cached (voice agents and KBs a few
  minutes, numbers and groups longer) and a create **does not** clear that cache — so **wire the id the
  write itself returned** instead of re-listing to find it. A missing row right after a create is not a
  failed write. (Custom tools are the exception: tool creates, tool updates, and assign/unassign all
  clear the tool list cache.)
- **Wire the *right* id.** The write returns both a 24-hex `id` and a numeric
  `voice_agent.voice_agent_id` — see *Two ids, one name* above for which tool takes which.
- **Parse results tolerantly.** Results have no output schema, so shapes can vary — and a
  successful-looking result carrying a `"validation_failed"` status **is a failure**: read the status,
  not just the transport-level success.

## Not available via MCP (yet)

| Need | Workaround |
|---|---|
| Validate a config before saving | Run the bundled [`scripts/validate_config.py`](./scripts/validate_config.py) **before every save** — there is no validate tool |
| Voice / LLM / language catalogs | Reuse the `voice` from `cloudtalk_get_voice_agent` (this agent's, or another agent's), or the documented premade defaults (`schema.md` §4.4) |
| Edit a KB's content | Create a **replacement KB** and re-link the agent; the old KB remains — clean it up in the Dashboard |
| Delete a KB or a custom tool | Dashboard only |
| Clone an agent | `get` → `create`; decide deliberately whether `knowledgeBaseIds` carry over — and **tool assignments do not copy**: re-assign them |
| Inbound number routing (which number an agent answers) | Dashboard only |
| A ring group's **extension** | `cloudtalk_list_groups` gives the id and name only — take `groupExtension` from the Dashboard, the user, or the agent's current config, or ship the transfer skill switched off ([`referenced-resources.md`](./referenced-resources.md)) |
| Read calendar integrations | No MCP read — `appointmentBooking` stays ask/omit + **disabled draft** until the user wires real IDs from the Dashboard ([`referenced-resources.md`](./referenced-resources.md)) |

## Test calls

`cloudtalk_trigger_aiva_call` places a **real outbound phone call** from the agent to the number you pass
— it is confirm-gated like every write, and the destination must be a number the **user names**
(typically their own phone), never one picked from a list. For an **inbound** agent, the test is the
other way around: the user calls the agent's assigned number.

Its two parameters: `voice_agent_id` — the **24-hex config id** (`cloudtalk_get_voice_agent`'s `id`, not
the numeric CDR one) — and `call_number`, strict **E.164**: a leading `+` then digits only, no spaces,
dashes or parentheses. The result carries a **`session_id`**, the correlation key for that call attempt;
keep it when reporting back. To find the call afterwards, `cloudtalk_search_calls` filtered by the
agent's **numeric** `voice_agent_id` (*Two ids, one name*), then transcript/insights.
