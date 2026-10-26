---
name: conversation-insight-log
description: Turn the last week of CloudTalk calls into a prioritized log of what matters, with customer requests, risks, opportunities, commitments the team made, and friction that keeps coming up. Use when the user asks what happened on their calls, what customers are asking for, what the team promised, or for a weekly call log or digest. Summaries and smart notes need Conversation Intelligence.
---

# Conversation insight log

Goal: one page a manager can act on in five minutes. Every item points to the call it came from. Explicit user instructions always win over this skill.

## 1. Set the scope

Default: the last 7 days, answered calls, the whole company. Ask only when the request is unclear about the number, group, agent, or time window. Use the user's choice when they give one.

## 2. Find the calls

- Call `cloudtalk_search_calls` with `status: "answered"`, the window as `date_from` and `date_to` (UTC, `YYYY-MM-DD HH:MM:SS`), and any filter (`group_id`, `user_id`). Page with `page` until you have them all, up to 200 calls.
- Skip calls under 30 seconds and voicemails. Count what you skipped.
- Calls handled by an AI Voice Agent have no transcript or AI insights. If the user asks about them, list them with `voice_agent_id` and say they can't be read yet.
- Pick up to 25 calls to read in depth: longest first, then calls with negative sentiment, then the rest.

## 3. Read them

For each picked call, call `cloudtalk_get_call_insights` with `include: ["summary", "sentiment", "smart_notes"]`. Open `cloudtalk_get_call_transcript` only to quote evidence for a P1 item. If the insights come back empty, either the call hasn't been analyzed or Conversation Intelligence isn't on the plan. Say so once, not per call.

## 4. Sort what you found

Give each item one type and one priority.

| Type | What counts |
|---|---|
| Request | The customer asked for something |
| Risk | Churn signal, complaint, escalation, payment or legal issue |
| Opportunity | Upsell, referral, a new need |
| Commitment | Someone on the team promised something, with or without a date |
| Friction | The same problem on 2 or more calls |

| Priority | When |
|---|---|
| **P1**, act today | Risk of losing the customer or revenue, a broken commitment, a deadline in the next 2 days |
| **P2**, follow up this week | Open requests, opportunities, commitments due later |
| **P3**, keep in view | Patterns and context with no action yet |

Merge items that describe the same thing across calls, and keep the count.

## 5. Write the log

1. Start with three facts: calls in the window, calls read, calls skipped and why.
2. One table per priority, P1 first: Item | Type | Customer | Agent | Call (date, id) | Evidence (at most 15 words, quoted from the transcript or summary).
3. End with **Recurring friction**: up to 3 patterns, each with its number of calls.

## 6. Offer next steps

Offer these, and do them only when the user agrees. Each one is a write, so the app asks for approval.

- Save an item as a note on the customer's contact with `cloudtalk_add_contact_note`.
- Draft a follow-up SMS for a P1 item. `cloudtalk_send_sms` returns a preview first; send only after approval.

## Rules

- No item without the call it came from.
- Don't guess intent. Mark an unclear item "unclear" instead of raising its priority.
- Keep personal details to what the item needs. Never paste full transcripts into the log.
- Reply in the user's language.
