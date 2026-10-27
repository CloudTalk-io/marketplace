---
name: voice-agent-replay
description: Improve a live CloudTalk AI Voice Agent from its real calls. Reads the agent's setup and a sample of its recent calls, flags where it failed (left the caller unresolved, repeated itself, made something up, missed a handoff to a person, frustrated the caller, lost the caller early), groups the failures by cause with two quoted calls as proof, and points each cause at the setup change that fixes it. Saves changes only when the user asks, with their approval. Use when the user asks how their AI Voice Agent is doing, why it fails, loops or loses callers, to review, replay or QA its calls, or to improve it after go-live. Needs AI Voice Agents, Conversation Intelligence for transcripts and insights, and a CloudTalk Admin sign-in to read and save the setup.
---

# AI Voice Agent replay

CloudTalk is the agent-first phone system: AI agents answer first, humans close. This skill replays what one AI Voice Agent actually did on its calls and turns its failures into setup changes.

Goal: a short list of causes, each proven by two real calls and tied to the one setup field that fixes it. Done means the user knows what to change, why, and how to check it worked, and the change is saved if they asked for it. Explicit user instructions always win over this skill.

Reads run straight away. Nothing changes on the agent until the user asks for a change and approves the save.

## Two kinds of input, treated oppositely

| | What you do | Covers |
|---|---|---|
| **Judgment** | **Author it.** Don't interview the user. | the sample, which flags apply, how failures group into causes, the ranking, the wording of each proposed change |
| **Ground truth** | **Read it from CloudTalk or ask, in one batch.** Never invent it, default it or copy it from an example. | which agent, the period, what was said on a call, the agent's current setup, any fact the agent should know (prices, hours, policies), any transfer target, the number for a test call |

A caller's words prove a failure. They are not ground truth for the fix: when the agent lacked a fact, the correct answer comes from the user.

## Bundled references, load on demand

They live in this plugin's `voice-agent-builder` skill.

| File | Read it for |
|---|---|
| `../voice-agent-builder/mcp-tools.md` | *Two ids, one name*, *Write safety*, *Test calls* |
| `../voice-agent-builder/generator-contract.md` | *Connected mode*: the write contract every save follows |
| `../voice-agent-builder/behavioral-guidance.md` | what each setup field does to behavior, and the §8 self-check for a changed setup |
| `../voice-agent-builder/schema.md` | field shapes and allowed values when you change a field |

## Workflow, follow in order

### 1 · Pick the agent and the period

- Call `cloudtalk_list_voice_agents` with `limit: 200`, and follow `pagination.next_page` until it is null before saying an agent doesn't exist. Match the name the user gave. One agent on the account: use it. Several that fit, or none named: ask, listing names and direction (inbound or outbound). A list is a question for the user, not a pick for you. One agent per run.
- The id this list returns (key `voice_agent_id`, 24 hex characters) is the **config id**. It reads and saves the setup. It finds no calls.
- Period: the user's dates, else the last 7 days, from midnight UTC 7 days ago to now, written `YYYY-MM-DD HH:MM:SS` in UTC. One search spans at most 92 days and a wider one is rejected, so split it or ask to narrow it. After an earlier change, start at the time it was saved and say so.

> **✓ Gate:**
> - [ ] one agent, confirmed by name
> - [ ] its config id
> - [ ] the period, in UTC

### 2 · Read the setup

- Call `cloudtalk_get_voice_agent` with `voice_agent_id` set to the config id. Keep `voice_agent.voiceAgentId`: that number is the **numeric id**, the only id that finds this agent's calls (`mcp-tools.md` *Two ids, one name*).
- Note what you will judge the calls against: direction, `language`, `greeting`, `goalPrompt` (role, style, task steps, guardrails, ending), `skills.custom`, `skills.transferToHuman` (`enabled`, each rule's `condition` and `destination`), `skills.answerQuestions.action`, `scenarios` (each `when`, `reply`, `action`, `enabled`), `knowledgeBaseIds`, `temperature`, `maxCallDuration`, and `elevenLabsSettings` when `provider` is `elevenlabs`.
- When `knowledgeBaseIds` isn't empty, call `cloudtalk_list_knowledge_bases` with `limit: 200` and keep the linked ones: name, type, status, and `description` and `value` when filled. This is not a full copy of their content, so a claim you can't find here may still be in a knowledge base.
- A read refused for authorization means the sign-in lacks CloudTalk Admin rights, which reading a setup needs. Say so in plain words and stop.

> **✓ Gate:**
> - [ ] the numeric id in hand, not the config id
> - [ ] a short note of the setup: what the agent is for, its task steps, when it may transfer and whether transfers are on, how it ends calls, which knowledge bases are linked

### 3 · Find the calls

- Call `cloudtalk_search_calls` with `voice_agent_id` set to the **numeric id**, `date_from`, `date_to`, `status: "answered"` and `limit: 200`. Page 1 carries the total in `pagination.items_count`; later pages report it as null, so keep the page 1 figure. Follow `next_page` for at most two more pages (600 calls). Beyond that, the sample comes from the newest 600: say so, or offer a shorter period.
- Call it once more with the same filters plus `sentiment: "negative"` and `limit: 50`: the calls the platform already judged negative.
- Each row has `call_id`, `started_at`, `talking_time`, `total_time`, the contact and `external_number`. Use `talking_time` for the 30 second line: a call under 30 seconds has no transcript or insights, so count it and don't read it. A row with no `talking_time` stays in the pool; reading it tells you.
- No calls: say so, and check the period and the agent with the user. An inbound agent with no calls may not be routed to any number, which is set in the Dashboard only.

> **✓ Gate:**
> - [ ] answered calls in the period, from page 1
> - [ ] how many ended under 30 seconds, or "unknown" when the rows carry no duration
> - [ ] the negative list, and the pool of everything else

### 4 · Read a sample

The sample is **25 calls with insights**. A failure that hits 1 call in 5 shows up at least twice in 97 of 100 such samples, and one that hits 1 call in 10 in about 3 of 4. That finds the problems that matter most and fits the budget below. Rarer problems may not show, and the coverage line says so.

- **Pick:** calls the user named, first. Then up to 8 from the negative list, then fill to 25 from the pool, evenly spaced over it (every *n*-th call), so every day of the period counts, not only the newest. With 25 or fewer, read them all.
- **Insights:** for each, `cloudtalk_get_call_insights` with `include: ["summary", "sentiment", "smart_notes"]`, in batches of at most 10, in parallel only where the app allows it. A field that comes back `null` has no insight. One that comes back with `reason: "rate_limited"` or `reason: "error"` is a failed read, not an empty one. A call with no insights doesn't count toward the 25: replace it with the next pick, up to 35 insight reads in all.
- **No insights at all:** when the first 10 reads have none, stop reading. Say once that this agent's calls carry no transcript or insights yet: they aren't analysed yet, or Conversation Intelligence isn't on the plan. Offer what still works: the user listens to a call they pick (`cloudtalk_get_call_recording` with `action: "play"`), or the `voice-agent-checkup` skill checks the setup without calls.
- **Transcripts:** `cloudtalk_get_call_transcript` with `limit: 300`, for at most 12 calls: up to 8 where the insights suggest a failure, and at least 4 that look fine, because repeating itself and making things up rarely reach a summary. Read a second page (`offset` set to `pagination.next_offset`) only when the end of the call decides a flag. `reason: "no_transcript"` is an answer, not an error: don't retry it, and use that call's summary instead, marked as a summary.
- Tell the AI Voice Agent from the caller with the transcript's speaker map: `callers` gives each speaker's `type` and `localIdentifier`, and each segment's `caller` points to one of them.

**Budget.** The account allows 60 requests a minute, shared by everything connected to it. This run makes at most about 55: setup 2 to 3, searches 2 to 4, insights up to 35, transcripts up to 12, plus a rare second transcript page. On a rate-limit error, wait a minute and continue where you stopped; don't start over.

> **✓ Gate:**
> - [ ] you can say how many calls you read and how you picked them
> - [ ] every call you will quote has a transcript, or is marked as summary only

### 5 · Flag what went wrong

Check every call you read for six failures. A flag needs evidence in that call, not a hunch.

| Flag | It counts when | Evidence |
|---|---|---|
| **Left unresolved** | the caller's need was not met and no next step was given | the summary or smart notes, or a call that ends without an answer or outcome |
| **Repeated itself** | the agent asked the same question or said the same line twice or more, or looped on a step | two or more matching agent turns in the transcript |
| **Made something up** | the agent stated a fact or promise (price, hours, availability, policy, a callback time) that its setup doesn't contain | the quote, checked against the greeting, instructions, custom skills, scenarios and knowledge bases from step 2 |
| **Missed a handoff** | the caller asked for a person, or a transfer rule's condition was met, and no transfer happened | the caller's request and what the agent did next |
| **Frustrated caller** | the caller showed it in words (repeats themselves, asks for a person again) or the sentiment is negative or very negative | a caller quote, or the sentiment verdict |
| **Early hang-up** | the caller hung up in the first exchanges, before the goal was reached and without a natural close | the last turns of the transcript |

- **Made something up** is the flag to be most careful with. When a linked knowledge base could hold the fact, mark it **unverified** and ask the user, rather than calling it made up.
- **Missed a handoff** comes in three kinds; note which. The transfer skill was off or had no rule for this case (a setup gap). It was on and the agent didn't use it (a wording gap). Or the agent tried and the transfer failed: the target may be wrong, and nothing checks a target until a live call uses it.
- On an outbound agent, a call that reached voicemail is not a failure unless the agent kept talking to it or never ended the call.
- Calls under 30 seconds can't be read. Report their count as possible early hang-ups, with no cause. When they are a large share of the calls, say so in the top line and suggest a test call to hear the opening.

### 6 · Group by cause, and map each cause to the setup

A cause is why the agent failed, named in setup terms, not the symptom. One cause often raises several flags: a missing opening-hours fact can show as made up, unresolved and frustrated on the same calls.

- Report a cause only with **at least two separate calls** as proof. A failure seen in one call goes under *Seen once*.
- At most 5 causes. Rank by calls affected, then by harm to the caller: made up, missed handoff, unresolved, early hang-up, frustration, repetition.
- Map each cause to the one field that fixes it (details in `behavioral-guidance.md`):

| Cause looks like | Field to change | Say it to the user as |
|---|---|---|
| Doesn't know a fact callers ask for | the fact in `goalPrompt` or a custom skill when short; a new knowledge base when long (over about 500 words) | the agent's instructions, or a knowledge base |
| States facts that aren't in its setup | a grounding rule in the `goalPrompt` `# Guardrails` section; `skills.answerQuestions.action` set to `admitUncertainty`; `temperature` back to the 0.5 baseline, never above 0.7 | a rule against guessing |
| Loops, asks again, or asks several things in one turn | the `goalPrompt` task steps: one question per turn, and what to do after two failed tries | the agent's task steps |
| Cuts callers off while they give numbers, names or spellings | `elevenLabsSettings.turnEagerness: "patient"` (ElevenLabs only) | how quickly it replies |
| Mishears names or products | a list of the right names in `goalPrompt`, mirrored in `elevenLabsSettings.asrKeywords` on ElevenLabs | words it should listen for |
| Doesn't hand off when it should | `skills.transferToHuman`: switched on, with a rule whose `condition` names the case (under 120 characters) and a real target | the transfer rules |
| Hands off what it could handle | a narrower transfer `condition`, or `skills.answerQuestions.action` not set to `transferToHuman` | the transfer rules |
| Promises a handoff it can't make | `goalPrompt` offers a callback while transfers are off | the agent's instructions |
| Loses callers in the first exchanges | `greeting`: short, names the business and the reason for the call | the greeting |
| Can't end the call, or keeps a finished call going | `scenarios` entries with `action: "hangup"` and `enabled: true` for the normal end, silence and, outbound, voicemail | the scenarios |
| Calls cut off mid-sentence at the same length | `maxCallDuration` set too tight | the maximum call length |
| Answers in the wrong language | `language`, or `secondaryLanguages` with `provider: "elevenlabs"` | the agent's languages |
| Cold, curt or rambling | `tone`, `verbosity`, and the style part of `goalPrompt` | tone, and how much it says |

> **✓ Gate:**
> - [ ] every cause has two calls of proof, one field, and the flags it explains

### 7 · Propose the changes

For each cause, one change: the field, what it says now (a short quote, or "nothing"), what it should say, and why that fixes the cause. Keep each change as small as the cause allows. Don't rewrite the whole setup.

- **Ground truth stays the user's.** A missing fact (a price, opening hours, a policy) comes from the user: ask for all of them in one message. A live transfer needs a real target with both its id and its extension. A person's come from `cloudtalk_list_agents`. A group's extension can't be read here, so it comes from the user. Without a target, transfers stay off and the instructions offer a callback.
- **Every change keeps the builder's rules** (`behavioral-guidance.md` §8): one question per turn, always-on rules written in the `# Guardrails` prose while the `guardrails` list stays empty, an explicit `enabled` on every skill and scenario, at least one hangup scenario, `optimizeStreamingLatency` never 4.
- **A knowledge base can't be edited after it's created.** Short facts go into the instructions or a custom skill, so the fix stays one save. A long one means a new knowledge base: `cloudtalk_create_knowledge_base` is a second write with its own approval, its id is then added to the full `knowledgeBaseIds` list in the save, and it needs `provider: "elevenlabs"`.
- Never apply the platform's optimized settings as part of a fix. Only when the user asks, and in a save of its own.

Then ask which changes to apply.

> **✓ Gate:**
> - [ ] each change is tied to a cause
> - [ ] no fact, id or number in a change that the user or a CloudTalk read didn't supply

### 8 · Apply, only when the user asks

Follow the connected-mode write contract (`generator-contract.md` *Connected mode*, `mcp-tools.md` *Write safety*):

1. Say in plain words which agent changes and, per field, what changes: before and after, one line each. Say once that the app will ask them to approve the save.
2. Call `cloudtalk_get_voice_agent` again, so you edit the current setup and not the copy from step 2.
3. Change only the agreed fields in that document. Collections are replaced whole (`skills`, `scenarios`, `guardrails`, `secondaryLanguages`, `knowledgeBaseIds`): to change one entry, send the full list. Carry forward `knowledgeBaseIds` (left out, every knowledge base is unlinked), `elevenLabsSettings` as a whole object, `provider`, `llm`, and `optimizeStreamingLatency` (left out, it resets to 0).
4. Save everything in **one** `cloudtalk_update_voice_agent` call with `voice_agent_id` set to the **config id**. It acts on that first call. An older server answers `status: "confirmation_required"` with a preview instead: nothing happened yet, so show the preview and call again with `"confirm": true` once the user agrees.
5. Report the result, not the attempt. `status: "updated"`: list `changed_fields` in plain words and hand over the `dashboard_url`. Surface any `voice_agent.error_codes` or `voice_agent.warnings` in plain words: saved is not clean. `status: "validation_failed"`: nothing was saved, so explain the error in plain words, fix it, and ask before saving again.

> **✓ Gate:**
> - [ ] the user asked for these changes
> - [ ] the saved document came from a fresh read
> - [ ] the result says it was saved

### 9 · Check that it worked

Note when the save happened (UTC), then offer two ways to verify:

- **A test call now.** Inbound: the user calls the agent's number and tries the case that failed. Outbound: `cloudtalk_trigger_aiva_call` with the **config id** and a number the user names, in E.164 (`+` then digits only). It places a real call, so the app asks them to approve it. Keep the call over 30 seconds so it gets a transcript, then find it with `cloudtalk_search_calls` (numeric id, period starting at the save) and read it as in step 4.
- **A later replay.** Run this skill again on calls after the save, once there are about 25 of them. The sampling is the same, so the counts per cause compare.

## Output

In the user's language, in this order:

1. **Top line:** the agent's name and direction, the period (in the user's timezone when known, plus the UTC times queried), and what was read: answered calls in the period, how many ended under 30 seconds, how many were sampled and how they were picked, how many transcripts were read.
2. **What went wrong:** one line per flag with its count, for example "Missed a handoff: 4 of 25 calls". These are counts in a sample, not a score for every call.
3. **Causes**, ranked, one block each:
   - **Cause:** one plain sentence.
   - **Flags:** which ones it explains, and in how many sampled calls.
   - **Proof:** two calls, each with its date and time, the call reference, and a quote of at most 15 words, saying who spoke. Evidence from a summary is marked "(summary)".
   - **Fix:** the part of the setup in plain words, what it says now, and what it should say.
4. **Seen once:** one line each.
5. **Proposed changes:** a numbered list to pick from, one per cause, plus any question about missing facts or transfer targets, in the same message.
6. **Not covered:** calls not sampled, calls under 30 seconds, calls with no insights or transcript, knowledge base content that couldn't be checked, and the part of the period left out when there were more than 600 calls.

After a save: what changed and the link (step 8), then the two ways to check it (step 9).

## Non-negotiables

- **No cause without two calls of proof.** Put only words that were said inside quote marks, and keep what you read apart from what you infer.
- **Calls take the numeric id, the setup takes the config id.** The config id finds no calls, and the numeric id reads and saves nothing.
- **No write the user didn't ask for.** Say what will change first, save once, and report the save's result, not the attempt.
- **Never build a save from memory.** Fresh read, change the agreed fields, send the whole document back. Leaving out `knowledgeBaseIds` unlinks every knowledge base.
- **Never put a fact, id or number into the setup that the user or a CloudTalk read didn't give you.** What a caller said, or what you guess the answer is, is not a fix.
- **Never place a test call to a number the user didn't name.**
- **Privacy:** quote only what proves the point, mask phone numbers to their last 3 digits, say "the caller" instead of a name, and never paste a whole transcript.
- **Plain words for the user:** no company ids, user ids or tool names, and setup parts named as in the last column of the table in step 6. No em dashes or en dashes. Never ask for an API key or password: CloudTalk is connected in the app's connector settings.
