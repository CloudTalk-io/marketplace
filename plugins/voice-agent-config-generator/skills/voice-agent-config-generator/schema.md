# Voice Agent v2 — Expert Mode schema (structural reference)

> **What this is:** the structural reference for the **v2 request body**
> (`VoiceAgentV2ConfigurationRequest`) — the canonical importable/exportable JSON. Human view of
> [`fields.json`](./fields.json); if a field's `authoring` tag and its row here ever disagree,
> `fields.json` wins. The `authoring` **column in §2 is the only per-field tier copy** in this doc
> (a convenience overview); the rest of this doc describes structure, not tiers.
>
> **What this is NOT:** quality guidance (see [`behavioral-guidance.md`](./behavioral-guidance.md)) or
> how to create the referenced resources in the UI (see [`referenced-resources.md`](./referenced-resources.md)).
> A good config must satisfy this doc **and** the behavioral one.

Each field carries an **`authoring`** tag — `generate` · `reference` · `environment` ·
`forbidden` (defined in the [README](./README.md#the-authoring-tiers-full-field-partition)).

---

## 1. What this document covers

The dashboard's Expert mode exposes an Advanced/code tab on an agent
you **already created in the UI** — pasting JSON there **edits that agent**, and the editor pre-loads the
agent's current config. There is also an export and a create path. All use the **v2** config document:

- **Export** copies the agent's current JSON to the clipboard (the JSON you paste into an LLM — and the
  source to **reuse** real values from).
- **Edit — the normal path:** saving the pasted body **replaces** the loaded agent's config wholesale
  (a full-document update). Reuse the real values it already has (outbound number, any wired IDs) rather
  than inventing them.
- **Create** makes a new agent from a body. In the dashboard the code tab is reachable only after a UI
  create, so the paste path is **effectively always an edit**; creating a brand-new agent from pasted
  JSON is not available there yet (connected mode can create directly — see [mcp-tools](./mcp-tools.md)).

The legacy v1 wizard fields (`voiceAgentPrompt`, `extractionPrompt`, `transferEnabled/transferTo`,
`hangupEnabled/hangupPrompt`, `resultsEndpoint`) are **not** part of v2 and must not appear.

> **Server-stamped / response-only (do not author):** `version` (always `2`) and
> `minorVersion` (`= LatestMinorVersion`, currently `3` → **v2.3**) are stamped server-side;
> `id` / `voiceAgentId` / `createdAt` / `updatedAt` are response-only. They appear on GET/export
> but are ignored on import — do not author them. `minorVersion` and `upgradeAvailable` are accepted
> on input and recomputed server-side, so a GET response round-trips safely into an update.
>
> The platform's **diagnostics are response-only too**: `warnings`, `errorCodes` and `upgradeAvailable`
> ride along on a read or a write result — and a **successful** save can still carry `errorCodes`
> (a stored-but-degraded reference). Read them and report them; never author them. (There is **no**
> `upgradeSummary` field — it does not exist.)

---

## 2. Top-level fields

| Field | `authoring` | Type | Required | Constraints / valid values | Notes |
|---|---|---|---|---|---|
| `agentName` | generate | string | ✅ | non-empty | Display name. |
| `direction` | generate | string | ✅ | `"inbound"` \| `"outbound"` | See dependency rules (§3). |
| `defaultOutboundNumberId` | **environment** | int | ✅ | ≠ `0`. **`1` = Automatic**; **every other value, incl. `2`, is a literal company-owned number ID** (no "Random") | Required even for inbound. **Defaults to `1` (Automatic), exactly as the dashboard seeds it** — the save never auto-picks a number, so `1` needs a real owned `failoverOutboundNumberId` in both directions to complete it (§3, §8). Setting a real owned number id directly is the alternative — reuse the agent's value, fetch it (`cloudtalk_list_numbers`), or ask; never guess `2`. |
| `failoverOutboundNumberId` | **environment** | int | ❌ | a real owned number ID — **omit the key only when `defaultOutboundNumberId` is a real non-`1` id; never `null`** | The number Automatic falls back to. **Required in BOTH directions whenever `defaultOutboundNumberId` is `1`** — the save `400`s without it and nothing self-heals (§3.2). |
| `language` | generate | string | ✅ | a value from the **resolved provider's** set (§4.3) | Drives provider auto-selection (§5). |
| `secondaryLanguages` | generate | string[] | ❌ | each provider-supported | Presence forces ElevenLabs + marks "complex"; **pin `providerOverride: "elevenlabs"`** when set (§5). |
| `maxCallDuration` | generate | int | ✅ | minutes; **hard cap** — call is cut off when reached; no hard API cap, but keep it **≤ 120** (a value above that draws a recommendation warning, not a save refusal) | Required; the dashboard fills **30** if omitted (no 240 default). Set generous headroom, not a tight fit; ~20–30 min inbound, ~10–15 min outbound (behavioral §4.4). |
| `temperature` | generate | float | ✅ | `0.0`–`1.0` | LLM sampling temperature. Baseline `0.5`; highly structured/deterministic flows may go lower (~`0.1`–`0.3`) (§7a-bis). |
| `voice` | generate | string | ✅ | a voice ID in the library (§4.4) | Built-in premade set is global (self-contained). |
| `optimizeStreamingLatency` | generate | int | ❌ | `0`–`4` | ElevenLabs latency tuning; **optional (not API-required), and the API applies no default**. Omitted on a write = **reset to `0`**, not preserved — so always emit it deliberately. Baseline `2`, never `4` (§7a-bis). Unlike `elevenLabsSettings` (omit-to-let-provider-default), this is not backfilled. |
| `stability` | generate | float | ✅ | `0.0`–`1.0` | Voice stability. **Required and passed straight through to ElevenLabs — the API applies no default and does NOT backfill it**; omitting it fails the save. Baseline `0.3` (§7a-bis). |
| `similarity` | generate | float | ✅ | `0.0`–`1.0` | Voice similarity boost. **Required and passed straight through to ElevenLabs — the API applies no default and does NOT backfill it**; omitting it fails the save. Baseline `0.7` (§7a-bis). |
| `llmOverride` | generate | string | ❌ | a canonical model ID (§4.2) | Skips auto LLM selection; must be offered by the resolved provider. |
| `providerOverride` | generate | string | ❌ | `"elevenlabs"` \| `"deepgram"` | Skips auto provider selection. |
| `dialTime` | generate | int | ❌ | `0` or `5`–`120` s; `0` = provider default; preserve-on-omit on PUT | Ring/no-answer timeout. Values above `90` fail when the call is dispatched — keep it ≤ `90` (§3.8). |
| `elevenLabsSettings` | generate | object | ❌ | see §10 | ElevenLabs-only tuning; ignored on Deepgram. |
| `verbosity` | generate | string | ❌ | `"concise"` \| `"standard"` \| `"thorough"`; `""`/omitted = unset | Response-length preset; platform default `standard` (§11). |
| `tone` | generate | string[] | ❌ | each ∈ the 6-label allowlist (§11); `[]`/omitted = unset | Identity tone presets; platform default `["friendly","direct"]`; no free text (§11). |
| `startSpeakingFirst` | generate | bool | ✅ | **must be `true` when inbound** (platform-enforced) | Gates `greeting`. Author-supplied in Expert Mode and respected; the wizard derives it as `!!greeting`, but that's the wizard path, not Expert Mode (§ greeting note). |
| `goalPrompt` | generate | string | ✅ | non-empty | The agent's core behavioral instructions. Can be substantial — a soft target of up to ~250 words (behavioral §2.1); only a genuinely empty or one-line prompt is flagged as thin. |
| `greeting` | generate | string | ❌ (recommended) | — | Spoken **verbatim** as the first line (§ greeting note). |
| `skills` | (per-skill) | object | ❌ | see §6 | Structured capabilities; tags vary by skill. |
| `scenarios` | generate¹ | array | ❌ | see §7 | ¹`action` sub-value changes the tag (§7). |
| `guardrails` | generate | array | ❌ | see §7 | Condition → safe reply. |
| `knowledgeBaseIds` | **reference** | string[] | ❌ | KB IDs owned by the company | Influences auto LLM (§5). **No preserve-on-omit:** omitting it on a full-document update unlinks every KB — carry the current value forward when editing. See [referenced-resources](./referenced-resources.md). |

> **System-managed fields — do NOT author (`forbidden`): `presetType`, `status`, `lastConfigurationStep`,
> `hasOverrides`.** These are real stored fields, but on the Expert-Mode editor save path the dashboard sources
> `presetType`/`status`/`lastConfigurationStep` from the **loaded agent** (not your pasted JSON) and
> force-sets `hasOverrides: true`; on create the platform defaults `status` to enabled and the others to
> empty/0. `hasOverrides` shelters the agent from future auto provider/LLM upgrades (and has no effect at
> creation, since new agents are stamped at the latest minorVersion). Net: the generator omits all four —
> the editor and the platform own them.

> **Do NOT include (computed / response-only):** `provider` / `llm` (computed server-side; influence via
> `providerOverride`/`llmOverride`), the response-only fields and the platform's diagnostics —
> `warnings`, `errorCodes`, `upgradeAvailable` (§1) — and the export tags `companyId` /
> `environmentName` (§8). Legacy v1 fields are not part of v2 at all — the `/validate` endpoint refuses
> them as unknown keys, and the save silently drops them (§9).

### `greeting` — what actually happens

`greeting` is the **exact line the agent speaks first** — used as written; nothing rewrites or
auto-generates it. It is the only field for the opening line (**there is no `firstMessage` field**).

- The agent speaks the greeting only when `startSpeakingFirst` is `true` (which is required for
  inbound, §3).
- If `greeting` is **empty**: an **inbound** agent falls back to a generic default
  (`"Hello, how can I help you today?"`); an **outbound** agent stays silent until the caller speaks
  — so an outbound agent that should open the call needs a greeting, or it begins with dead air.
- On import, `greeting` is optional: a missing, null, or empty value is accepted — the fallbacks above
  then apply.

**Implication:** always give inbound agents a concrete `greeting` with `startSpeakingFirst: true`;
never rely on the runtime fallback.

---

## 3. Field dependency rules (enforced — cause `400`/`422` on import)

1. `defaultOutboundNumberId` must not be `0`. It **defaults to `1` (Automatic)**, exactly as the dashboard
   seeds it; any other value is a **real owned number ID** (never invented or copied from an example).
2. `defaultOutboundNumberId == 1` (Automatic) picks a number per call and falls back to
   `failoverOutboundNumberId`, so **Automatic REQUIRES a real owned `failoverOutboundNumberId` in BOTH
   directions** — there is no inbound carve-out, the save `400`s without it, and nothing self-heals (the
   config save does not auto-pick a number). **Never send `null`.** Omit the failover key only when
   `defaultOutboundNumberId` is a real non-`1` id. **There is no "Random": every value other than `1` —
   including `2` — is a literal phone-number ID the company must own.**
3. `direction == "inbound"` ⇒ `startSpeakingFirst` **must be `true`**.
4. `temperature`, `stability`, `similarity` ∈ `[0, 1]`; `optimizeStreamingLatency` ∈ `[0, 4]`.
5. `voice` must exist in the voice library.
6. `llmOverride`, if set, must resolve to a model offered by the **resolved** provider (§4.2) — else `400`.
7. **Deepgram + `secondaryLanguages`** is rejected (Deepgram has no multilingual mode) — so pin `providerOverride: "elevenlabs"` for any multilingual config (§5).
8. `dialTime`, if non-zero, must be `5`–`120` s. Values above `90` pass validation but fail when the
   call is dispatched — recommend ≤ `90`. Omitted preserves the stored value.
9. `elevenLabsSettings.turnEagerness` ∈ {`patient`,`normal`,`eager`}, `.turnModel` ∈ {`turn_v2`,`turn_v3`}, `.backgroundSound.preset` ∈ {`office`,`office2`,`restaurant`,`city`,`typing`,`elevator`,`elevator2`,`elevator3`,`elevator4`} (required when `backgroundSound` is present), `.backgroundSound.volume` ∈ `[0,1]`; `.interruptionIgnoreTerms` / `.interruptionIgnoreTermLanguages` are lists of non-empty strings.
10. Skill / scenario rules — §6 / §7.

> The only *structural* validation on the outbound number is rules 1–2 — nothing here checks that the
> number ID is one your company owns. An unowned ID is a hard `400` at save with a clear error naming the
> number: `outbound number <id> does not exist or does not belong to the company`, with no self-heal. So a
> guessed `2` passes this check but breaks the save; reuse the agent's real value or fetch a real one
> (`cloudtalk_list_numbers` / the dashboard). Bare `1` with no failover breaks the save the same way.

---

## 4. Enumerated valid values

### 4.1 Providers
`elevenlabs`, `deepgram`. Chosen automatically (§5); override with `providerOverride`.

### 4.2 LLM models — canonical IDs (for `llmOverride`)

The API keeps a fixed **registry of 25 canonical models**. The wire format is a canonical id
`"<vendor> - <model>"`, vendor ∈ `openai` | `anthropic` | `google` | `qwen`. **ElevenLabs offers all 25;
Deepgram offers only the 14 marked ✅ in its column below.** The model must match the **resolved**
provider or the save returns `400`. Use the **canonical ID**; native/legacy masks are also accepted and
normalized server-side (responses return the canonical ID).

> **The LLM is auto-selected server-side unless `llmOverride` is set** (§5). `llmOverride` skips that
> selection and pins a specific model.

| Canonical ID (`llmOverride`) | ElevenLabs | Deepgram |
|---|:---:|:---:|
| `openai - gpt-4o-mini` | ✅ | ✅ |
| `openai - gpt-4o` | ✅ | ✅ |
| `openai - gpt-4.1` | ✅ | ✅ |
| `openai - gpt-4.1-mini` | ✅ | ✅ |
| `openai - gpt-4.1-nano` | ✅ | ✅ |
| `openai - gpt-5` | ✅ | — |
| `openai - gpt-5-mini` | ✅ | ✅ |
| `openai - gpt-5-nano` | ✅ | ✅ |
| `openai - gpt-5.1` | ✅ | — |
| `openai - gpt-5.2` | ✅ | — |
| `openai - gpt-5.4` | ✅ | — |
| `openai - gpt-5.4-mini` | ✅ | ✅ |
| `openai - gpt-5.4-nano` | ✅ | ✅ |
| `openai - gpt-5.5` | ✅ | — |
| `anthropic - claude-haiku-4-5` | ✅ | ✅ |
| `anthropic - claude-sonnet-4-5` | ✅ | — |
| `anthropic - claude-sonnet-4-6` | ✅ | — |
| `google - gemini-2.5-flash` | ✅ | ✅ |
| `google - gemini-2.5-flash-lite` | ✅ | — |
| `google - gemini-3-flash-preview` | ✅ | ✅ |
| `google - gemini-3.1-flash-lite` | ✅ | ✅ |
| `google - gemini-3.5-flash` | ✅ | ✅ |
| `google - gemini-3.6-flash` | ✅ | — |
| `qwen - qwen36-35b-a3b` | ✅ | — |
| `qwen - qwen35-397b-a17b` | ✅ | — |

> **Default pick:** `anthropic - claude-haiku-4-5` (offered by both providers) is the safe default for an
> agent doing real work. The two `qwen` models are valid **ElevenLabs-only** overrides — and
> `qwen - qwen36-35b-a3b` is also the value a *trivial* ElevenLabs agent auto-defaults to (§5).
>
> An `llmOverride` is valid only if the **resolved provider** offers it (e.g. `openai - gpt-5` on a
> Deepgram-resolved agent → `400`). If you also set `providerOverride`, keep the two consistent.
>
> **Legacy aliases** are accepted on input but **silently normalized to a current canonical ID** on
> save (the export then shows the canonical one). Always author the canonical ID — the bundled validator
> (§9) flags legacy aliases. Examples: `anthropic - claude-3-7-sonnet` → `anthropic - claude-sonnet-4-5`;
> `anthropic - claude-3-haiku` → `anthropic - claude-haiku-4-5`; `google - gemini-1.5-pro` →
> `google - gemini-2.5-flash`; `google - gemini-2.0-flash-lite` → `google - gemini-2.5-flash-lite`.

### 4.3 Languages (per provider)

- **ElevenLabs**: a wide accepted list (~66 codes), including all the plain two-letter codes
  (`en`, `de`, `es`, `fr`, `pt`, …) — when in doubt, the plain code is supported.
- **Deepgram** (`multi` + regional variants): `multi, en, en-US, en-AU, en-GB, en-NZ, en-IN, bg, ca,
  zh, zh-CN, zh-Hans, zh-TW, zh-Hant, zh-HK, cs, da, da-DK, nl, et, fi, nl-BE, fr, fr-CA, de, de-CH,
  el, hi, hu, id, it, ja, ko, lv, lt, ms, no, pl, pt, pt-BR, pt-PT, ro, ru, sk, es, es-419, sv, th,
  tr, uk, vi`.

> The server normalizes languages to the resolved provider's set. Pick a language the target provider
> supports (§5 explains how the provider is chosen from the language).
>
> **Multilingual combinations are validated server-side** — not every code can join a multilingual set:
> an incompatible `language` + `secondaryLanguages` combination is rejected on save with per-code errors.
>
> **Two distinct multilingual mechanisms — do not conflate them:**
> - **ElevenLabs multilingual** is driven by **`secondaryLanguages`**, which forces the ElevenLabs provider
>   (§5). This is the default for any multilingual agent.
> - **Deepgram multilingual** is the single language code **`multi`** — Deepgram-only, and it switches
>   Deepgram's listen model to `nova-3`. It is **never auto-selected for a multilingual request**: reach it
>   only by explicitly setting `language: "multi"` **together with** `providerOverride: "deepgram"`.
> - **Deepgram + `secondaryLanguages` is rejected at save** (Deepgram has no `secondaryLanguages` mode).
>
> So: **default to ElevenLabs for multilingual; use Deepgram `multi` only on explicit request.**

### 4.4 Voices (shared IDs)

The platform serves a fixed set of built-in **premade voice IDs** (global, not company-scoped —
`GET /api/v1/voice-agent/voices`). **Every one is an ElevenLabs voice ID, and CloudTalk uses ElevenLabs
voices for every provider**, so all four below are usable on **both** ElevenLabs- and Deepgram-resolved
agents. There is **no MCP/plugin tool that lists voices**, so this is the confirmed default set to pick
from (or reuse a `voice` from an existing agent's config):

```
cgSgspJ2msm6clMCkdW9  (Jessica — Female, American English; also ar, cs, de, fr, hi, ja, zh)
IKne3meq5aSn9XLyUdCD  (Charlie — Male, Australian English; also es, fil, pt, zh)
cjVigY5qzO86Huf0OWal  (Eric — Male, American English; also de, es, fr, pt, sk)
iP95p4xoKVk53GoZ742B  (Chris — Male, American English; also ar, fr, hi, pt, sv)
```

- **Default when unsure: `cgSgspJ2msm6clMCkdW9` (Jessica)** — the only **female** voice in this default
  set. The model picks by gender/language; for another voice or gender, the **dashboard voice picker** is
  the path.
- **Always advise the user to pick their preferred voice in the dashboard voice picker** — it holds the
  full, language-filtered catalog (synced from ElevenLabs); this short set is only the default.
- The language captions are **free-text labels, not a guarantee of per-language coverage** — a voice speaks
  whatever the agent's `language` is (E2 runs a German agent on an American-English-labelled voice).
- Whatever you pick, `voice` must exist in the **resolved provider's** library or import fails (§3.5).

---

## 5. How provider & LLM are auto-selected

When `providerOverride`/`llmOverride` are absent, the server computes them at save time, routing on
language and complexity:

#### Provider
1. `secondaryLanguages` present → **ElevenLabs** (generator pins `providerOverride: "elevenlabs"` — see note below).
2. Language supported **exactly** by Deepgram but **not** ElevenLabs — the **non-plain** codes: `multi`
   and the regional variants (`en-US`, `en-GB`, `pt-BR`, `es-419`, `zh-Hans`, …) → **Deepgram**.
3. Else ElevenLabs supports the language (**all plain codes** `en`, `de`, `es`, `fr`, …) → **ElevenLabs**.
4. Else → **Deepgram**.

> The **knowledge base does not affect the provider**, and plain languages resolve to
> **ElevenLabs**. Deepgram is auto-picked only for a Deepgram-exclusive code (rule 2) or rule-4 fallback.
> A plain two-letter code that the §4.3 Deepgram list *also* carries (`ca`, `et`, `lv`, `lt`, `th`, …) is
> **not** exclusive — it still resolves to ElevenLabs, so ElevenLabs-only settings and models stay valid
> on it.
>
> **Generator rule:** when emitting `secondaryLanguages`, also set `providerOverride: "elevenlabs"` to
> pin the provider. Auto-selection yields ElevenLabs anyway, but an edited agent with a stored Deepgram
> provider would otherwise preserve it and reject the multilingual save (§3.7).
>
> **Deepgram `multi` is explicit-only (§4.3).** A multilingual *request* defaults to ElevenLabs via
> `secondaryLanguages`; never auto-route it to Deepgram. Rule 2 will resolve a bare `language: "multi"` to
> Deepgram, but the generator emits `multi` **only when the user explicitly asks for Deepgram
> multilingual**, and then pins it with `providerOverride: "deepgram"` so a later edit can't drift it off.

#### LLM
The agent is classified **complex** if any of: has KB, has secondary languages, **≥1 custom tool**,
**≥3 transfer rules**, **≥3 scenarios**, or **goalPrompt ≥ 1500 chars**; else **trivial**.

> **"≥1 custom tool" counts enabled `skills.custom` entries PLUS scenarios with `action == "toolCall"`** —
> both feed the same tool tally, so either one on its own tips the agent to complex.

- Deepgram (any tier) → `anthropic - claude-haiku-4-5`
- ElevenLabs + complex → `anthropic - claude-haiku-4-5`
- ElevenLabs + **trivial** → `qwen - qwen36-35b-a3b` (lightweight)

> A *simple* ElevenLabs agent silently defaults to the lightweight **Qwen** model. To guarantee a
> stronger model on a small but important agent, set `llmOverride: "anthropic - claude-haiku-4-5"`.
> See behavioral §7b.

---

## 6. `skills` sub-schema

All skills optional — but **every skill object you *do* send must carry an explicit `enabled` bool**
(plain `true`/`false`, never omitted): the API rejects a skill without it (`422 expected required
property enabled to be present`), and nothing defaults it on import. `enabled: false` is a legal,
useful shape — it ships a skill switched-off for the user to finish in the dashboard (§6.1).

```jsonc
"skills": {
  "transferToHuman":    { ... },
  "takeMessage":        { ... },
  "extractData":        { ... },
  "custom":             [ ... ],
  "answerQuestions":    { ... },
  "appointmentBooking": { ... }
}
```

> **Some of these need an already-created company object** (a custom tool, agent/group, or calendar
> integration) — those are **not** self-contained: a human must create/select the resource and wire its
> ID in the UI. A direct `transferToHuman`/`answerQuestions` transfer needs a real agent/group **id +
> extension**, and `appointmentBooking` needs a connected calendar. When the real values aren't available,
> the shape that still saves is the skill **switched off** — `enabled: false` with `rules: []` — which the
> dashboard surfaces as *"Requires configuration"* for the user to finish (§6.1). The `authoring` tier per
> field is in the §2 column and [`fields.json`](./fields.json); **what each referenced object is and how to
> create + wire it is in [`referenced-resources.md`](./referenced-resources.md).**

**What each skill does:**

| Skill | Dashboard name | What it does |
|---|---|---|
| `transferToHuman` | Transfer to Human | Transfer callers based on what they say or need |
| `takeMessage` | Take a message | Takes a message and collects caller details |
| `extractData` | Extract information | Capture specific data points during the call |
| `answerQuestions` | Answer Questions | Answer FAQs from your knowledge base |
| `appointmentBooking` | Appointment Booking | Connect your calendar so the agent can book meetings |
| `custom` | Custom | Configure your own skill |

### 6.1 `transferToHuman`
```jsonc
{
  "enabled": false,                         // required bool — the generator ships this draft switched OFF
  "confirmationRequired": true,             // optional; the scaffold default (matches the dashboard create-time default)
  "rules": [                                // required key whenever this object is present ([] legal only while OFF)
    {
      "condition": "when the customer explicitly asks for a human agent",
      "destination": "group"                 // "agent" | "group" | "call_flow" — the intended human target
      // groupId / groupExtension OMITTED on a switched-off draft: the user completes the target in the
      // dashboard, then switches the skill on. Never blank an integer id to "" — that is an INVALID_TYPE.
      // When you DO have a complete real pair: enabled: true with groupId + groupExtension both set (or
      // agentId + agentExtension for an "agent" target) — both halves are part of the dial
    }
  ],
  "includeProperties": ["callerName", "summary"],   // optional; scaffold default — ONLY these two valid — context for the human who picks up
  "customProperties": [ { "name": "accountTier", "type": "STRING", "description": "Plan tier" } ]
}
```
- **`rules` is a required key** as soon as the object exists — omitting it is a `422`. **`[]` is legal only
  while the skill is switched off**; an **enabled** `transferToHuman` needs **≥ 1 rule** (an enabled skill
  with `rules: []` is save-refused). Every rule you do send needs both a `condition` and a non-blank
  `destination` — `""` (target not decided) is legal only while the skill is switched off.
- `destination` ∈ `agent | group | call_flow`. **A direct destination needs BOTH halves of its pair** —
  `agent` ⇒ `agentId` **and** `agentExtension`; `group` ⇒ `groupId` **and** `groupExtension`. **`agentId`
  and `groupId` are INTEGERS** (the extension is a string, and is part of the dial; see
  [referenced-resources](./referenced-resources.md)).
- **The default way to ship a transfer the generator can't fully ground is a *disabled draft*.** Two shapes:
  - **Scaffold the group** — `enabled: false` with a rule carrying `destination: "group"` and the id/extension
    keys **omitted** (`groupId`/`groupExtension` absent). The group intent is visible; the target is the
    user's to finish. This is the default, because a group's extension **can't be read programmatically**, so
    the generator scaffolds and the user completes it.
  - **Or `enabled: false` with `rules: []`** when there is no specific group in mind at all.
  Both save cleanly and the dashboard shows the skill as *"Requires configuration"* (locked toggle) for the
  user to finish with the real pickers. Say it to the user in plain terms — *"finish setting up the transfer
  to your team in the dashboard and turn it on"* — never in DB terms like "add a group extension."
- **On a draft, OMIT the id/extension keys — never blank them to `""`.** `agentId`/`groupId` are integers,
  so `"groupId": ""` is an **INVALID_TYPE** the save rejects even on a disabled skill; and on an *enabled*
  rule an empty extension passes validation *and* the runtime's usability check, gets advertised to the LLM
  as a working transfer, then dials nothing — dead air on a cold fallback. So a draft omits the keys, and an
  enabled rule always carries a complete real pair.
- **Transfer ids/extensions are not verified at save.** A wrong or foreign id/extension pair fails only
  mid-call — where advanced transfer is enabled the AI announces the failure and resumes, but on a cold
  fallback the caller is dropped silently — double-check both halves. Wire a complete pair (`enabled: true`)
  only from IDs the user gave you or that came out of their current config — in connected mode
  `cloudtalk_list_agents` returns an agent's id **and** extension, while `cloudtalk_list_groups` gives the id
  and name but **not** the group extension; **never guess one.**
- Where advanced transfer is enabled for the company, `agent` / `group` run **attended** (the caller stays
  with the AI while the second leg is placed, and a leg that goes busy, declined, timed-out, or dropped
  bounces back to the AI); where it is not enabled they fall back to **cold**.
- `call_flow` needs no ID: the agent hangs up and the Call Flow continues — **always a cold hand-off with
  no resume**. That only means something when the agent **runs as a step inside a Call Flow** — for a
  standalone agent it is just a hangup — so use it when the user says that's their setup, not as the
  default handoff.
- `includeProperties` (`callerName` | `summary`) plus any `customProperties` you define are the **data
  extracted and handed to the human who picks up the transferred call**, so the receiver has context on the
  transfer (not a caller-facing feature). `customProperties[].type` ∈ `STRING|NUMBER|BOOLEAN|ARRAY`.

### 6.2 `takeMessage`
```jsonc
{ "enabled": true, "prompt": "Ask the caller for their name, number, and reason for calling." }
```
`prompt` optional. Self-contained.

### 6.3 `extractData`

`properties` is a **list** of `{ name, type, description }` items; `type` ∈ `STRING|NUMBER|BOOLEAN|ARRAY`
(**uppercase**), all three fields required.

```jsonc
{
  "enabled": true,
  "properties": [
    { "name": "customerName", "type": "STRING", "description": "Caller's full name" },
    { "name": "orderNumber",  "type": "NUMBER", "description": "Order reference number" }
  ],
  "endpoint": "https://example.com/webhook"   // optional, user-supplied (not a company-resource ID)
}
```

A **lead-qualification** set, for example, might capture: **full name** (`STRING`), **company size**
(`STRING` band or `NUMBER`), **budget range** (`STRING`), and **callback requested** (`BOOLEAN`) — write
each `description` as an extraction instruction ("the budget the caller states, as a range"), never as a
quoted question.

> **`extractData` is a PASSIVE, post-call step — it does NOT steer the live conversation.** The agent does
> not ask for these values just because they are declared here; extraction runs **after the call, against
> the transcript** (a runtime code comment confirms extract-data is handled post-call, not in the prompt —
> behavioral §1/§3.1). To have the agent **actively collect** a value during the call, put the ask in
> `goalPrompt` (or a custom skill) **and** declare the matching `extractData` property — the two together.
> A property on its own captures only what the caller happened to say.

### 6.4 `custom`
```jsonc
[ { "enabled": true, "name": "verifyIdentity", "prompt": "Verify the caller via DOB + last 4 digits." } ]
```
All three fields required per entry. Self-contained.

### 6.5 `answerQuestions`
```jsonc
{
  "enabled": true,
  "action": "admitUncertainty"   // "admitUncertainty" | "offerAlternative" | "transferToHuman" (the last requires transferConfig)
}
```
**What it does:** lets the agent answer caller questions from the attached knowledge base / custom
skills. **`action` tells the agent how to behave when it *can't* answer a question** from what it knows:

| `action` | What the agent does when it can't answer | Example response |
|---|---|---|
| `admitUncertainty` | Says it doesn't have the answer, and leaves it there | *"I'm sorry, I don't have that information right now."* |
| `offerAlternative` | Admits it can't answer, then steers the caller to what it *can* help with | *"I can't answer that, but I can help you with [other topics]."* |
| `transferToHuman` | Hands the caller to a person (requires `transferConfig` — a real agent/group **id + extension**, or `call_flow` inside a Call Flow) | *"Let me transfer you to someone who can help."* |

- **`action` is a 3-value enum** — `admitUncertainty` | `offerAlternative` | `transferToHuman`. The first
  two are **self-contained** (no target). `transferToHuman` ⇒ `transferConfig` required.
- **`transferConfig.destination` is the fixed enum** `agent` | `group` | `call_flow`, but the concrete
  **target IDs are free-form** (an agent id + extension from `cloudtalk_list_agents`, a group id +
  extension) — **not an API-provided option list**; nothing hands you the valid targets. Same rules as §6.1:
  a direct target needs the id **and** the extension.
- **Don't emit a wired group target here either** (per §6.1) — a group's extension can't be read
  programmatically. Either scaffold `transferToHuman` as a **disabled draft** (`enabled: false`, a rule
  with `destination: "group"` and the id/extension omitted) for the user to *finish setting up the
  transfer to their team in the dashboard*, or — the
  simpler default — pick `admitUncertainty`/`offerAlternative`, which need no target at all. Picking the
  action: behavioral §3.2.

### 6.6 `appointmentBooking`  — needs a connected calendar integration
```jsonc
{
  "enabled": true,
  "integrationId": "65f...",            // required — a calendar integration owned by the company
  "calendarId": "primary",              // required
  "eventName": "Discovery call",        // required
  "durationMinutes": 30,                // required — > 0
  "serviceDescription": "30-min intro call.",         // optional
  "calendarEventDescription": "Booked by Acme agent"  // optional
}
```
- `enabled: true` ⇒ `integrationId`, `calendarId`, `eventName` required; `durationMinutes > 0`.
- **`durationMinutes`** — any positive duration (e.g. `15` or `30` minutes); set whatever the booked
  service needs.
- **`serviceDescription`** — a description of the service, made available to the voice-agent LLM so it knows
  what it is booking and can communicate it to the contact.
- **`calendarEventDescription`** — the description written onto the scheduled calendar event itself (may be
  customer-facing).
- **Server-managed — do not author:** `integrationType`, `availabilityToolId`, `bookingToolId`,
  `errorCode`. Strip `errorCode` if present in an export.
- `integrationId`/`calendarId` are company-scoped — see [referenced-resources](./referenced-resources.md).
- Booking data is exposed as `{{appointment.*}}` template variables (behavioral §6); to text a confirmation
  after an in-call booking, use a `triggerType: "booking_confirmed"` scenario (§7.1) — there is no
  customer-facing booking/calendar link.

---

## 7. `scenarios` and `guardrails`

### 7.1 `scenarios`
```jsonc
[
  {
    "enabled": true,                               // REQUIRED plain bool on every scenario
    "when": "the customer asks about their order status",
    "reply": "Let me check that for you.",
    "triggerType": "custom",                       // optional: "custom" (default) | "booking_confirmed"
    "action": "toolCall",                          // "toolCall" | "sendSms" | "hangup"; omittable, but a hangup must say so explicitly
    "toolReferenceId": "aabbccddeeff001122334455"  // REQUIRED when action == "toolCall"
  },
  {
    "enabled": true,
    "triggerType": "booking_confirmed",            // fires automatically after a successful in-call booking; omit `when` — the platform overwrites it
    "action": "sendSms",                           // REQUIRED params shape below
    "params": {
      "senderNumber": "+15555550100",              //   valid E.164, owned by the company
      "message": "You're booked for {{appointment.event_name}} on {{appointment.start_pretty}}. See you then!"
    }
  }
]
```
- **`enabled` is required** on every scenario — omit it and the save fails with `422 expected required
  property enabled to be present`. Two traps: a pre-save check **green-lights a missing `enabled`** (the
  absent key decodes to *disabled*, so it only demotes the finding to a warning) while the save then 422s
  — the bundled validator (§9) closes that gap; and a stored scenario without it is **silently inactive**
  at runtime. Always emit it.
- `triggerType` (optional) ∈ `"custom"` (default when omitted) | `"booking_confirmed"`. **`custom` requires
  a non-empty `when`** — author `when` only for custom triggers. **`booking_confirmed`** fires
  automatically after a successful in-call booking and the platform **overwrites `when`** with its own
  text (*"the booking is confirmed"*), so anything you put there is discarded — omit the key. Any other
  `triggerType` value → `422`.
- `action == "hangup"` → self-contained, and the **only** way to give the agent `end_call`. **Write it
  explicitly:** an omitted `action` leaves the scenario a plain reply, so a config whose closing scenario
  has no `action` ships an agent that cannot end a call (the validator's save-blocking `no-hangup`).
  `enabled: true` is part of the same rule — a switched-off hangup scenario grants nothing.
- `action == "toolCall"` → needs `toolReferenceId` (a company custom tool).
- `action == "sendSms"` → needs `params.senderNumber` (a company-owned number). **`params.message` is fixed
  config text** — the LLM only decides *whether* to send (it passes a logging `reason`), never writes or
  edits the body. Before sending, the body runs through a **template engine**: `{{…}}` variables resolve
  (call-placement dynamic vars, `{{caller_number}}`, `{{contact.*}}`, and — post-booking — `{{appointment.*}}`;
  full set in behavioral §6). An **unknown/unset variable resolves to an empty string** (silently deleted,
  no braces shown). **URLs must be user-supplied verbatim** — never invent one, and there is **no per-call/
  booking-link variable**. A `triggerType: "booking_confirmed"` + `sendSms` scenario is the correct way to
  send a booking-confirmation SMS.

> On a **cross-account** paste (a config from a *different* company — `companyId`/`environmentName` ≠
> target; **not** the normal case of editing your own agent, where the company matches) the dashboard **silently
> strips** `toolCall`/`sendSms` actions down to plain replies; the backend also rejects an unowned
> `senderNumber`. The generator does not emit these unless explicitly asked — see
> [generator-contract](./generator-contract.md) and [referenced-resources](./referenced-resources.md).

### 7.2 `guardrails`

**Do not emit guardrails — keep the array empty (`[]`).** They are **accepted and stored** by the config
API, but the runtime model carries **no `enabled` field**, so at runtime every stored guardrail
deserializes to `enabled=false` and is **silently skipped** — the feature is not yet honored end-to-end.
Put always-on safety rules in the `goalPrompt` `## Guardrails` prose section instead (behavioral §2.1). The
bundled validator warns (`guardrails-inert`) on any non-empty array.

Shape, for reference only — if one is ever populated, `enabled`, `when`, and `reply` are all required and
each carries the same `enabled` contract as scenarios (missing → `422` on save):
```jsonc
[ { "enabled": true, "when": "the customer uses abusive language", "reply": "I'm here to help respectfully; let's keep it civil." } ]
```

---

## 8. Export wrapper metadata (`VoiceAgentV2ExportPayload`)

A clipboard export = the v2 body **plus** two frontend-only provenance tags (do not author):
```jsonc
{ /* ...all v2 fields... */ "companyId": 12345, "environmentName": "production" }
```
- **Export-only tags — omit both keys from a generated write payload.** They are provenance for the
  clipboard, not config fields: the API ignores them (used only for cross-account-import detection, next
  bullet) and the validator tolerates them as INFO `export-tag`, never an `unknown-field` error — but a
  clean, schema-only body still carries neither (§9).
- On import, if `companyId`/`environmentName` differ from the target, the dashboard treats it as a
  **cross-account** import and strips/replaces company-scoped references (chiefly the outbound number
  IDs, and the `toolCall`/`sendSms` actions). Editing your own agent is same-company — nothing is stripped.
- **Connected mode rarely needs the clipboard flow at all:** `cloudtalk_get_voice_agent` returns the full
  config document — no export tags to strip. Always **get → modify → update**
  ([mcp-tools](./mcp-tools.md)).

**Why the outbound number IDs are `environment` (never invented):** they are environment-specific and not
portable, and **there is no "Random"** — only `1` (Automatic) is magic; every other value, including `2`, is
a literal ID the company must own. **The config save stores exactly what you send and does not auto-pick a
number**, so `1` on its own is not save-ready — it needs a real owned failover to complete it, and any
specific number id must be **real ground truth**:

- `defaultOutboundNumberId` **defaults to `1` (Automatic), exactly as the dashboard seeds it.** Setting a
  specific number instead means a real owned id — reuse the agent's current value when editing, fetch one
  (`cloudtalk_list_numbers`), or ask the user. A guessed `2` overwrites a working number and the save is
  refused **by name** (a `400`), with no self-heal.
- With Automatic (`1`), pair it with a real owned `failoverOutboundNumberId` **in both directions** —
  the save `400`s without it (there is no inbound carve-out, and nothing fills it in for you). Completing
  that failover is the FE-faithful path (connected: `cloudtalk_list_numbers`; offline: the dashboard).

The same "owned by this company" caveat applies to every
company-scoped reference (`toolReferenceId`, `agentId`, `groupId`, `knowledgeBaseIds`, `senderNumber`,
`integrationId`/`calendarId`) — [referenced-resources](./referenced-resources.md) covers each.

---

## 9. Validating a draft

- **Run the bundled validator before every save:**
  [`scripts/validate_config.py`](./scripts/validate_config.py) (structural + dependency rules + the
  behavioral §8 lints). It also enforces **paste-ready**: any non-schema key (including a
  `_requiredResources` block) or any placeholder/sentinel ID is an **error to fix** — the body must be
  schema-only and run as-is. Or check by hand against this doc + `fields.json` + the dependency rules
  (§3, §6, §7).
- **The platform check is the save itself.** In connected mode there is no separate validate tool: the
  confirm-gated write (`cloudtalk_update_voice_agent` / `cloudtalk_create_voice_agent`) validates the
  document and returns the platform's verdict — so the local validator runs first, and the write is the
  authority ([mcp-tools](./mcp-tools.md)). Offline, the dashboard's Expert-Mode save plays the same role:
  a violation comes back as a `400`/`422` with a descriptive message.
- **Omit the export tags.** When the draft came from a clipboard export, drop `companyId` and
  `environmentName` (§8) from the write payload. They are tolerated, not rejected — the validator reports
  them as INFO `export-tag` (never an `unknown-field` error) and the API ignores them (using them only for
  cross-account-import detection) — but a clean paste-ready body carries neither.
- **Unknown keys are NOT caught by the save — they are silently dropped.** The create/update save relaxes
  `additionalProperties` and drops an unknown or misspelled key (nested ones too): the field just vanishes,
  unremarked, so a typo is *lost*, not flagged. Only the `/validate` endpoint and this local validator
  reject them (`UNKNOWN_FIELD`) — which is exactly why running the validator matters, since it is the only
  thing that surfaces a typo before it is silently dropped.

---

## 10. `elevenLabsSettings` — ElevenLabs advanced tuning  (ElevenLabs-only)

Optional object exposing ElevenLabs `conversation_config` knobs. Meaningful only when the resolved
provider is `elevenlabs` (ignored on Deepgram). Every knob is **omit-to-let-provider-default**: leave a
field unset to accept ElevenLabs' own default, and set one **only to solve a specific problem** —
turn-taking that cuts callers off or lags, background noise/voices, mis-heard brand names, backchannel
that interrupts, or ambience. **When to reach for each, and what values to pick:** behavioral §7a-bis
(values) and §9 (when).

```jsonc
"elevenLabsSettings": {
  "speculativeTurn": true,            // start composing the reply before the caller finishes — cuts perceived latency
  "turnEagerness": "normal",          // how readily the agent takes its turn: "patient" | "normal" | "eager"
  "turnModel": "turn_v2",             // turn-detection model version: "turn_v2" | "turn_v3"
  "vad": true,                        // ignore background voices (TV, bystanders) so they don't trigger a turn
  "asrKeywords": ["CloudTalk", "VoIP"], // boost speech recognition of these niche words/phrases
  "interruptionIgnoreTerms": ["...", "..."],      // caller acknowledgements that must NOT count as an interruption (in the caller's language)
  "interruptionIgnoreTermLanguages": ["en"],      // languages the ignore-terms are matched in
  "backgroundSound": {                            // ambient bed played under the agent's speech
    "preset": "office",                           // REQUIRED when backgroundSound is present (one of 9 presets)
    "volume": 0.3,                                // optional, 0–1
    "crossfadeLoop": true                         // optional, seamlessly loop the bed
  }
}
```

- The API enforces the `turnEagerness` / `turnModel` enums **and** `backgroundSound.preset`
  (required-when-present, the 9-value enum) and `backgroundSound.volume` (range `[0,1]`); the remaining
  sub-fields' types are unchecked server-side, so `validate_config.py` holds the line — each field above
  must have exactly the shape shown. `vad` is a flag, not an object: the nested `background_voice_detection`
  form is built server-side and is never accepted as input, and a wrong type is refused with a `422`. An
  undocumented sub-field — **including a nested one** under `backgroundSound` — is rejected by the
  `/validate` endpoint and this validator (`UNKNOWN_FIELD`, recursively), while the **save silently drops
  it** (§9).
- **`interruptionIgnoreTerms`** — short caller acknowledgements/backchannel that should not be treated
  as a turn-taking interruption (in the caller's language); **`interruptionIgnoreTermLanguages`** lists
  the languages those terms are matched in. Both are lists of non-empty strings.
- **`backgroundSound`** — an ambient bed played under the agent: `preset` (**required when the object is
  present**; one of `office`, `office2`, `restaurant`, `city`, `typing`, `elevator`, `elevator2`,
  `elevator3`, `elevator4`), `volume` (optional, `0`–`1`), `crossfadeLoop` (optional bool). Omit the
  whole object to play no bed.
- **`turn_v3` is safe** through this API: the ASR provider is pinned server-side to the one `turn_v3`
  needs (`scribe_realtime`) on every ElevenLabs payload — it is never yours to set.
- **Preserve-on-omit on PUT at the object level:** omit the whole object → stored settings kept; send
  it → it **replaces** the stored one (clear a sub-field by omitting it from the sent object).

---

## 11. `tone` and `verbosity` — identity presets

Two optional top-level fields that shape the agent's identity independently of `goalPrompt`. Both are
provider-agnostic (they apply whatever the resolved provider is). What to pick: behavioral §2.1.

### `tone` — how the agent should sound

A **flat `string[]`** drawn from a **fixed allowlist of exactly six labels** — **no free text**, no
nesting, no objects:

`professional`, `friendly`, `casual`, `calm`, `empathetic`, `direct`

Every element must be one of the six; anything else is rejected (error `bad-enum` at `tone[i]`).
**Duplicates are de-duplicated** on save — repeating a label does not strengthen it. Prefer one or two:
a blend expresses each preset more weakly than a single label, and only one- and two-label combinations
have been validated. `[]` or an omitted key means **unset**, which **self-heals to
`["friendly","direct"]`** server-side. Nuance beyond the six labels belongs in `goalPrompt` style
guardrails (behavioral §2.1), described as intent in the caller's language — not as quoted example lines.

### `verbosity` — how much the agent says

A single enum controlling response length — `concise` | `standard` | `thorough`:

- `concise` — the shortest useful answer.
- `standard` — balanced (the default).
- `thorough` — fuller, more detailed replies.

`""` or an omitted key means **unset**, which **self-heals to `standard`** server-side. Any other value
is rejected (`bad-enum` at `verbosity`). This is a length dial, not a substitute for the
response-guideline prose in `goalPrompt`.
