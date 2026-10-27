# CloudTalk Claude Plugins

CloudTalk's Claude plugin marketplace. [CloudTalk](https://www.cloudtalk.io) is the agent-first phone
system: AI agents answer first, humans close.

## The CloudTalk plugin

[**CloudTalk**](./plugins/cloudtalk) (`cloudtalk`) runs every call from your AI assistant. It signs in to
your CloudTalk account and ships eight skills. It used to be **CloudTalk VoiceAgent Builder**
(`voice-agent-config-generator`); see [Upgrading](#upgrading-from-cloudtalk-voiceagent-builder).

| Skill | What it does |
|---|---|
| [`get-started`](./plugins/cloudtalk/skills/get-started/SKILL.md) | Checks the connection, finds what your account has, and offers three first tasks that work on it. |
| [`conversation-insights`](./plugins/cloudtalk/skills/conversation-insights/SKILL.md) | Turns recent conversations into open loops, and says who should close each one: a person or an AI Voice Agent. |
| [`missed-call-follow-up`](./plugins/cloudtalk/skills/missed-call-follow-up/SKILL.md) | Finds today's missed callers nobody has reached yet, drafts a short text back to each from their history, and sends only what you approve. |
| [`call-coach`](./plugins/cloudtalk/skills/call-coach/SKILL.md) | Coaches your team and your AI Voice Agents from real calls. |
| [`voice-agent-builder`](./plugins/cloudtalk/skills/voice-agent-builder) | Generates, fixes and validates **VoiceAgent v2 (Expert Mode)** configurations for any inbound or outbound use case, and runs a structural and behavioral validator before every hand-back. Works offline too. |
| [`voice-agent-checkup`](./plugins/cloudtalk/skills/voice-agent-checkup/SKILL.md) | Checks whether an AI Voice Agent is ready to go live: a verdict, the fix to make first, the tests to run and a go-live checklist. Read-only. |
| [`voice-agent-replay`](./plugins/cloudtalk/skills/voice-agent-replay/SKILL.md) | Improves a live AI Voice Agent from its real calls: failures grouped by cause, two calls of proof each, and the setup change that fixes each one. |
| [`voice-agent-simulator`](./plugins/cloudtalk/claude-skills/voice-agent-simulator/README.md) | Roleplays a caller persona against a configuration and scores the transcript with an automated judge, so you can test an agent before it takes real calls. Claude only. |

The same folder is also the ChatGPT plugin package; see its [README](./plugins/cloudtalk/README.md).

## Install

**In Claude Code (CLI or IDE):**

```
/plugin marketplace add CloudTalk-io/marketplace
/plugin install cloudtalk@cloudtalk
```

**In the Claude app (claude.ai / desktop):** Customize → **Plugins** → **Add** → **Add marketplace** →
`CloudTalk-io/marketplace`, then add **CloudTalk**.

## Upgrading from CloudTalk VoiceAgent Builder

VoiceAgent Builder is now the CloudTalk plugin. When the marketplace updates, your settings move to the new
name on their own. Two steps are yours, once:

1. **Install the new name.** In Claude Code, run `/plugin install cloudtalk@cloudtalk`; it replaces
   VoiceAgent Builder. In the Claude app, open Customize → **Plugins** and add **CloudTalk** if it isn't
   there.
2. **Connect again.** Sign in with CloudTalk (below). If you prefer your API key, paste it once more: a
   saved key doesn't carry over to the new name.

Your skills are still there under new names: `voice-agent-config-generator` is now `voice-agent-builder`,
and `simulate-conversation` is now `voice-agent-simulator`. If you allowed CloudTalk tools in your
permission settings, their names now start with `mcp__plugin_cloudtalk_`.

## Connect your CloudTalk account

**Sign in (recommended).** The plugin's `cloudtalk` connection is the CloudTalk MCP at
`https://mcp.cloudtalk.io`. Sign in with CloudTalk as an **Admin** and approve the access; there is no key
to create or paste.

- **Claude Code:** run `/mcp`, pick `plugin:cloudtalk:cloudtalk`, and choose **Authenticate**.
- **Claude app:** open the plugin (Customize → Plugins), its **Connectors** tab, and **Connect** the
  `cloudtalk` connector.

CloudTalk's AI connection needs the Essential plan or higher. AI Voice Agents, Conversation Intelligence
and Sales Dialer unlock the matching tools.

**Or use an API key (voice agent tools only).** The optional `cloudtalk-voice-agents` connection is the
voice-agents profile at `https://mcp.cloudtalk.io/voice-agents`, with a company API key over HTTP Basic.
It carries the tools `voice-agent-builder` and `voice-agent-simulator` use, and nothing else.

1. Create an API key in the CloudTalk dashboard: **Account → Settings → API keys**. You get a key ID and
   a key secret.
2. Build the credential, the base64 of `API_KEY_ID:API_KEY_SECRET` (note the colon):

   ```bash
   echo -n "API_KEY_ID:API_KEY_SECRET" | base64
   ```

3. **Claude Code** asks for it when the plugin is enabled, or later with
   `/plugin configure cloudtalk@cloudtalk`. Paste the base64 from step 2; the input is masked and stored
   in your OS keychain (or `~/.claude/.credentials.json`), not a dotfile. In the **Claude app**, Connect the `cloudtalk-voice-agents` connector and paste it into the popup (a "Bearer"
   label there is cosmetic; the plugin sends it as **Basic**).

Leave the key empty if you signed in. The `cloudtalk-voice-agents` connection then shows as failed in
`/mcp`, which is expected and harmless.

To add the server yourself instead, outside the plugin:

```bash
claude mcp add --scope user --transport http cloudtalk-voice-agents \
  https://mcp.cloudtalk.io/voice-agents \
  -H "Authorization: Basic <base64 of API_KEY_ID:API_KEY_SECRET>"
```

**No connection at all?** `voice-agent-builder` still works offline: describe the agent, and Claude hands
back a validated, save-ready configuration to paste into the dashboard's **Expert Mode** (Advanced/code
tab). The other skills need a connection.

## Limitations

- **Sign-in** needs a CloudTalk **Admin**. The API key connection reaches the voice agent tools only, and
  its base64 step is yours to run once: the plugin stores the result, it does not compute it.
- **A non-admin API key is more limited than it looks.** It can list your VoiceAgents, but the other
  config reads (fetching one agent, listing knowledge bases or custom tools) and **every** write fail with
  an authorization error. If one list works and nothing else does, check the key's role:
  `cloudtalk_health_check` echoes the company, user and role the connection resolved to. An account that
  isn't eligible is refused before any tool runs, with a message that says why: the account isn't active,
  the plan is below Essential, or the account couldn't be verified.
- **Authorization** is account-wide today. Finer role-based restriction of what a connection can do
  through the MCP is still evolving.
- **Some operations stay in the dashboard** for now: inbound number routing, calendar connections,
  file-based knowledge bases, and looking up a ring group's extension.
- **You approve every account write.** Claude says what it's about to change, then asks you once to
  allow it; nothing is saved to your account silently.

## Updates & changelog

Each release carries a semver (in the plugin manifest and the marketplace catalog) and a matching dated
entry in [CHANGELOG.md](./CHANGELOG.md). Updates follow the version: a new release reaches Claude Code
when the manifest version changes. Auto-update is off by default for third-party marketplaces, so either
turn it on (`/plugin` → **Marketplaces** → `cloudtalk` → **Enable auto-update**) or update by hand with
**Update now** on the plugin's **Installed** tab, or `claude plugin update cloudtalk@cloudtalk`. The
Claude app picks up new versions from the marketplace (**Check for updates**, or **Sync automatically**
for a marketplace you added yourself).

## Repo layout

```
marketplace/
├── .claude-plugin/
│   └── marketplace.json        ← the catalog, plus the rename from voice-agent-config-generator
└── plugins/
    └── cloudtalk/
        ├── .claude-plugin/
        │   └── plugin.json     ← Claude manifest: both MCP connections, the optional API key
        ├── plugin.json         ← ChatGPT manifest (listing, starter prompts, review cases)
        ├── mcp.json            ← ChatGPT MCP connection
        ├── assets/icon.png
        ├── skills/             ← skills for Claude and ChatGPT
        │   ├── get-started/
        │   ├── conversation-insights/
        │   ├── missed-call-follow-up/
        │   ├── call-coach/
        │   ├── voice-agent-builder/   ← SKILL.md, bundled refs, examples, validator
        │   ├── voice-agent-checkup/
        │   └── voice-agent-replay/
        └── claude-skills/      ← skills for Claude only
            └── voice-agent-simulator/
```

## Contributing & license

Contributions are welcome. See [CONTRIBUTING.md](./CONTRIBUTING.md) for local test and validation steps.
Licensed under [Apache-2.0](./LICENSE).
