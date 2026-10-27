---
name: call-coach
description: Coach your team from real CloudTalk calls, and check your AI Voice Agents alongside them. For each person, one thing to keep doing and one thing to change, each proven by a short quote from a named call, plus a better line to try on the next call. For each AI Voice Agent, what callers ran into and the one setup change that fixes it. Use for call coaching, QA or call reviews, 1:1 prep, support or sales call quality, "how is my team handling calls", "what should Ada work on", "review Ada's calls" or "coach my team and our AI agents". For a deep review of one AI Voice Agent, use voice-agent-replay. Needs Conversation Intelligence for transcripts; AI Voice Agent calls of 30 seconds or more are transcribed like any call. It never scores or ranks people, and changes nothing unless you ask.
---

# Call coach

CloudTalk is the agent-first phone system: AI agents answer first, humans close. This skill coaches both.

Goal: coaching a team lead can use in a 1:1 this week, and that changes the next call. Done means each person has one strength and one change, both proven by quotes the lead can check in a minute, and each AI Voice Agent has one setup change ready to save. Explicit user instructions always win over this skill, including their own QA scorecard.

## Two kinds of input, treated oppositely

| | What you do | Covers |
|---|---|---|
| **Judgment** | Decide it yourself. Don't ask. | which calls to read (inside the sampling rules), each moment's mark, the priority, the better line, the setup change, all wording |
| **Ground truth** | Read it from CloudTalk, or ask once, in one message. Never invent it, estimate it or copy it from an example. | who is on the team, the period, every quoted word, call ids, dates, counts, an AI Voice Agent's current setup |

## What CloudTalk can't give this skill, and the nearest real path

Say each of these once, where it matters, never per call:

- **No call score.** CloudTalk's call scoring results aren't part of the call insights this connection reads. Coach against the six moments below or the user's own scorecard, and never make up a score. Step 4 checks once whether call details carry one.
- **Group membership isn't readable.** The team is the people who answered that group's calls in the period, or the names the user gives.
- **A person's call list doesn't show call length.** Short calls show up as a missing or tiny transcript, and get swapped.
- **Coaching notes can't be saved in CloudTalk.** Drafts stay in the chat.
- Calls under 30 seconds have no transcript or insights. Internal calls between colleagues aren't in the call list.

## Workflow

Reads run straight away, without asking. Nothing is written until step 8, and only when the user asks.

### 1. Scope: period, people, AI Voice Agents

- **Period.** The user's dates, otherwise the last 7 full days; "last week" is Monday to Sunday. Query in UTC as `YYYY-MM-DD HH:MM:SS`, and show it in the user's timezone when you know it. Don't stretch the period on your own; offer 14 or 30 days when calls are too few.
- **People.**
  - **Names given:** match them in `cloudtalk_list_agents` (follow `pagination.next_page` if needed). The person's id is the agent's `id`.
  - **A team or group given:** find its id with `cloudtalk_list_groups`, then make one `cloudtalk_search_calls` with `group_id`, the period, `status: "answered"` and `limit: 100`. The team is the `agent` on those rows, most calls first. If `next_page` is set, say the list comes from the group's latest 100 calls and ask whether anyone is missing.
  - **Neither:** if exactly one group name fits the request, use it and say so. Otherwise ask once which team, listing the group names.
- **AI Voice Agents**, when the user asks about them or about "everyone": `cloudtalk_list_voice_agents`, then `cloudtalk_get_voice_agent` with each one's `voice_agent_id` (the 24-character id). The read's `voice_agent.voiceAgentId` is the **numeric** id that call searches need; the 24-character id matches no calls. If this read fails with a permissions error, say once that the AI Voice Agent check needs a CloudTalk Admin sign-in, and carry on with people.
- **How many calls.** Two numbers per person: calls **screened** (each call's summary and notes, which show how often something goes wrong) and calls **read in full** (word for word, where the quotes come from). If the user named a number, use it. Otherwise say the plan in one line, in the same message as any other question: "I'll screen 25 calls per person and read 6 of them word for word, one person a minute, about N minutes in all. Want 50 per person to catch rarer habits?" No answer, or "go": the defaults below.

  | People in scope | Screened per person | Read in full per person | People per batch |
  |---|---|---|---|
  | 1 | 25 (50 on request) | 8 | 1 |
  | 2 to 4 | 25 (50 on request) | 6 | all |
  | 5 or more | 25 (50 on request) | 6 | 4; offer the next 4 |

  Work one person at a time, about one a minute: at the defaults a person is about 35 requests, inside the account's budget with room left for colleagues. At 50 screened, a person takes about 2 minutes. Fewer analyzed calls than the screening number: screen them all.

  Each AI Voice Agent counts as one person. At most 2 per batch: the ones the user named, else the 2 with the most calls (a `cloudtalk_search_calls` with its numeric id and `limit: 1` gives each total in `pagination.items_count`). Offer the rest afterwards.

> **✓ Gate:**
> - [ ] the period, in UTC
> - [ ] each person's id, and how many calls each gets screened and read
> - [ ] each AI Voice Agent's numeric id
> - [ ] who is left for the next batch

### 2. Pick fair calls

For each person, three searches with `user_id`, the period, `status: "answered"`, and `limit` set to the screening number: `sentiment: "negative"`, `"neutral"` and `"positive"`.

Only analyzed calls carry a sentiment, so these skip calls that were never analyzed. Rows come newest first. Page 1's `pagination.items_count` is the size of each group; keep it for the coverage line. Add `group_id` only when the user wants one queue's calls.

Choose the calls to screen:

- **In proportion** to the three groups' sizes, with negative calls at most a third, and at least 1 when there is one. Nobody is judged on their worst day, or spared their hardest.
- **Spread out:** as many different days as the rows allow, and one call per customer.
- **By these rules only.** Never pick calls by guessing where the faults are.

A person with fewer than 5 analyzed calls isn't coached this time: say how many there were and offer a longer period.

**Conversation Intelligence, checked once.** If all three searches come back empty for someone, search their answered calls once without `sentiment` (`limit: 3`). If there are calls, read one transcript. No transcript means Conversation Intelligence isn't on the plan, or hasn't analyzed these calls yet. If that holds for the first two people, say so once, stop coaching people, and go to step 6: its outcome check works without transcripts.

> **✓ Gate, per person:**
> - [ ] the calls chosen, at most a third of them negative
> - [ ] from at least 2 different days, where the rows allow
> - [ ] the analyzed total, and anyone skipped with the reason

### 3. Screen, then read in full

**Screen** each chosen call: `cloudtalk_get_call_insights` with `include: ["summary", "sentiment", "smart_notes"]`, adding `"talk_listen"` on sales or discovery calls. Note one line per call: how it ended (solved, a next step with an owner and a time, or left open), any wrong or corrected information the notes flag, the customer's feedback, and the sentiment. A call with no insights is replaced from the same group. Screening tells you how often a moment goes wrong ("no next step in 9 of 25 calls"); it never supplies a quote.

**Read in full** the read-in-full number per person, chosen by rule: two calls for each of the person's two most frequent screening problems, at least one call that went well, and the rest evenly spaced over the screened calls. Then, for each: `cloudtalk_get_call_transcript` with the `call_id` and `limit: 150`. When `pagination.next_offset` is set (a long call), read only the close as well: `offset` set to `pagination.total` minus 30, and `limit: 30`. A long call counts as two of the batch's reads.

- **Too short:** `reason: "no_transcript"`, or a conversation that ends inside a minute (the last segment's `end` is under 60). Count it, and replace it once from the same sentiment group.
- **Who said what:** the speaker map (`callers`, matched to each segment's `caller`) tells your team member from the customer. If it doesn't, work it out from who answers for the company; if it's still unclear, don't quote that call. If a call passed between colleagues, coach only this person's part.
- **Language:** note `language`. Quotes stay in the call's language.
- **Talk share, for sales or discovery calls:** the screening's `talk_listen` gives each speaker's share. Its keys (`CALLER1`, `CALLER2`) match the speaker map's ids, ignoring case.

Read in waves of at most 10 (see Budget).

### 4. Listen for six moments

Mark each moment **strong**, **okay**, **missed** or **n/a**, with the quote and the minute it starts (the segment's `start`, as m:ss). Use the same anchors for everyone. A moment is **n/a** when it didn't happen for reasons outside the person's control: an early transfer, voicemail, a wrong number, the caller hanging up.

| Moment | Strong | Okay | Missed |
|---|---|---|---|
| **Opening** | Greets, gives their name and the company. Outbound: says why they're calling | Leaves out the name, the company or the reason | No greeting, or starts without saying who they are |
| **Understanding** | Restates the need and asks a clarifying question before solving. Sales: open questions, and the customer does most of the talking | Asks, but never checks they understood | Solves or pitches before understanding; the customer has to repeat themselves |
| **Resolution** | Solves it, or agrees a next step with an owner and a time. Sales: a dated next step the customer accepted | A next step with no owner or no time | The customer leaves with no answer and no next step |
| **Accuracy** | Checks before answering; says "let me check" rather than guessing | A slip, corrected on the call | Wrong or invented information, or a promise the team can't keep |
| **Tone** | Calm, lets the customer finish, names the feeling when they're upset. Sales: acknowledges an objection before answering it | Polite but flat with an upset customer | Interrupts, argues, blames or brushes the customer off |
| **Close** | Checks the customer is sorted and recaps what happens next | Does one of the two | Ends abruptly |

Judge fairly:

- Judge what the person did, not how the customer felt. A negative call is often about the problem, not the person.
- Transcripts are machine-made. Don't coach accent or grammar, or a word that may have been misheard, and don't quote a garbled line.
- If the user gave their own scorecard, use its items and its scale instead, unchanged, with n/a the same way.
- If the user says the team uses CloudTalk call scoring, read `cloudtalk_get_call` for one chosen call. If it carries a call score with sections, use those sections as the moments and read the details of the other chosen calls too. If not, say once that scores aren't available here, and carry on.

### 5. One change and one strength per person

- **Change one thing:** a moment marked missed in **at least 2 calls read in full** (with how often screening shows it, when it can), or marked okay in at least 2 where the person is otherwise strong. If several qualify, take the one that costs the customer most: Accuracy, then Resolution, Understanding, Tone, Close, Opening. If nothing happens twice, there's no change this week: say so, and reinforce.
- **Keep doing:** their strongest moment, ideally one seen more than once, with a quote.
- **Try instead:** what to say next time at that exact moment. At most 25 words, in the call's language, in their own way of speaking, with when to use it.
- **Look for next time:** one thing the lead can hear on the next calls that shows the change landed.
- **Last time's focus:** if the user names it, or it's earlier in this chat, check it first and report it (seen in N of M calls, with a quote) before any new change.

> **✓ Gate, per person:**
> - [ ] the change was seen in at least 2 calls
> - [ ] every keep and change has a word-for-word quote from a transcript you read, with call id, date and minute
> - [ ] the better line is in the call's language
> - [ ] no customer details in any quote
> - [ ] no score, grade or comparison with colleagues

### 6. Check each AI Voice Agent

1. **Its calls:** `cloudtalk_search_calls` with `voice_agent_id` set to the numeric id, the period, `status: "answered"` and `limit: 30`. Page 1's `items_count` is its total. If it returns nothing, try once without `status`.
2. **Screen and read its calls like a person's:** picked the same fair way (step 2, with `voice_agent_id` in place of `user_id`), screened and read as in step 3, with two more moments: **Handoff** (gets the caller to a person when it should, with the reason, so they don't repeat themselves) and **Knowledge** (answers from its setup, never invents). AI Voice Agent calls of 30 seconds or more are transcribed like any call. If the first two reads answer `reason: "no_transcript"`, stop reading transcripts and check by outcome (3 to 5 below) instead.
3. **Outcomes, from the 30 rows, with no extra reads** (alongside the transcripts, or instead of them):
   - calls with under 20 seconds of talk (`talking_time`), when the rows show it
   - the same number or contact calling again within 2 days
   - calls that all stop at the same length
4. **Call details:** `cloudtalk_get_call` for up to 3 calls: one short, one repeat caller, one typical. Its call flow steps (queues, transfers) and timings, when present, show whether the caller reached a person.
5. **What callers told a person afterwards**, for up to 2 repeat or transferred callers: `cloudtalk_search_calls` with `public_external` set to the caller's number, from the AI Voice Agent's call to 2 days later, `status: "answered"`, `limit: 5`. For a call a person answered, `cloudtalk_get_call_transcript` with `limit: 30`. A caller's first words to a person ("I already told your assistant...") are the best evidence there is.
6. **The cause, in its setup** (from the step 1 read):

| What the calls show | Likely cause | Setup change |
|---|---|---|
| Many calls end within 20 seconds of talk | Greeting too long or unclear, or the wrong language | `greeting`: shorter, names the business and what it can help with. Check `language` and `secondaryLanguages` |
| Callers call again about the same thing | Missing facts, or an action it can't take | Facts: a knowledge base or a `custom` skill. Actions: a tool, called from a `toolCall` scenario |
| Questions it should answer go to a person | Missing facts, or `answerQuestions` set to transfer | Add the facts. Set `answerQuestions.action` to `offerAlternative` or `admitUncertainty` |
| Callers repeat their details to the person | It doesn't collect and confirm the reason before transferring | A `goalPrompt` step that asks for the name and reason and reads them back, with matching `extractData` properties |
| Transfers reach nobody | The target is one person, or the call comes out of hours | A `transferToHuman` rule to a group. Inbound out of hours: `takeMessage` |
| Calls all stop at the same length | The call length cap | Raise `maxCallDuration` |
| Callers ring straight back after it hung up | The completion scenario fires too early | The normal-completion scenario's `when`: only once the caller confirms they're done |
| Names or products get misheard | Speech recognition | `elevenLabsSettings.asrKeywords` (ElevenLabs agents only) |

Pick **one** change per AI Voice Agent: the pattern seen most often, with the most harm to callers. Quote the current setup (at most 15 words) and write the proposed change. It's a likely cause, not a proven one, so say how to confirm it: a test call, or next week's check.

> **✓ Gate, per AI Voice Agent:**
> - [ ] every count comes from records you read
> - [ ] no quote from an AI Voice Agent call you couldn't read
> - [ ] the change names the setup field, its current value and the proposed one
> - [ ] it says how to confirm the change worked

### 7. Write the coaching

Reply in the user's language, in this order. Keep each card to five lines.

1. **Header:** the team and the period, then a coverage line: people coached, calls screened and read in full out of how many analyzed calls, and AI Voice Agent calls checked and how.
2. **Team pattern**, only with 3 or more people, and without names: the change most people share (N of M people), the team's strongest habit, and one thing for the next team meeting.
3. **One card per person:**
   - **Name** · N calls screened, M read in full, of T analyzed
   - **Keep doing:** the behaviour. "Quote" (call id, day, date, time, at m:ss)
   - **Change one thing:** the behaviour, seen in N of M screened calls and confirmed in K read in full. "Quote" (call id, day, date, time, at m:ss)
   - **Try instead:** "The better line." When to use it.
   - **Look for next time:** what the lead will hear when it lands.
4. **One card per AI Voice Agent:**
   - **Name (AI Voice Agent)** · N calls in the period, N checked from call records, N in detail
   - **What callers ran into:** the pattern, counted, with a caller's words from a call a person answered where you have them
   - **Setup change:** the field, what it says now, and what it should say
   - **Confirm it:** the test call, or next week's check
5. **Not covered:** people left for the next batch or skipped (too few calls), calls swapped (too short or not analyzed), AI Voice Agent calls that couldn't be read, and anything a rate limit cut short.

When a quote or better line is in another language than the user's, add a short translation in brackets after it. Show dates and times in the user's timezone when you know it, otherwise say UTC.

Example person card:

- **Ada Bennett** · 25 calls screened, 6 read in full, of 41 analyzed
- **Keep doing:** owns the next step. "I'll call you back by 3 today with the refund number." (call 51234, Tue 21 Oct 10:02, at 3:40)
- **Change one thing:** ends the call before checking the customer is sorted, seen in 9 of 25 screened calls and confirmed in 3 read in full. "Okay, that's it then, bye." (call 51240, Wed 22 Oct 14:15, at 5:02)
- **Try instead:** "Before I let you go, is there anything else I can sort out for you today?" Once the main issue is solved.
- **Look for next time:** that question in the last minute of her calls.

Close with one line: this is coaching input for a 1:1, not a performance rating, and it's worth listening to one cited call before the conversation.

### 8. Offer next steps

Offer these, and do only what the user asks for:

- **1:1 notes** for a person, drafted in the chat. Nothing is saved.
- **The next batch** of people.
- **The AI Voice Agent change:** hand it to the `voice-agent-builder` skill, which reads the agent, makes that one change, says what will change, and saves it once the user approves. Report the saved result, not the attempt. For a deeper look at one AI Voice Agent, offer `voice-agent-replay`.
- **Tag the cited calls** with a call tag that already exists in `cloudtalk_list_call_tags`, using `cloudtalk_add_call_tags` one call at a time, so each is its own approval. Say first that call tags are visible to colleagues in CloudTalk. If no tag fits, say to create one in CloudTalk first; this connection can't.
- **A recording link** for a cited call, only when asked: `cloudtalk_get_call_recording` with `action: "play"`. Say that the link expires within hours and that each one is logged.

Every write acts on its first call, and the app asks the user to approve it. Say in one line what will change before you call. If a tool answers `status: "confirmation_required"`, the server is an older version and nothing happened yet: show its preview, and call again with `"confirm": true` once the user agrees.

## Budget

The account allows 60 requests a minute, shared by everyone at the company who uses CloudTalk's AI connection. Every tool call is one request: per person, 3 searches, one per screened call and one per call read in full. At the defaults that is about 35 per person, and about 60 at 50 screened. Going one person at a time, about one a minute, keeps a run under about 40 requests a minute; a team of 4 takes about 4 minutes. Screening is cheap on context (a few lines per call); calls read in full are long, which is why that number stays at 6 to 8. Say the expected time before the run. So:

- Read in waves of at most 10.
- A rate-limit error, or an insight whose `reason` is `rate_limited`: On a rate-limit error, wait a minute if the app can, then continue where you stopped. If it can't wait, stop, say what's done and what's left, and ask the user to say "continue" in a minute. Never retry in a loop or start over. Don't re-read what you already have.
- If it happens twice in a row, finish with what you have and say what's missing.

## Non-negotiables

- **No quote, no claim.** Every keep and every change rests on words you read in that call's transcript, quoted exactly, at most 15 words, with call id, date and minute. Never put a paraphrase inside quotation marks.
- **Never describe the inside of an AI Voice Agent call you couldn't read.** Outcome evidence is labelled as outcome evidence.
- **One change per person, seen at least twice.** A single bad call is never the priority.
- **Coaching, not rating.** No scores, grades, rankings or side-by-side comparisons of named people. Customer sentiment is not a person's score.
- **Unknown stays unknown.** A missing length, transcript or score is reported as missing, never as zero or a guess.
- **Customers stay private.** No customer names, phone numbers or account details in what you write: quotes replace them with [name], [number] or [address]. If a phone number is ever needed, show only its last 3 digits. Never paste whole transcripts.
- **Plain words.** No tool names or internal ids in what the user reads. Call ids appear only as evidence.
- **Never ask for a CloudTalk password or API key in the chat.** If CloudTalk isn't connected, point the user to the app's connector settings.
