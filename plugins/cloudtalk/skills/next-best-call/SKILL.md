---
name: next-best-call
description: Rank recent sales leads by how ready they are, and say the next best move for each and who makes it, a call from you, an AI Voice Agent call, or a text. Use when the user asks who to call next, which leads are hot, how to prioritize prospects, or to qualify leads from recent calls. Works best with Conversation Intelligence (summaries and transcripts).
---

# Next best call

CloudTalk is the agent-first phone system: AI agents answer first, humans close. This skill decides where a person's time pays off, and where an AI Voice Agent can take the next touch.

Goal: the user knows who to call in the next hour and why, plus what the AI agent can handle. Explicit user instructions always win over this skill, including their own signals.

## 1. Pick the leads

Default: the last 14 days, sales calls only, at most 30 leads. Sales calls are outbound calls, or inbound calls to a sales group. If `cloudtalk_list_groups` doesn't make the sales team clear, ask which group or agents count as sales.

## 2. Gather

- Call `cloudtalk_search_calls` for the period (`date_from`, `date_to` in UTC), with `group_id` or `user_id` if given. Group the calls by contact, including calls an AI Voice Agent handled.
- For each lead, call `cloudtalk_get_contact_interactions_summary` for the call mix, last contact and tags.
- For the latest answered call over 30 seconds, call `cloudtalk_get_call_insights` with `include: ["summary", "smart_notes"]`. Open the transcript only to quote evidence.

## 3. Read the readiness signals

Check each signal as **yes**, **no** or **not heard**. Never fill a gap with a guess.

| Signal | Yes means the calls show |
|---|---|
| Pain | A problem or goal the offer solves |
| Timing | When they want to start or decide |
| Decision-maker | The person deciding was on the call, or named |
| Budget | Price discussed without pushback, or a budget mentioned |
| Momentum | They answer, talk at length, or call back themselves |
| Next step | A dated next step both sides agreed |

Readiness:

- **Ready:** pain plus at least two of timing, decision-maker and budget, and momentum.
- **Warming:** pain, but timing or the decision-maker isn't heard yet.
- **Not now:** no clear pain, or they said no.

Don't turn the signals into a numeric score. The point is the next move, not precision.

## 4. Choose the next move and who makes it

| Situation | Next move | Who |
|---|---|---|
| Ready, or a real objection to handle | Call now | A person, with click-to-call (`cloudtalk_initiate_call`) |
| Warming, and the gap is a simple fact (timing, a date, the right contact) | A short qualifying call | An AI Voice Agent (`cloudtalk_trigger_aiva_call`), if the account has an outbound one fit for it |
| Waiting on us (a quote, info) | Send what was promised, then call | A person |
| Not now | A friendly text or a reminder later | A text (`cloudtalk_send_sms`), or nothing |

## 5. Present it

1. One line: the period, leads reviewed, and calls read and skipped.
2. **Call in the next hour:** up to 3 leads. For each, the reason in one sentence, the question that fills the biggest gap, and the last call (date, id).
3. **Hand to an AI Voice Agent:** leads where a short qualifying call is enough, with the agent's name.
4. The full table, sorted Ready, then Warming, then Not now: Lead | Company | Readiness | Signals heard | Missing | Next move | Who | Last call.
5. Say once that readiness comes from what was said on calls and isn't a fact about the customer.

## 6. Act only when asked

Calls, AI agent calls, texts, tags ("Ready" with `cloudtalk_bulk_tag_contacts` in `mode: "append"`) and notes (`cloudtalk_add_contact_note`) each show a preview first. The app asks the user to approve them.

## Rules

- Show the evidence for every Ready lead.
- Leads who only reached voicemail, or had calls under 30 seconds, go under "not enough to judge".
- Mask phone numbers to their last 3 digits unless the user needs them. Reply in the user's language.
