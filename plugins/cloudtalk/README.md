# CloudTalk

Run every call from your AI assistant. CloudTalk is the agent-first phone system: AI agents answer
first, humans close.

This plugin connects your AI assistant to your CloudTalk account through the CloudTalk MCP
(`https://mcp.cloudtalk.io`) and ships eight skills. It used to be **CloudTalk VoiceAgent Builder**; the
[repo README](../../README.md#upgrading-from-cloudtalk-voiceagent-builder) has the two upgrade steps.

| Skill | What it does | Needs |
|---|---|---|
| [`get-started`](./skills/get-started/SKILL.md) | Checks the connection, finds what your account has (AI Voice Agents, call insights, campaigns), and offers up to three first tasks that work on it. | Essential plan |
| [`conversation-insights`](./skills/conversation-insights/SKILL.md) | Turns recent conversations into open loops: what is still owed after your calls (unanswered questions, broken promises, missed callers, risks) and who should close each loop: a person or an AI Voice Agent. | Conversation Intelligence |
| [`missed-call-follow-up`](./skills/missed-call-follow-up/SKILL.md) | Finds today's missed callers nobody has reached yet, drafts a short text back to each from their history, and sends only what you approve. Can hand routine callbacks to an AI Voice Agent. | No add-on; a number with SMS for texts |
| [`call-coach`](./skills/call-coach/SKILL.md) | Coaches your team and your AI Voice Agents from real calls: one moment to keep, one to change, and a better line or setup change. | Conversation Intelligence |
| [`voice-agent-builder`](./skills/voice-agent-builder/README.md) | Builds, fixes and validates an AI Voice Agent from a plain-language description, reusing your real numbers, knowledge bases and tools, and saves it after your approval. | AI Voice Agents; works offline too |
| [`voice-agent-checkup`](./skills/voice-agent-checkup/SKILL.md) | Checks whether an AI Voice Agent is ready to go live: a verdict, the fix to make first, the tests to run and a go-live checklist. Changes nothing, except a test call to your own phone when you ask. | AI Voice Agents |
| [`voice-agent-replay`](./skills/voice-agent-replay/SKILL.md) | Improves a live AI Voice Agent from its real calls: failures grouped by cause, two calls of proof each, and the setup change that fixes each one. | AI Voice Agents, Conversation Intelligence |
| [`voice-agent-simulator`](./claude-skills/voice-agent-simulator/README.md) | Plays a difficult caller against an agent's setup and scores the call, before real customers reach it. Claude only. | Nothing; a real test call needs AI Voice Agents |

## Example prompts

- Who called yesterday that we missed, and who should we call back first?
- Have our AI Voice Agent call my phone so I can hear it
- Set up an AI Voice Agent that answers questions from our FAQ page
- What's still open after this week's calls?
- Test this agent against an impatient caller who keeps interrupting

## Install

**Claude Code:**

```
/plugin marketplace add CloudTalk-io/marketplace
/plugin install cloudtalk@cloudtalk
```

**Claude app (claude.ai / desktop):** Customize → **Plugins** → **Add** → **Add marketplace** →
`CloudTalk-io/marketplace`, then add **CloudTalk**.

On first use, sign in with CloudTalk as an **Admin** and approve the access. There is no API key to
create or paste. CloudTalk's AI connection needs the Essential plan or higher; AI Voice Agents,
Conversation Intelligence and Sales Dialer unlock the matching tools.

Developers in Claude Code who prefer a company API key can add the voice agent server themselves; see
[Advanced: connect with an API key](../../README.md#advanced-connect-with-an-api-key) in the repo README.

## ChatGPT

The same folder is the ChatGPT plugin package. Each assistant reads its own manifest:

| File | Read by |
|---|---|
| `.claude-plugin/plugin.json` | Claude: plugin identity and the MCP server (sign-in) |
| `plugin.json` | ChatGPT: identity, listing, starter prompts, review test cases, translations (`extensions.com.openai`) |
| `mcp.json` | ChatGPT: the MCP server. Sign-in is discovered from the server (Client ID Metadata Document) |
| `skills/`, `assets/` | Both |
| `claude-skills/` | Claude only (`voice-agent-simulator` needs subagents) |

Build the upload ZIP from this folder:

```bash
cd plugins/cloudtalk
zip -r ../../cloudtalk-chatgpt.zip plugin.json mcp.json skills assets -x '*/__pycache__/*'
```

Upload it at [platform.openai.com/plugins](https://platform.openai.com/plugins), then connect the MCP
server and enter the reviewer credentials in the portal. Credentials never go in this folder.

**Still needed before the first ChatGPT submission:** a demo recording URL
(`review.demo_recording_url`), the country list (`publication.countries`), a reviewer account on a
demo company, and a run of the five test cases against it.
