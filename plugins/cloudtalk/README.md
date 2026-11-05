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
| [`missed-call-follow-up`](./skills/missed-call-follow-up/SKILL.md) | Finds today's missed callers and unanswered texts nobody has reached yet, names an owner and flags anyone past your response time, drafts a short text back to each from their history, and sends only what you approve. Can hand routine callbacks to an AI Voice Agent, and run on a schedule for chosen lines, delivered to Slack or email. | No add-on; a number with SMS for texts |
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

Developers in Claude Code who prefer a company API key can add the AI Voice Agent server themselves; see
[Advanced: connect with an API key](../../README.md#advanced-connect-with-an-api-key) in the repo README.

## ChatGPT

The same folder is the ChatGPT plugin package. Each assistant reads its own manifest:

| File | Read by |
|---|---|
| `.claude-plugin/plugin.json` | Claude: plugin identity and the MCP server (sign-in) |
| `plugin.json` | ChatGPT: identity, listing, starter prompts, review test cases, translations (`extensions.com.openai`) |
| `mcp.json` | ChatGPT: the MCP server. Sign-in is discovered from the server (Client ID Metadata Document) |
| `.grok-plugin/plugin.json` | Grok: plugin identity and the MCP server (see [Grok](#grok)) |
| `skills/`, `assets/` | All three |
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

## Grok

The same folder is also the Grok plugin, for Grok Bot, Grok Build and Cursor. Grok reads
`.grok-plugin/plugin.json` first: the plugin identity and the MCP server. It loads `skills/` and leaves
out `claude-skills/`. Sign-in works the same way as in ChatGPT, with a Client ID Metadata Document.

**Grok Bot and Cursor:** submit through xAI's marketplace form with this repo's URL, a short description,
testing instructions and a square logo on a solid background, then pick both Grok Bot and Cursor.
Submit only after CloudTalk sign-in accepts Grok Bot and Cursor in production; check by signing in from
both first.

**Grok Build:** open a pull request to [xai-org/plugin-marketplace](https://github.com/xai-org/plugin-marketplace)
that adds this entry to `.grok-plugin/marketplace.json`. Pin `sha` to the released commit on `main`, then
regenerate the index as its CONTRIBUTING describes.

```json
{
  "name": "cloudtalk",
  "description": "Official CloudTalk plugin for Grok. Follow up missed calls and unanswered texts the same day, find open loops after calls, coach your team, and build and check AI Voice Agents, through CloudTalk's hosted OAuth MCP server.",
  "category": "productivity",
  "source": {
    "source": "url",
    "url": "https://github.com/CloudTalk-io/marketplace.git",
    "sha": "<40-character commit on main>",
    "path": "plugins/cloudtalk"
  },
  "homepage": "https://www.cloudtalk.io/",
  "keywords": ["cloudtalk", "cloudtalk mcp", "cloudtalk phone", "cloudtalk missed calls", "cloudtalk voice agent"],
  "domains": ["cloudtalk.io", "mcp.cloudtalk.io", "help.cloudtalk.io"]
}
```

**Grok Bot template, "Missed Call Follow-Up by CloudTalk":** publish it after the plugin is approved, with
this prompt and a weekday schedule the customer picks:

> Use CloudTalk's missed-call-follow-up skill. On the first run, ask me which lines or teams count,
> my response time, my business name and hours, and where to deliver (a Slack channel or an email
> address), and save them. On every scheduled run, cover the time since the last run, then deliver
> the list there. Never text or call anyone unless I approve it in the thread.
