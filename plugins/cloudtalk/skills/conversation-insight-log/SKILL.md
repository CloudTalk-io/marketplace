---
name: conversation-insight-log
description: Build a prioritized log of what matters in recent CloudTalk conversations, including answered calls, missed calls, and texts when asked. It covers customer requests, risks, opportunities, commitments the team made, and friction that keeps coming up, each tied to the call it came from. Use for a daily or weekly call log or digest, or when the user asks what customers want, what the team promised, or what needs attention. It reads only and is not an analytics report; summaries need Conversation Intelligence.
---

# Conversation insight log

Goal: one page a manager can act on in five minutes. Every item points to the conversation it came from. Explicit user instructions always win over this skill.

This skill only reads. It never sends, tags, or edits anything while building the log.

## 1. Set the window

- Use the user's start and end when they give them.
- Otherwise, cover the last 7 days: from midnight 7 days ago to now.
- For "what changed since my last log", start where the previous log ended, and say so. If that end time isn't available, use the 7-day default and say that too.
- Never widen the window silently, and don't go past 7 days unless the user asks.
- At the top of the log, state the window in the user's timezone if you know it, plus the exact UTC boundaries you queried. The tools take UTC as `YYYY-MM-DD HH:MM:SS`.

## 2. Gather, in this order

1. **Answered calls.** Call `cloudtalk_search_calls` with `status: "answered"` and the window, plus any filter the user gave (`group_id`, `user_id`). Page with `page`, up to 200 calls. Skip calls under 30 seconds. Pick up to 25 to read: longest first, then negative sentiment, then the rest. For each, call `cloudtalk_get_call_insights` with `include: ["summary", "sentiment", "smart_notes"]`. Open `cloudtalk_get_call_transcript` only to quote evidence for a P1 item.
2. **Missed calls.** Call `cloudtalk_search_calls` with `status: "missed"`. Group by caller. For repeat callers or known contacts, call `cloudtalk_get_contact_interactions_summary`.
3. **Texts, only when the user asks.** SMS is read per agent: call `cloudtalk_list_sms_conversations` for the agents the user names, then `cloudtalk_list_sms_messages` for the threads that matter.
4. **AI Voice Agent calls.** These have no transcript or insights yet. Count them for the coverage note and don't try to read them.

Empty insights mean the call isn't analyzed yet, or Conversation Intelligence isn't on the plan. Say so once, not per call.

## 3. Prioritize from evidence

Judge each item only from what the call or text shows, and use the strongest band that applies.

| Band | Use it when |
|---|---|
| **P1**, act now | A deadline within 2 business days. An escalation, cancellation or churn signal, or a serious service failure. A deal or lead blocked waiting on us. A request that went unanswered more than once, or a promise whose time has passed. An urgent billing, legal, security or account-access issue. |
| **P2**, follow up | An open question or request (quote, demo, document, callback). A buying signal, expansion or referral. A commitment with no near deadline. Friction that has a plausible owner. An objection that could affect the relationship. |
| **P3**, keep in view | Praise or a customer story worth keeping. An early or unclear opportunity. A theme that isn't actionable yet. Context that will help the next conversation. |

**Leave out:** greetings and scheduling chatter, spam, wrong numbers and test calls, exchanges already resolved, guesses based on silence, and repeated fragments of the same exchange.

**Within a band, order by:** harm or deadline, then business impact, then how explicit the ask was, then recency.

Merge items about the same customer and topic, keeping the newest state and any earlier promise still open. Tone alone never makes something P1.

## 4. Write the log

1. **Header:** the window, then the coverage: answered calls in the window and how many you read, missed calls, texts (reviewed or not), and AI Voice Agent calls (counted only).
2. **P1, then P2:** one entry each.
   - **When and channel:** date and time, answered call, missed call or text, and the agent.
   - **Why it matters:** the deadline, consequence or blocker.
   - **What happened:** one or two sentences from the evidence, with a quote of at most 15 words.
   - **Next step:** a real commitment from the call, or a suggestion labeled "Recommended".
   - **Source:** the call id.
3. **P3:** one line per item.
4. **Patterns:** only those backed by at least two separate conversations, each with its count.
5. **Coverage limits:** what this log didn't see: calls not read, AI Voice Agent calls, voicemails, texts not requested. It is not a full call report, so don't state call volumes, answer rates or agent performance as findings.

By default show about 10 items: every P1, then the strongest P2 and P3. Say how many more you found and offer a deeper log by group, agent or customer.

## 5. After the log

Offer, and do only if the user agrees: save an item as a contact note (`cloudtalk_add_contact_note`), or draft a follow-up text (`cloudtalk_send_sms`, which returns a preview first). The app asks for approval on each.

## Rules

- No item without the conversation it came from. Keep inference apart from evidence.
- Mask phone numbers to their last 3 digits unless the user needs them in full. Never paste full transcripts.
- Reply in the user's language.
