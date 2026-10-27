---
name: missed-call-follow-up
description: Make sure no missed caller waits. Finds today's missed CloudTalk calls (or those since the last run), groups repeat tries by caller, drops anyone the team has reached since, looks up who each caller is, and drafts a short text back from their history, in their language where it is known. Sends only the texts the user approves, or hands routine callbacks to an AI Voice Agent. Use when the user asks who called and didn't get through, who is waiting for a call back, to text back missed calls, to clear today's missed calls, or to check missed calls twice a day. For a weekly look at everything still owed after calls, use conversation-insights instead. Sending needs a CloudTalk number with SMS enabled; callbacks need AI Voice Agents; call summaries need Conversation Intelligence.
---

# Missed call follow-up

CloudTalk is the agent-first phone system: AI agents answer first, humans close. A missed call is a customer left waiting. This skill closes that gap the same day.

Goal: every caller missed in the period ends up in one of five places, and the user can see which: reached already, texted, queued for an AI Voice Agent callback, held until business hours, or skipped on the user's say. Explicit user instructions always win over this skill.

This is same-day action on missed calls. If the user wants the week's open loops from answered calls too, hand over to `conversation-insights`.

## Two kinds of input, treated oppositely

| | What you do | Covers |
|---|---|---|
| **Judgment** | Decide it yourself. Don't ask. | the ranking, the wording of each draft, which reply suits each caller (a text, an AI Voice Agent, or a person), the language when the evidence shows it |
| **Ground truth** | Read it from CloudTalk, or ask, all in one message. Never invent it, default it or copy it from an example. | the business name callers know, business hours and timezone, who not to contact, anything a text promises (a callback time, a price, an offer, a link), the line to text from, each caller's number and history, who was reached already |

CloudTalk doesn't hold the business name customers know: ask for it unless the user already said it. Ask for business hours and the timezone only if you don't know them. Reads run first; then ask what's missing in one short message, next to what you found ("7 callers are waiting. Before I draft texts: what name do your customers know you by, and what are your opening hours?"). If you'd reach for a placeholder, ask instead.

## Workflow

### 1. Set the period

- **Default:** today, from midnight in the user's timezone to now.
- **"Since the last run" or "since I last checked":** start where the previous run in this conversation ended, or at the time the user names. A scheduled run starts at the previous scheduled run (step 8). If you don't know the start, ask; never guess.
- Pass every date to CloudTalk in UTC as `YYYY-MM-DD HH:MM:SS`. Show the period to the user in their timezone.

"Today" leaves out calls that came in last night after closing. On the first run of the day, say so in the coverage line and offer "since yesterday at closing time".

### 2. Find the missed callers

- Call `cloudtalk_search_calls` with `status: "missed"`, `direction: "incoming"`, `date_from`, `date_to` and `limit: 200`. Page with `page` while `pagination.next_page` is set, at most 5 pages. `pagination.items_count` comes on page 1 only; keep that figure.
- Group the rows by `external_number`, compared digit for digit (ignore spaces, brackets and a leading +). For each caller keep: the number of tries, the latest missed time (`started_at`), the contact name if there is one (`contact.name`), and the `call_id` of the latest missed call.
- A row with no `external_number` is a hidden number. Count those; nobody can text or call them back.

### 3. Drop callers already reached

A caller is **reached** when an answered call with the same number, inbound or outbound, started after their latest missed call.

- Call `cloudtalk_search_calls` with `status: "answered"` and no direction, `date_from` set to the earliest missed call, `date_to` now, `limit: 200`.
  - Page 1 says 600 calls or fewer (`items_count`): page through all of them and match numbers.
  - More than 600: stop paging. Check each caller you look up in step 4 on its own instead: `cloudtalk_search_calls` with `public_external` set to their number, `status: "answered"`, `date_from` set to their latest missed call, `limit: 1`. Any row means reached.
- Call `cloudtalk_search_calls` once more with `status: "missed"`, `direction: "outgoing"`, the same window, `limit: 200`. A missed outgoing call to a caller after their miss means someone tried to call back and didn't get through. Keep that caller on the list and note the time: the text should say "we tried to call you back".
- In the same conversation, remember who you texted or queued. On a later run, show them as "Texted at 12:05" and draft again only if they called again after that.

> **✓ Gate: before ranking**
> - [ ] the search covered the whole period, or the coverage line says where it stopped
> - [ ] only incoming missed calls; repeat tries grouped into one caller
> - [ ] every caller with a later answered call, either direction, is dropped and counted
> - [ ] hidden numbers are counted, not listed

### 4. Rank, then look up the top 12

Rank the open callers:

1. tried 2 or more times
2. a known contact (a `contact` on their call)
3. a new number

Within each group, the longest wait comes first (the earliest latest-missed call).

Look up at most **12 callers** per run, from the top. The rest are counted under "Not on this list", and the user can ask for the next 12. For each of the 12:

- If step 3 switched to one-by-one checks, run that check first. A reached caller is dropped before any other read, and the next caller in the ranking takes the place.
- `cloudtalk_get_contact_interactions_summary` with `phone` set to the caller's number in E.164 (a leading + and digits; never a 00 prefix), `max_calls: 20` and `sample_size: 2`. It gives the contact's name and company, `interactions.last_contact_date`, and `ai.recent_summaries` for their two latest answered calls. For how many calls they've had, use `window.calls_total_in_window`, never `interactions.calls_analyzed` (that is the 20 read). `contact: null` with `reason: "no_contact_with_phone"` means a new caller. `ai.degraded.incomplete: true` means some summaries couldn't be read: say so on that entry.
- `cloudtalk_get_call` with the latest missed `call_id`. Read `internal_number` (the line they called: its `name` and `number`) and `out_of_office` (true when they called while you were closed).
- **Language, only when it changes the draft:** `cloudtalk_get_call_transcript` with `limit: 1` on the `call_id` of their latest summary returns the call's detected `language`. At most 5 per run, first for callers whose country code differs from the business's.

Then re-rank the 12. Move up a caller whose last call went badly or left something open (a complaint, a cancellation, a billing or access problem, a promise we didn't keep). Tone alone never moves anyone.

Calls under 30 seconds have no transcript or summary, whether a person or an AI Voice Agent took them. Empty summaries on longer calls mean Conversation Intelligence isn't on the plan, or the call isn't analyzed yet. Say so once, not per caller.

> **✓ Gate: before drafting**
> - [ ] at most 12 callers looked up; the rest counted
> - [ ] each lookup used the caller's own number from the call log
> - [ ] with more than 600 answered calls, each looked-up caller was checked on its own, and reached ones dropped

### 5. Pick the reply, then draft it

Suggest one reply per caller:

- **Text:** the default.
- **AI Voice Agent callback:** a routine callback (a new caller, a simple question, a booking) when the account has an outbound AI Voice Agent built for it. Call `cloudtalk_list_voice_agents` once (`limit: 50`) and keep the agents whose `direction` is outbound; it takes no direction filter. Check with `cloudtalk_get_voice_agent` (its `voice_agent_id`) that the setup fits a callback to someone whose reason for calling it won't know. Ask if several fit. None fits: don't offer it, and mention once that you can help set one up with the `voice-agent-builder` skill.
- **A person calls back:** a complaint, a cancellation, a billing, access or legal issue, a deal in progress, or a last call that went badly. Draft a short holding text too, so the caller hears from you today.
- **Hold:** it's outside business hours now (step 7).
- **Skip:** the user said not to contact them.

**The line to text from.** Call `cloudtalk_list_numbers` once per run (`limit: 200`). Use the line the customer called (match `internal_number.number` to `caller_id_e164`) when its `sms_supported` is true. If it isn't, use another line with `sms_supported: true`, from the same country if there is one, and say which line and why. No line can send texts: draft nothing to send, say so, and offer an AI Voice Agent callback or a person instead.

**Draft rules:**

- Name the business the way the user gave it. Use the caller's first name only when the contact has a real person's name.
- Say you missed their call. If `out_of_office` was true, say you were closed. If someone tried to call back, say so.
- Use their history only when it's harmless and helps: "about your delivery" is fine; amounts, health, account or order details are not, because anyone holding the phone can read a text.
- Offer a next step the user can keep: reply to this text, or call back on this number (only when the line takes calls, `voice_supported: true`). Nothing more unless the user gave it: no callback time, price, offer or link.
- Write in the caller's language when you know it: the detected language of their last call, or their own earlier texts. A country code is not a language. Otherwise, write in the business's language.
- Keep it under 160 characters where you can (one text), never over 300. Plain words, no emoji, no em dashes or en dashes, no placeholders.

The shape, not a template: a greeting, the business name, sorry we missed your call, the next step. Write each one fresh for the caller.

### 6. Show the list

Reply in the user's language. In this order:

1. **Top line:** the period in the user's timezone, then: missed calls and callers found, already reached, hidden numbers, and how many are on this list.
2. **The list**, ranked and numbered, one entry per caller:
   - **Header:** name (or "New caller"), the number masked to its last 3 digits, how many tries, the latest one's time, and the line they called.
   - **Who:** a known customer with how many calls and when they last spoke to you, or "Not in your contacts".
   - **History:** one line from their latest call summary, with a quote of at most 15 words, and that call's date and call reference. Mark it partial when it is. Skip this line for a new caller.
   - **Why here:** the reason for this rank (tried 3 times; complaint last week; waited since 9:12).
   - **Reply:** text from which line, which AI Voice Agent, a person, hold until when, or skip.
   - **Draft:** the text, with its language when it isn't the user's.
3. **Not on this list:** reached already (a count, and first names when there are a few), hidden numbers, and callers past the first 12 (a count; offer the next 12).
4. **Not covered:** voicemails (not readable here), texts the team already sent (not checked), calls before the period started, and missing summaries (once).
5. **The question:** which to send. "Reply with the numbers to send (for example: send 1, 2 and 4), change any draft, or tell me who not to contact."

Nobody missed in the period: say so in one line with the period, and stop. Everyone reached already: say that, with the count.

> **✓ Gate: before you show the list**
> - [ ] every draft names the business and promises nothing the user didn't give: no link, price, offer or callback time
> - [ ] no sensitive detail, no placeholder, no em or en dash, at most 300 characters
> - [ ] phone numbers masked; no company ids, user ids or tool names in what the user reads
> - [ ] the coverage lines are there

### 7. Send what the user picks

The user's pick is the choice; the app's approval prompt on each send is the approval. Before the first send of the conversation, say once that the app will ask to approve each text. Don't ask "are you sure?" in between.

- **Check the time first.** Texts and AI calls go out only inside the business hours the user gave. For a caller whose number is from another country, also only between 8:00 and 20:00 in their timezone; if you can't tell their timezone, business hours alone decide. Outside those hours, hold: CloudTalk can't schedule a text, so held texts wait for the user or the next run.
- **Say who gets what**, one line per text: the name, the full number, the line it goes from, and the text. This is the only place the full number appears.
- **Text:** call `cloudtalk_send_sms` once per text, with `recipient` set to the caller's number in E.164 as the call log gave it, `sender` set to the chosen line's `caller_id_e164`, and `message` set to the approved text, word for word. If the user rewrote a text, send their words. A number that isn't in E.164: don't fix it by guessing a country code; show it and ask.
- **AI Voice Agent callback:** call `cloudtalk_trigger_aiva_call` once per caller, with `voice_agent_id` set to the 24-character id from `cloudtalk_list_voice_agents` (not the numeric id inside the agent's setup) and `call_number` set to the caller's number in E.164. The call carries only the agent and the number, so tell the user the agent won't know why they called.
- **Older server:** if a tool answers `status: "confirmation_required"`, nothing happened yet. Show its preview, and call again with `"confirm": true` once the user agrees.
- **Report the result, not the attempt.** A text is sent only when the result says `status: "sent"`; an AI callback is "queued", not made. A refused send: say why in plain words and don't retry without telling the user. Offer the link to the Messages report the result gives.

> **✓ Gate: before each send or call**
> - [ ] the user picked this caller in this conversation, and they aren't on the skip list
> - [ ] the recipient is the number that called, in E.164; the sender is a company line with `sms_supported: true`
> - [ ] it is inside business hours, and daytime for the caller
> - [ ] the text is the approved one, word for word
> - [ ] this caller hasn't had a text or an AI call from this run already

### 8. Run it twice a day, where the app can

After the first run, offer this once.

- **The app can run scheduled tasks** (you can see a way to create one here): offer two runs each business day, around midday and an hour before closing. Put the business name, hours, timezone and skip list into the task, so a run doesn't need to ask. Each run covers the time since the previous run; the first run of the day covers since the last run of the day before, so overnight calls are in it.
- **A scheduled run reads and drafts only.** It never sends a text or starts a call, even when the app would let it. It leaves the list for the user to pick from when they're back.
- **The app can't schedule:** say so plainly. Suggest running it at those two times by hand, with "missed calls since my last check". Never promise a schedule or a reminder the app can't run.

## What this can't do

- **Voicemails:** CloudTalk's connection can't tell whether a caller left a voicemail, or play one. If the lines take voicemail, check them in CloudTalk before sending.
- **Texts sent by the team:** texts can only be read agent by agent, so a caller someone already texted back still shows. Ask the user to skip them.
- **Scheduled sends:** a text goes now or not at all.
- **Context for the AI Voice Agent:** it gets the number, not the reason for the call.
- **Hidden numbers** can't be contacted.
- **Plan:** sending needs a number with SMS enabled; callbacks need AI Voice Agents; call summaries need Conversation Intelligence. Say what's missing once.

## Budget and privacy

- The account allows 60 requests per minute. A full run makes about 50 at most: up to 9 searches, one number list, up to 3 AI Voice Agent reads, 2 or 3 reads for each of 12 callers, and at most 5 language checks. Fetch in parallel only where the app allows, at most 10 at a time. On a rate-limit error, wait a minute and retry once.
- Mask phone numbers to their last 3 digits everywhere except the send lines in step 7. Never paste transcripts or full summaries.

## Non-negotiables

- **Send only what the user picked in this conversation.** One call per text or AI call, after saying who gets what. A scheduled or unattended run never sends.
- **Text only the number that called**, exactly as the call log has it. Never another number from the contact's record, never a guessed country code.
- **Never invent a promise.** No link, price, offer, discount or callback time the user didn't give, and no placeholder.
- **Never put a sensitive detail in a text.** No amounts, health, account or order details.
- **Never text outside business hours**, or at night for the caller.
- **Never contact a caller the user ruled out, or one reached already.**
- **Report what happened, not what you tried:** "sent" only on a sent result, "queued" for an AI call.
- **Plain words for the user:** no company ids, user ids or tool names, and no em or en dashes in anything you write.
- **Never ask the user to paste a CloudTalk API key, password or sign-in code into the chat.** If CloudTalk isn't connected, point them to the app's connector settings.
