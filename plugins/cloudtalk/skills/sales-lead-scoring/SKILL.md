---
name: sales-lead-scoring
description: Score leads from recent CloudTalk sales calls and rank who to follow up first, with the evidence behind each score. Use when the user asks which leads are hot, who to call back, how promising recent prospects are, or to score or qualify leads from calls. Works best with Conversation Intelligence (summaries and transcripts).
---

# Sales lead scoring

Goal: a ranked list of leads, each with a score, the reason, and the next step. Explicit user instructions always win over this skill, including their own criteria or weights.

## 1. Set the scope

Default: the last 14 days, sales calls only, at most 30 leads. Sales calls are outbound calls, or inbound calls to a sales group. If `cloudtalk_list_groups` doesn't make the sales team obvious, ask which group or agents count as sales.

## 2. Gather

- Call `cloudtalk_search_calls` for the window (`date_from`, `date_to` in UTC), with `group_id` or `user_id` if given. Group the calls by contact, and skip contacts with no answered call.
- For each lead, call `cloudtalk_get_contact_interactions_summary` for the call mix, last contact and tags.
- For the latest answered call over 60 seconds, call `cloudtalk_get_call_insights` with `include: ["summary", "smart_notes"]`. Open the transcript only to quote evidence.

## 3. Score from 0 to 100

| Signal | Points | Look for |
|---|---|---|
| Need | 0 to 25 | A stated problem or goal the offer solves |
| Timeline | 0 to 20 | When they want to start or decide |
| Authority | 0 to 15 | The decision-maker is on the call, or named |
| Budget | 0 to 15 | Price discussed without pushback, or a budget named |
| Engagement | 0 to 15 | Answered calls, call length, the lead calling back |
| Next step | 0 to 10 | A dated next step both sides agreed |

No evidence for a signal means 0 points and the note "unknown". Never infer budget or authority from tone.

Tiers: **Hot** 70 and up, **Warm** 40 to 69, **Cold** under 40.

## 4. Present the ranking

1. One line of coverage: the window (exact dates), leads scored, and calls read and skipped.
2. A table sorted by score: Lead | Company | Score | Tier | Strongest signal | Missing | Next step | Last call (date, id).
3. Under it, the 3 leads to call today, each with one sentence on why and the question that fills its biggest unknown.
4. Say once that scores rank leads from what was said on calls; they are not facts about the customer.

## 5. Offer next steps

Offer these, and do them only when the user agrees. Each one is a write, so the app asks for approval.

- Tag leads by tier (for example "Hot lead") with `cloudtalk_bulk_tag_contacts` in `mode: "append"`. It returns a preview first.
- Save the score and reason as a note with `cloudtalk_add_contact_note`.
- Start a call to a Hot lead with `cloudtalk_initiate_call`, which rings the agent first. It returns a preview first.

## Rules

- Show the evidence. The user must see why a lead scored high.
- Leads who only reached voicemail or an AI Voice Agent have no transcript. List them as "not enough data" instead of scoring them.
- Keep personal details to what the ranking needs. Mask phone numbers to their last 3 digits unless the user needs them in full.
- Reply in the user's language.
