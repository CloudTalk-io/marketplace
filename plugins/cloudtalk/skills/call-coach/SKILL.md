---
name: call-coach
description: Coach your team and your AI Voice Agents from real CloudTalk calls. For each one, find a moment that went well, a moment to change and a better line to try, all quoted from the call. Use for QA, call reviews, 1:1 prep, support quality, or when the user asks how their agents or AI agents handle customers. Needs Conversation Intelligence for transcripts.
---

# Call coach

CloudTalk is the agent-first phone system: AI agents answer first, humans close. Coaching applies to both. People get a better line to try. AI Voice Agents get a setup change.

Goal: specific, kind coaching that changes the next call. Explicit user instructions always win over this skill, including their own checklist.

## 1. Pick who to coach

Default: the last 7 days, the support group, every person in it, and every AI Voice Agent that answered calls. Resolve the team with `cloudtalk_list_groups`, `cloudtalk_list_agents` and `cloudtalk_list_voice_agents`. Ask for the group if it isn't clear. At most 8 people and 3 AI agents per run.

## 2. Pick fair calls

- People: call `cloudtalk_search_calls` with `status: "answered"`, the period and `user_id`. AI agents: the same with `voice_agent_id` set to the agent's numeric id. Get it from `cloudtalk_get_voice_agent` (`voice_agent.voice_agent_id`); the text id from `cloudtalk_list_voice_agents` won't match calls.
- Take up to 5 calls over 60 seconds each. Include up to 2 with negative sentiment (`sentiment: "negative"`), and fill the rest from ordinary calls, so nobody is judged on their worst day.
- Read each with `cloudtalk_get_call_transcript`, plus `cloudtalk_get_call_insights` with `include: ["summary", "sentiment"]`. Calls under 30 seconds have no transcript; skip them and count them.

## 3. Listen for six moments

| Moment | What good sounds like |
|---|---|
| Opening | Greets, says who they are and the company |
| Getting it | Restates the need and asks a clarifying question |
| Getting it done | Solves it, or gives a next step with an owner and a time |
| Getting it right | No wrong or invented information |
| Tone | Calm and polite, no interrupting, empathy when the caller is upset |
| Wrap-up | Checks the caller is sorted and recaps next steps |

Mark each moment **strong**, **okay** or **missed**, with a quote. Skip a moment that doesn't apply, such as a call transferred early.

AI Voice Agents add two:

- **Handoff:** transferred to a person when it should have, and with the context.
- **Knowledge:** answered from its knowledge base without making things up.

## 4. Coach

For each person or AI agent:

- **Keep doing:** the strongest moment, quoted.
- **Change one thing:** the most common miss, quoted, with a better line to say next time. For an AI Voice Agent, name the setup change instead: its greeting, a knowledge-base gap, a transfer rule, or a tool.
- **Example call:** date and call id.

Then the team view: the moment missed most often across everyone, and one line on what would help most.

## 5. After coaching

Offer, and do only when the user agrees:

- draft the 1:1 notes
- tag the reviewed calls with `cloudtalk_add_call_tags`, using a tag that exists in `cloudtalk_list_call_tags`
- for an AI Voice Agent, prepare the setup change with `cloudtalk_update_voice_agent`, which shows a preview and asks for approval

## Rules

- Coach from what was said. Quote the evidence for every miss.
- One change per person or agent, not a list of faults. This is coaching input, not a performance rating.
- Mask phone numbers and keep quotes short. Reply in the user's language.
