# VoiceAgent v2 — connected mode (CloudTalk MCP tools)

> Semantics last verified against the MCP server source: **2026-10-27**, for production and for the release in which every write acts on its first call.

The connected-mode reference: the 20 voice agent tools the CloudTalk MCP exposes for reading real IDs, saving configs, and placing test calls — plus the write-safety rules and what still needs the Dashboard.

**Connected mode** is this skill working against your CloudTalk account directly, through the CloudTalk
MCP. The plugin connects by CloudTalk sign-in (OAuth) at `https://mcp.cloudtalk.io`, which carries every
CloudTalk tool: the user signs in with CloudTalk in the app's connector settings. Anyone who wants an API
key connection instead adds the voice-agents profile server themselves, as the repo README shows:
`https://mcp.cloudtalk.io/voice-agents` with a company API key over HTTP Basic (Dashboard → Account →
Settings → API keys), which carries only the 20 tools below. Connection setup is documented in the **repo
README**, not here. **Offline mode always works:** without the MCP, you paste the generated JSON into
the dashboard's Expert Mode and copy IDs from the Dashboard
([`referenced-resources.md`](./referenced-resources.md)).

> **Never ask the user to paste an API key, password or sign-in code into the chat.** Sign-in happens in
> the app's connector settings; someone who wants an API key adds the voice-agents server to their app
> themselves (repo README), never through the chat. If the MCP isn't connected, point the user to the
> connector settings rather than collecting credentials here.

## The tool surface

### Authoring

| Tool | Purpose | Key caveat |
|---|---|---|
| `cloudtalk_list_voice_agents` | List the company's VoiceAgents (id, name, direction) | **Pages** (see *Reading lists*) and cached a few minutes — a just-created agent can be missing; see *Write safety* |
| `cloudtalk_get_voice_agent` | Fetch one agent's **complete config document** | The mandatory first step of every update — and the way to read a real, working `voice` ID. It does **not** pre-validate the 24-hex shape, so a numeric id fails upstream rather than at dispatch (`trigger_aiva_call` does check) |
| `cloudtalk_create_voice_agent` | Create an agent from a config | Write; the result carries the new `id`, a `dashboard_url`, and possibly `error_codes` (*Write safety*) |
| `cloudtalk_update_voice_agent` | Save a config to an existing agent (`voice_agent_id`) | Write — **merges** the fields you pass onto a fresh read (collections replaced wholesale); `apply_optimized_settings: true` applies the platform's optimized list; see Write safety |
| `cloudtalk_list_knowledge_bases` | List KBs: id, name, `description`, type (`CUSTOM`/`URL`/`FILE`), status, attached agents | Link only `ACTIVE` KBs, except a web page KB you just created, which `SKILL.md` *From a web page* links in the same save and checks once. **Pages**, and cached ~5 min — so a `SYNCHRONIZING` → `ACTIVE` flip can show up a cache TTL late: never poll |
| `cloudtalk_create_knowledge_base` | Create a KB: `custom` (you supply the text, `ACTIVE` at once) or `url` (ingested asynchronously, starts `SYNCHRONIZING`) | Write — name ≤ 50 chars; **text is frozen after creation**; **`description` is unsettable on create** — there is no input field for it, though the create response and the list read both carry it; file KBs are Dashboard-only |
| `cloudtalk_list_voice_agent_tools` | List custom tools, optionally filtered to one agent | **Never returns header/param values** — secrets go in, never come back out. **Pages** |
| `cloudtalk_create_voice_agent_tool` | Create a custom HTTP tool, optionally **attached** to agents in the same call | Write — name ≤ 64 (alnum + `-_`); method `GET/POST/PUT/DELETE/PATCH`; the URL may embed `{{param}}`; `awaiting_response_message` ≤ 4096; headers `CONST`\|`SECRET`; query/body params `CONST`\|`PARAM`\|`LLM`, each with a data type; **`voice_agent_config_ids`** attaches the new tool to those agents on create |
| `cloudtalk_update_voice_agent_tool` | Edit a custom tool | Write — **partial via read-modify-write**: the MCP fetches the tool, merges your fields, and sends a full replace upstream. **Omit** a key to preserve it; an explicit `[]` **clears** that list; **never send `null`** — the MCP rejects a null argument before the handler ever runs, so it preserves nothing. No version precondition upstream, so a concurrent Dashboard edit in that window is lost — re-read before editing a tool someone else is touching |
| `cloudtalk_assign_tool_to_voice_agent` | Attach a tool that **already exists** to an agent | Write — idempotent; an assign that changes nothing is a no-op and writes nothing (so does the matching unassign). For a brand-new tool, prefer `voice_agent_config_ids` on create |
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
| `cloudtalk_health_check` | Confirm the MCP is reachable and see which company/user the sign-in or key resolved to | Run it first when a tool fails: it separates an auth/tenant problem from a data problem. Makes **no** API call of its own, so it proves the credential was accepted, not that an upstream is healthy. **Check the echoed company id is the account you meant** (silently: never show a company id, user id or tool name to the user) — and the **`role_id`**: a non-admin key can still `cloudtalk_list_voice_agents`, but fails the other config reads (`get_voice_agent`, `list_knowledge_bases`, `list_voice_agent_tools`) **and every write** with an authorization error, which is the first thing to check when one list works and nothing else does. |
| `cloudtalk_list_agents` | Human agents: id, name, email, **extension**, availability | Both halves of an `agent` transfer pair come from here. Still prefer groups as targets (behavioral §3.4) |
| `cloudtalk_list_groups` | Ring groups — the preferred transfer targets | Returns **id + name only**. The `groupExtension` half is **not** in this response — take it from the Dashboard, the user, or the agent's current config |
| `cloudtalk_list_numbers` | Company numbers: id, country/area code, name, E.164, per-channel support flags | Resolves outbound-number IDs **and** SMS senders (`sms_supported: true`). `country_code` here is the **numeric calling code** (`421`), not the ISO-2 code `cloudtalk_search_calls` wants |
| `cloudtalk_list_contact_tags` | Contact tags in the account | An always-on account lookup — no VoiceAgent config field references a contact tag. **Pages** |

## Reading lists

- **The AI Voice Agent list reads page.** The three voice-agent-domain lists — VoiceAgents, knowledge bases,
  custom tools — take a `limit` (**default 50**, ceiling **200**) and return `pagination.next_page`
  when more rows exist. Check any list result for that field before treating it as complete.
- **The account reads page on different numbers.** Agents, groups, numbers and contact tags default to
  **200** with a ceiling of **1000**, and return `pagination.next_page` the same way.
- **`limit` trims the response, not the upstream cost.** The page is fetched either way, so a small
  `limit` saves you context, not rate budget — narrow with a filter when the budget is what's tight.
- **Follow `next_page` before concluding something doesn't exist.** Real accounts hold more than 50
  VoiceAgents, so "not in the list" from page one means nothing — page through, or filter.
- The call reads page differently: `cloudtalk_get_call_transcript` uses `limit`/`offset`, and
  `cloudtalk_search_calls` has a **bounded** pagination depth (narrow the filter instead of walking).

## Two ids, one name

A VoiceAgent has **two** identifiers. The read and every write carry both, under different key names:

| Id | Shape | In `cloudtalk_get_voice_agent` | In a write's result | Used by |
|---|---|---|---|---|
| config id | 24-hex string | `voice_agent.id` | `id` | `cloudtalk_get_voice_agent`, `cloudtalk_update_voice_agent`, `cloudtalk_trigger_aiva_call` (`voice_agent_id`) |
| numeric id | number | `voice_agent.voiceAgentId` | `voice_agent.voice_agent_id` | `cloudtalk_search_calls` (`voice_agent_id`), the call-record side |

Same name at the call boundary, different type. Passing the 24-hex config id to `search_calls`, or the
numeric one to `get`/`update`/`trigger`, fails or returns nothing — take each from the write's own result
rather than guessing which one you are holding.

**The key name does not tell you which id you hold.** `cloudtalk_list_voice_agents` returns the **24-hex**
id under the key name `voice_agent_id`, so a value read from a list is the config id whatever it is
called. Only the get and write responses carry the numeric one: `voice_agent.voiceAgentId` on the get
(the raw config document), `voice_agent.voice_agent_id` on a write's result.

## Write safety

- **Every write acts on its first call, and the app asks the user to approve it.** Claude or ChatGPT
  shows its own approval prompt before each write; that prompt is the user's one approval. So say in plain
  words what will change on which agent before you call, write only what the user asked for, and never
  report a write as saved until its result says so. An `assign` or `unassign` that changes nothing is a
  no-op. *Older servers:* a write that answers `status: "confirmation_required"` with a preview did
  nothing yet. That is a success state, not an error: show the preview, and call again with
  `"confirm": true` only once the user agrees.
- **Never send `null` for any argument.** The MCP rejects a null argument before the handler sees it, on
  every tool — omit the argument instead of passing null.
- **Updates merge onto the stored agent.** `cloudtalk_update_voice_agent` reads the agent and merges the
  fields you pass onto it before the upstream full replace, so only `voice_agent_id` is required and an
  omitted field keeps its stored value. **Collections are replaced, not merged** (`skills`, `scenarios`,
  `guardrails`, `secondaryLanguages`, `knowledgeBaseIds`): to change one entry, pass the whole list.
  Still **get → modify → update**: read the agent in this turn (the read gives you the current lists and
  the real IDs; never compose an update from memory or a stale copy), then send `voice_agent_id` plus
  only the fields you change, each changed collection or `elevenLabsSettings` in full. Re-sending the
  whole document would overwrite anything changed in the dashboard since your read.
- **Applying optimized settings is its own opt-in.** The agent's read (`cloudtalk_get_voice_agent`)
  carries `optimizedSettings`: the platform's picks for the agent's current setup (`provider`, `llm`, the ElevenLabs turn settings, the latest `minorVersion`;
  `schema.md` §5). Nothing in it is applied on its own. `apply_optimized_settings: true` copies every
  change's `to` into this save, `minorVersion` included, and is refused when nothing is available, when
  you also send a value for a listed path that is neither its `from` nor its `to`, or when you send a
  retired alias (`providerOverride` / `llmOverride`). **It must be its own save** when the call also
  changes `language`, `secondaryLanguages`, `knowledgeBaseIds`, `skills.custom`,
  `skills.transferToHuman`, `scenarios` or `goalPrompt`: the list was computed for the stored setup, so
  save that change first, then apply. Use it only when the user asks to take the platform's picks — it
  moves the agent's behaviour version.
- **The create demands the full set of required scalars.** `agentName`, `direction`,
  `defaultOutboundNumberId`, `language`, `maxCallDuration`, `temperature`, `voice`, `stability`,
  `similarity`, `startSpeakingFirst` and `goalPrompt`. A partial create payload comes back as *missing
  required*.
- **On a full-document save (Expert Mode, or the create), omission is not neutral, and not uniform** —
  one habit covers all three cases: send back the document `cloudtalk_get_voice_agent` gave you, modified.
  (The connected update is the exception: it merges, so there you send only the change, as above.)
  - `knowledgeBaseIds` **omitted = every KB unlinked**: carry the current list through each full document.
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
  first (below), then let the write return the server's answer. On newer servers the
  `cloudtalk_update_voice_agent` result also carries `changed_fields` and `applied_optimized_settings`;
  an older server's result doesn't (only its preview lists `changed_fields`). Report `changed_fields`
  only when the result carries them; otherwise list the changes you described before the save.
- **Read what a successful write returns.** Three writes carry a **`dashboard_url`** — create and update
  VoiceAgent, and create knowledge base: hand that link to the user instead of describing where to
  click. The tool and assignment writes and `cloudtalk_trigger_aiva_call` return none, so don't promise a
  link there. A VoiceAgent write can also carry **`voice_agent.error_codes[]`** *on a save that
  succeeded*: a stored-but-degraded reference (an unusable voice, a number the company can't send from).
  Surface those in plain language — **saved is not clean**.
- **Propagation lag is minutes, not seconds.** The list reads are cached (VoiceAgents and KBs a few
  minutes, numbers and groups longer) and a create **does not** clear that cache — so **wire the id the
  write itself returned** instead of re-listing to find it. A missing row right after a create is not a
  failed write. (Custom tools are the exception: tool creates, tool updates, and assign/unassign all
  clear the tool list cache.)
- **Wire the *right* id.** The write returns both a 24-hex `id` and a numeric
  `voice_agent.voice_agent_id`; see *Two ids, one name* above for which tool takes which.
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
— the app asks the user to approve it like every write, and the destination must be a number the **user names**
(typically their own phone), never one picked from a list. For an **inbound** agent, the test is the
other way around: the user calls the agent's assigned number.

Its two parameters: `voice_agent_id` — the **24-hex config id** (`cloudtalk_get_voice_agent`'s `id`, not
the numeric CDR one) — and `call_number`, strict **E.164**: a leading `+` then digits only, no spaces,
dashes or parentheses. The result carries a **`session_id`**, the correlation key for that call attempt;
keep it when reporting back. To find the call afterwards, `cloudtalk_search_calls` filtered by the
agent's **numeric** `voice_agent_id` (*Two ids, one name*), then transcript/insights.

Ask the user to stay on a test call for **at least 30 seconds**. A shorter call has no transcript or
insights: `cloudtalk_get_call_transcript` answers `reason: "no_transcript"`, which is an answer, not a
reason to retry. Say so once and ask the user what they heard. *Older servers:* the first
`cloudtalk_trigger_aiva_call` answers `status: "confirmation_required"` and dials nothing; show its
preview and call again with `"confirm": true` once the user agrees. A `queued` result is queued, not
answered.
