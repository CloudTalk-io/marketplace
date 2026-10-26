---
name: service-scorecard
description: Score support calls against a service checklist and give each agent a scorecard with a strength and one coaching point, backed by quotes. Use when the user asks for QA, call quality review, a service or support scorecard, agent coaching, or how well the team handled customers. Needs Conversation Intelligence for transcripts.
---

# Service scorecard

Goal: a fair, evidence-based scorecard per agent that a team lead can bring to a 1:1. Explicit user instructions always win over this skill, including their own checklist.

## 1. Set the scope

Default: the last 7 days, the support group, up to 5 answered calls per agent, at most 8 agents. Resolve the team with `cloudtalk_list_groups` and `cloudtalk_list_agents`, and ask for the group if it isn't clear.

## 2. Pick fair samples

- Call `cloudtalk_search_calls` with `status: "answered"`, the window (`date_from`, `date_to` in UTC), and `group_id` or `user_id`.
- Per agent, pick up to 5 calls over 60 seconds. Include up to 2 with negative sentiment (`sentiment: "negative"`) and fill the rest from other calls, so no one is judged on bad calls only.
- For each call, read `cloudtalk_get_call_transcript`; it's needed to score. Add `cloudtalk_get_call_insights` with `include: ["summary", "sentiment"]` for context.
- Skip calls with no transcript, and count them.

## 3. Score with the checklist

Score each criterion 2 (met), 1 (partly) or 0 (missed). Mark it N/A when it can't apply, for example a call transferred before resolution, and leave it out of the total.

| Criterion | 2 means |
|---|---|
| Greeting | Greets the customer and names the company and themself |
| Understanding | Restates the issue and asks clarifying questions |
| Resolution | Solves it, or gives a clear next step with an owner and a time |
| Accuracy | Gives no wrong or invented information |
| Tone | Calm and polite, doesn't interrupt, shows empathy when the customer is upset |
| Close | Confirms the customer is sorted and sums up next steps |

Call score = points earned / points possible, as a percentage. Agent score = the average of their calls.

## 4. Present the scorecard

1. Per agent: Agent | Calls scored | Score | Strongest criterion | One coaching point | Example call (date, id) with a quote of at most 15 words.
2. Team summary: average score, the criterion missed most often, calls skipped and why.
3. Per-call detail only if the user asks.

## 5. Offer next steps

Offer these, and do them only when the user agrees.

- Tag the scored calls (for example "QA reviewed") with `cloudtalk_add_call_tags`, using only a tag that exists in `cloudtalk_list_call_tags`. The app asks for approval.
- Draft the coaching note for each agent's 1:1.

## Rules

- Score only what's in the transcript. Quote the evidence for every 0.
- One coaching point per agent, specific and kind, not a list of faults.
- Present scores as coaching input, not as a performance rating.
- Calls handled by an AI Voice Agent have no transcript yet; leave them out.
- Reply in the user's language.
