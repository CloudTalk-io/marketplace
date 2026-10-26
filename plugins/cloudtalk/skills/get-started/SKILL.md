---
name: get-started
description: Set up CloudTalk in this chat and show what it can do. Use right after CloudTalk is installed or connected, when the user asks what CloudTalk can do or how to start, or when a CloudTalk tool fails or returns nothing and the user doesn't know why. Checks the connection, finds what the account has (AI Voice Agents, call insights, campaigns), and offers three first tasks that work on this account.
---

# Get started with CloudTalk

CloudTalk is the agent-first phone system: AI agents answer first, humans close. One place to run every call.

Goal: take the user from "connected" to a first useful answer in one or two turns. Explicit user instructions always win over this skill.

## 1. Check the connection

Call `cloudtalk_health_check`.

- **It succeeds:** say in one line that CloudTalk is connected, and to which company (its ID).
- **It fails:** explain the cause in plain words and stop. Retry at most once.
  - Not signed in, or the sign-in expired: reconnect CloudTalk in the app's connector settings and sign in as a CloudTalk Admin.
  - The account isn't eligible: CloudTalk's AI connection needs the Essential plan or higher.

## 2. Find what this account has

These are reads, so they run without asking the user. Make them in parallel when the app allows it:

- `cloudtalk_list_voice_agents` with `limit: 5`: AI Voice Agents.
- `cloudtalk_search_calls` for the last 7 days with `limit: 5`: recent calls, and whether they carry AI insights (a summary or sentiment).
- `cloudtalk_list_campaigns`: outbound campaigns. An error here means the Sales Dialer add-on isn't on the plan. That's normal; don't treat it as a failure.

Don't show raw results. Give one short line per area: what exists, or that the area isn't set up yet.

## 3. Offer three first tasks

Pick the three that fit what step 2 found, in this order of preference, and show them as a numbered list. Ask which one to run, and run it when the user picks.

| Show it when | Task |
|---|---|
| Always | Who called yesterday that we missed, and who should we call back first? |
| The account has an outbound AI Voice Agent | Have our AI Voice Agent call a customer to confirm their appointment |
| No AI Voice Agents yet | Set up an AI Voice Agent that answers questions from our website |
| The account has AI Voice Agents | Compare last week's calls handled by our AI Voice Agents and by my team |
| Recent calls carry AI insights | Find this week's calls with negative sentiment and tell me what went wrong |
| The account has campaigns | How are my running campaigns doing, and which one should I pause? |

How to run the first three:

- **Missed calls:** `cloudtalk_search_calls` with `status: "missed"` for yesterday, then `cloudtalk_get_contact_interactions_summary` for at most 10 callers. Rank callbacks by how often the caller tried and how recent their last contact was. Say why each caller is ranked where they are.
- **AI agent calls a customer:** ask which customer if the user didn't say. Find them with `cloudtalk_list_contacts`, pick the outbound agent from `cloudtalk_list_voice_agents` whose name fits the task (check with `cloudtalk_get_voice_agent`, and ask if several fit), then call `cloudtalk_trigger_aiva_call` without `confirm` to get the preview. The call carries only the agent and the number, not details like the appointment time: tell the user what the agent will do from its own setup. See Approvals below.
- **AI agents and team:** `cloudtalk_list_voice_agents`, then `cloudtalk_get_voice_agent` for each to get its numeric id (`voice_agent.voice_agent_id`). Call `cloudtalk_search_calls` for last week once per voice agent with `voice_agent_id` set to that numeric id, and once for all answered calls. Report the totals side by side, and name the date range.

After the first task, suggest the one skill that fits what the user did next:

- `open-loops`: what's still open after this week's calls, and who should close it.
- `next-best-call`: who to call next, and what an AI Voice Agent can handle.
- `call-coach`: coaching for the team and the AI Voice Agents.

## Approvals

Reads run straight away. Anything that sends or changes something (an SMS, a call, a campaign start, a contact edit, a new voice agent) works in two steps:

1. Call the tool without `confirm`. It returns a preview and does nothing yet.
2. Show the preview in one or two plain lines (who, what, when). If the user asked for exactly this action, call again with `"confirm": true`; the app asks the user to approve that call. If the request was vague, ask in chat before confirming.

Explain this once, in one sentence, before the first write of the conversation. Never pass `"confirm": true` on a first call.

## Ground rules

- Reply in the user's language.
- Never invent numbers, names, or call content. If a read returns nothing, say so.
- Calls under 30 seconds have no transcript or insights, whether a person or an AI Voice Agent took them. Say so instead of retrying.
- Empty summary, sentiment or transcript fields on a longer call mean Conversation Intelligence isn't on the plan, or the call hasn't been analyzed yet.
- The account allows 60 requests per minute. Fetch details for at most 10 calls at a time, and on a rate-limit error wait a minute before retrying.
- Include phone numbers and customer details only when the task needs them.

More help: https://help.cloudtalk.io/guides/mcp/overview
