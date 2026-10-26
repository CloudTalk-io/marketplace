# CloudTalk

Run every call from your AI assistant. CloudTalk is the agent-first phone system: AI agents answer
first, humans close.

This plugin connects your AI assistant to your CloudTalk account through the CloudTalk MCP
(`https://mcp.cloudtalk.io`) and ships four skills:

| Skill | What it does | Needs |
|---|---|---|
| [`get-started`](./skills/get-started/SKILL.md) | Checks the connection, finds what your account has (AI Voice Agents, call insights, campaigns), and offers three first tasks that work on it. | Essential plan |
| [`conversation-insight-log`](./skills/conversation-insight-log/SKILL.md) | A prioritized weekly log of requests, risks, opportunities, commitments and recurring friction, each tied to the call it came from. | Conversation Intelligence |
| [`sales-lead-scoring`](./skills/sales-lead-scoring/SKILL.md) | Scores leads from recent sales calls from 0 to 100 and ranks who to call back first, with the evidence. | Conversation Intelligence |
| [`service-scorecard`](./skills/service-scorecard/SKILL.md) | Scores support calls against a six-point service checklist and gives each agent a strength and one coaching point. | Conversation Intelligence |

## Example prompts

- Who called yesterday that we missed, and who should we call back first?
- Have our AI Voice Agent call a customer to confirm their appointment
- Set up an AI Voice Agent that answers questions from our website
- Give me this week's conversation insight log

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

## ChatGPT

The same folder is the ChatGPT plugin package. Each assistant reads its own manifest:

| File | Read by |
|---|---|
| `.claude-plugin/plugin.json` | Claude: plugin identity and the MCP server |
| `plugin.json` | ChatGPT: identity, listing, starter prompts, review test cases, translations (`extensions.com.openai`) |
| `mcp.json` | ChatGPT: the MCP server. Sign-in is discovered from the server (Client ID Metadata Document) |
| `skills/`, `assets/` | Both |

Build the upload ZIP from this folder:

```bash
cd plugins/cloudtalk
zip -r ../../cloudtalk-chatgpt.zip plugin.json mcp.json skills assets
```

Upload it at [platform.openai.com/plugins](https://platform.openai.com/plugins), then connect the MCP
server and enter the reviewer credentials in the portal. Credentials never go in this folder.

**Still needed before the first ChatGPT submission:** a demo recording URL
(`review.demo_recording_url`), the country list (`publication.countries`), a reviewer account on a
demo company, and a run of the five test cases against it.
