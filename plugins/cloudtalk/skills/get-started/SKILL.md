---
name: get-started
description: Set up CloudTalk in this chat and show what it can do. Use right after CloudTalk is installed or connected, when the user asks what CloudTalk can do or how to start, or when a CloudTalk tool fails or returns nothing and the user doesn't know why. Checks the connection, finds what the account has (AI Voice Agents, call insights, texting, campaigns), and offers three first tasks that work on this account.
---

# Get started with CloudTalk

CloudTalk is the agent-first phone system: AI agents answer first, humans close. One place to run every call.

Goal: take the user from "connected" to a first useful answer in one or two turns. Done means the user has run one real task on their own account and knows which skill to use next. Explicit user instructions always win over this skill.

## Two kinds of input

| | What you do | Covers |
|---|---|---|
| **Judgment** | Decide it yourself, without asking. | Which three tasks to offer, how to word a summary, how to rank callers or calls |
| **Ground truth** | Read it from CloudTalk, or ask. Never invent it, default it, or copy it from an example. | Who the user is, what the account has, names, numbers, dates, what was said on a call |

People don't know their account's internal ids. Never show a company id, user id or tool name in what the user reads.

## 1. Check the connection

Call `cloudtalk_health_check`.

- **It succeeds:** find out who is signed in. If it returns a `user_id`, call `cloudtalk_list_agents` with `id` set to it and greet the user by name and email in one line: "You're connected to CloudTalk as Jana Novak (jana@acme.com)." If there is no `user_id`, or the lookup finds nobody, say only "You're connected to CloudTalk."
- **It fails:** explain the cause in plain words and stop. Retry at most once.
  - Not signed in, or the sign-in expired: reconnect CloudTalk in the app's connector settings and sign in as a CloudTalk Admin.
  - The account isn't eligible: CloudTalk's AI connection needs the Essential plan or higher.

> **✓ Gate:** the connection works · the greeting names a person and an email, or no one · no id appears in the reply.

## 2. Find what this account has

These are reads, so they run without asking. Make them in parallel when the app allows it:

- `cloudtalk_list_voice_agents` with `limit: 5`: AI Voice Agents, and which are outbound.
- `cloudtalk_search_calls` for the last 7 days with `limit: 5`: recent calls, and whether they carry AI insights (a summary or sentiment).
- `cloudtalk_list_numbers`: whether any number can send texts (`sms_supported: true`).
- `cloudtalk_list_campaigns`: outbound campaigns. An error here means the Sales Dialer add-on isn't on the plan. That's normal; don't treat it as a failure.

Don't show raw results. Give one short line per area: what exists, or that it isn't set up yet.

> **✓ Gate:** you know, for this account: AI Voice Agents (none / inbound / outbound) · call insights (on / off / no recent calls) · texting (yes / no) · campaigns (yes / no).

## 3. Offer three first tasks

Offer one task from each of these three areas when the account supports it, using the first row that fits in each. If an area has nothing that fits, take the next fitting row from another area. Show the three as a numbered list, ask which to run, and run it when the user picks.

**Your phone line**

| Show it when | Task |
|---|---|
| Always | Who called yesterday that we missed, and who should we call back first? |
| A number can send texts | Text everyone we missed today that we'll call back within the hour |

**AI Voice Agents**

| Show it when | Task |
|---|---|
| No AI Voice Agents yet | Set up an AI Voice Agent that answers questions from our website |
| An outbound AI Voice Agent exists | Have our AI Voice Agent call a customer to confirm their appointment |
| Any AI Voice Agent exists | Turn our pricing page into a knowledge base for our AI Voice Agent |
| Any AI Voice Agent exists | Compare last week's calls handled by our AI Voice Agents and by my team |

**What happened on calls** (needs call insights)

| Show it when | Task |
|---|---|
| Recent calls carry insights | Show me last week's three toughest calls and what our team promised to do next |
| Recent calls carry insights | Find this week's calls with negative sentiment and tell me what went wrong |
| Recent calls carry insights | Score last week's sales calls and tell me which leads to follow up first |
| Recent calls carry insights | Review yesterday's support calls against our service checklist |
| Recent calls carry insights | Log what the customer asked for on my last call as a note on their contact |
| The account has campaigns | How are my running campaigns doing, and which one should I pause? |

### How to run them

- **Missed calls:** `cloudtalk_search_calls` with `status: "missed"` for yesterday. Group by caller, then call `cloudtalk_get_contact_interactions_summary` for at most 10 callers. Rank callbacks by how often the caller tried and how recently they were last in touch. Say why each caller is ranked where they are.
- **Text today's missed callers:** hand over to the `missed-call-follow-up` skill. It drafts each text from the caller's history and sends only what the user approves.
- **Set up an AI Voice Agent:** hand over to the `voice-agent-builder` skill. It asks for the business's real name and anything only the user knows, then saves the agent after approval.
- **AI agent calls a customer:** ask which customer if the user didn't say. Find them with `cloudtalk_list_contacts`. Pick the outbound agent from `cloudtalk_list_voice_agents` whose name fits the task (check with `cloudtalk_get_voice_agent`, and ask if several fit). Say in one line who the agent will call and what it will do, from its own setup: the call carries only the agent and the number, not details like the appointment time. Then call `cloudtalk_trigger_aiva_call`. See Approvals below.
- **Pricing page knowledge base:** hand over to `voice-agent-builder`. Ask for the page's address if the user didn't give it; never guess one. A web page knowledge base syncs in the background and its content is fixed once created.
- **AI agents and team:** `cloudtalk_list_voice_agents`, then `cloudtalk_get_voice_agent` for each to get its numeric id (`voice_agent.voiceAgentId`). Call `cloudtalk_search_calls` for last week once per voice agent with `voice_agent_id` set to that numeric id, and once for all answered calls. Report the totals side by side, and name the date range.
- **Three toughest calls:** `cloudtalk_search_calls` with `status: "answered"` and `sentiment: "negative"` for last week. Read insights (`cloudtalk_get_call_insights` with `include: ["summary", "sentiment", "smart_notes"]`) for up to 15 of them, longest first, and pick the three where the customer was worst served. For each: who handled it, what went wrong in one line, and the action items from its smart notes, quoted. Say how many negative calls there were and how many you read. If none are negative, say so and offer the longest calls instead.
- **Negative sentiment this week:** the same search for this week. List the negative calls with one line each on what went wrong, then the pattern across them, if there is one.
- **Sales leads to follow up:** hand over to `conversation-insights`, limited to last week's sales calls. Its buying signals and open questions give the ranking. Calls don't carry a lead score, so say the order comes from what was said on the calls.
- **Service checklist:** hand over to `call-coach` for yesterday's support calls. If the user has their own checklist, use it instead of the skill's default moments.
- **Note from my last call:** the signed-in user's latest answered call (`cloudtalk_search_calls` with their `user_id` and `limit: 1`). Read its summary and smart notes, find the contact, draft the note in one or two lines, and save it with `cloudtalk_add_contact_note` (a write; see Approvals).
- **Campaigns:** `cloudtalk_list_campaigns`, then `cloudtalk_get_campaign_statistics` for the running ones. Recommend a pause only with a reason from the numbers.

After the first task, suggest the one skill that fits what the user did next:

- `conversation-insights`: what's still open after this week's calls, and who should close it.
- `missed-call-follow-up`: make sure no missed caller waits, twice a day.
- `call-coach`: coaching for the team and the AI Voice Agents.
- `voice-agent-builder`: build or fix an AI Voice Agent, and save it after approval.
- `voice-agent-checkup`: is an AI Voice Agent ready to go live?
- `voice-agent-replay`: improve a live AI Voice Agent from its real calls.

> **✓ Gate:** three tasks, each one this account can actually run · no task needs a plan or add-on the account doesn't have.

## Approvals

Reads run straight away. Anything that sends or changes something (an SMS, a call, a campaign start, a contact edit, a new voice agent) runs on one call, and the app asks the user to approve it:

1. Say what will happen in one or two plain lines (who, what, when). If the request was vague, ask in chat first.
2. Make the call. The app's approval prompt is the user's one approval; don't ask them again in chat.

Explain this once, in one sentence, before the first write of the conversation. If a tool answers `status: "confirmation_required"`, the server is an older version: nothing happened yet, so show its preview and call again with `"confirm": true` once the user agrees.

## Non-negotiables

- Never show a company id, user id or tool name to the user. Name people, agents and numbers instead.
- Never invent numbers, names, dates or call content. If a read returns nothing, say so.
- Never write anything the user didn't ask for, and report a write as done only when its result says so.
- Calls under 30 seconds have no transcript or insights, whether a person or an AI Voice Agent took them. Say so instead of retrying.
- Empty summary, sentiment or transcript fields on a longer call mean Conversation Intelligence isn't on the plan, or the call hasn't been analyzed yet. Say it once, not per call.
- The account allows 60 requests per minute. Read details for at most 15 calls at a time, and on a rate-limit error wait a minute before retrying.
- Show phone numbers and customer details only when the task needs them.
- Reply in the user's language.

More help: https://help.cloudtalk.io/guides/mcp/overview
