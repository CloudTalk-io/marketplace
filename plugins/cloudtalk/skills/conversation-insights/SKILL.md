---
name: conversation-insights
description: Turn recent CloudTalk conversations into insights you can act on. It finds the open loops, meaning questions not answered, promises not kept, callers not called back and risks not handled, and say who should close each one, a person or an AI Voice Agent. Use when the user asks what needs attention, what's still open, what the team owes customers, who to follow up with, or for a daily or weekly call digest. It only reads, and it is not a call-volume report. Summaries need Conversation Intelligence.
---

# Conversation insights

CloudTalk is the agent-first phone system: AI agents answer first, humans close. This skill reads recent conversations and turns them into open loops, meaning things still owed to a customer, each with who should close it.

Goal: a short list a manager can clear in one sitting. Every loop points to the conversation it came from. Explicit user instructions always win over this skill.

It only reads. Nothing is sent, tagged or changed while the list is built.

## Two kinds of input

| | What you do | Covers |
|---|---|---|
| **Judgment** | Decide it yourself, without asking. | What counts as a loop, its urgency, who should close it, how to word it |
| **Ground truth** | Read it from CloudTalk, or ask. Never invent it. | Who called, when, what was said or promised, which AI Voice Agents exist |

A loop you infer is labelled as inferred. A next step nobody promised is labelled "Suggested".

## 1. Pick the period

- Use the user's dates when they give them. Otherwise use the last 7 days, from midnight 7 days ago to now.
- For "what's new since last time", start where the previous list ended, and say so.
- Don't stretch the period on your own. Name it at the top in the user's timezone if you know it, plus the UTC times you queried (`YYYY-MM-DD HH:MM:SS`).

> **✓ Gate:** one period, named with its exact start and end · no longer than the user asked for.

## 2. Look in three places

1. **Missed calls.** Call `cloudtalk_search_calls` with `status: "missed"` and group by caller. A caller who tried more than once, or a known customer, is a loop. Call `cloudtalk_get_contact_interactions_summary` for those.
2. **Answered calls, by people and by AI Voice Agents.** Call `cloudtalk_search_calls` with `status: "answered"` and page up to 200 calls. Read up to 25: longest first, then negative sentiment. For each, call `cloudtalk_get_call_insights` with `include: ["summary", "sentiment", "smart_notes"]`. Action items, risks and unanswered questions in the smart notes are the main source of loops. Open `cloudtalk_get_call_transcript` only to quote proof for an urgent loop.
3. **Texts, when the user asks.** SMS is read per agent: call `cloudtalk_list_sms_conversations` for the agents named, then `cloudtalk_list_sms_messages` for the threads that matter.

Calls under 30 seconds have no transcript or insights, whoever answered them. Empty insights on a longer call mean it isn't analyzed yet, or Conversation Intelligence isn't on the plan. Say so once, not per call.

> **✓ Gate:** you know how many missed and answered calls the period has, how many you read, and whether texts were in scope. A list built from fewer than 5 readable calls says so at the top.

## 3. Decide what's open, and how urgent

A loop is open when the conversation shows something still owed. It is not open when it was settled, was only small talk, or is a guess from silence.

**Close today:**
- a customer waiting past a promised time
- the same request made twice
- a cancellation or complaint signal
- a deal stuck waiting on us
- an urgent billing, access or legal issue
- anything due within 2 business days

**Close this week:**
- an open question, quote, demo or document
- a buying signal or referral
- friction someone can own

**Worth knowing:** context, praise, early signals. No action yet.

Rank inside each group by customer harm, then money at stake, then how clearly they asked, then recency. Merge loops about the same customer and topic. Tone alone never makes a loop urgent.

## 4. Say who closes it

For each loop, suggest an owner:

- **The agent who had the call**, when it needs judgment, negotiation or a relationship.
- **An AI Voice Agent**, when it's routine and the account has one set up for it, such as a confirmation, a reminder, or a callback to collect details. Name the agent from `cloudtalk_list_voice_agents`.
- **Unassigned**, when nobody obvious owns it.

## 5. Write the list

1. **Top line:** the period, then what you looked at: missed calls, answered calls read and in total, and texts reviewed or not.
2. **Close today** and **Close this week.** One entry per loop:
   - **Customer:** name, with the phone number masked to its last 3 digits.
   - **What's open:** one sentence, with a quote of at most 15 words.
   - **Why now:** the deadline, risk or money involved.
   - **Who closes it:** a person, an AI Voice Agent, or unassigned.
   - **Next step:** a real promise from the call, or a suggestion marked "Suggested".
   - **Source:** date, time and who took the call, plus the call reference so the user can find it.
3. **Worth knowing:** one line each.
4. **Patterns:** only those seen in at least two separate conversations.
5. **Not covered:** calls not read, calls under 30 seconds, voicemails, texts not requested. Don't present counts as call volumes or performance.

Show about 10 loops by default: all "close today", then the strongest of the rest. Say how many more there are.

## 6. Then offer to close loops

Offer, and act only when the user agrees. The app asks for approval each time:

- save a loop as a note on the contact (`cloudtalk_add_contact_note`)
- send a follow-up text (`cloudtalk_send_sms`)
- have an AI Voice Agent make the routine callback (`cloudtalk_trigger_aiva_call`)

Say who gets what before each one.

## Non-negotiables

- No loop without its source. Keep what you inferred apart from what was said.
- Never invent a customer, a promise, a date or a quote. If a read returns nothing, say so.
- Nothing is sent, tagged or saved unless the user asks for that one action.
- Never show a company id, user id or tool name to the user; name people, agents and numbers.
- Mask phone numbers to their last 3 digits. Quote at most 15 words. Never paste full transcripts.
- The account allows 60 requests per minute. On a rate-limit error, wait a minute and say what was left unread.
- Never present counts as call volumes, answer rates or performance.
- Reply in the user's language.
