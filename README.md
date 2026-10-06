# CloudTalk Claude Plugins

CloudTalk's Claude plugin marketplace — plugins for building and testing
[CloudTalk](https://www.cloudtalk.io) **AI VoiceAgents** with Claude.

**CloudTalk VoiceAgent Builder** (`voice-agent-config-generator`) bundles two skills:

| Skill | What it does |
|---|---|
| [`voice-agent-config-generator`](./plugins/voice-agent-config-generator/skills/voice-agent-config-generator) | Generate, fix, and validate **VoiceAgent v2 (Expert Mode)** JSON configurations for any inbound/outbound use case, with a structural + behavioral validator run before every hand-back. |
| [`simulate-conversation`](./plugins/voice-agent-config-generator/skills/simulate-conversation/README.md) | Roleplay a caller persona against a config and score the transcript with an automated judge — test an agent before it takes real calls. |

It works two ways:

- **Standalone (offline).** No account connection needed. Describe the agent you want; the skill
  generates a validated, save-ready JSON config that you paste into the CloudTalk dashboard's
  **Expert Mode** (Advanced/code tab).
- **Connected (CloudTalk MCP).** Connect the CloudTalk MCP and Claude can also read and operate
  your real account — numbers, knowledge bases, tools, and VoiceAgents — and save configs for you.
  **Every write to your account requires your explicit confirmation** (one no-op exception: an
  assign/unassign that changes nothing).

## Install

**In Claude Code (CLI or IDE):**

```
/plugin marketplace add CloudTalk-io/marketplace
/plugin install voice-agent-config-generator@cloudtalk
```

**In the Claude app (claude.ai / desktop):** Customize → **Plugins** → **Add** → **Add marketplace** →
`CloudTalk-io/marketplace`, then add **CloudTalk VoiceAgent Builder**. The plugin runs in the Claude app
as well as in Claude Code.

That's all you need for offline use. To let Claude operate your account, connect the MCP below.

## Connect your CloudTalk account (optional)

The CloudTalk MCP (voice-agents profile) is a streamable-HTTP server at
`https://mcp.cloudtalk.io/voice-agents` (**no trailing slash** — the URL is exact). It
authenticates with **HTTP Basic** using a company API key.

1. Create an API key in the CloudTalk dashboard: **Account → Settings → API keys**. You get a
   key ID and a key secret.
2. Build the credential — it's the base64 of `API_KEY_ID:API_KEY_SECRET` (note the colon):

   ```bash
   echo -n "API_KEY_ID:API_KEY_SECRET" | base64
   ```

   This one step stays manual: the plugin can collect and store the value, but it cannot compute
   the base64 for you.

3. **Give Claude the key (easiest path).** The plugin bundles the MCP server and declares the key as
   plugin configuration:
   - **Claude Code** prompts you for it when the plugin is enabled — paste the base64 from step 2; the
     input is masked and stored in your OS keychain (or `~/.claude/.credentials.json`), not a dotfile.
     Needs Claude Code **2.1.207** or later (when `userConfig` prompting landed); on an older CLI, use step 4.
   - **Claude app** — open the plugin (Customize → Plugins) and its **Connectors** tab. If the CloudTalk
     connector shows **Not added**, add it; then **Connect** and paste the base64 into the popup. The
     field may be labelled "Bearer" — that's cosmetic; the plugin sends the value with the correct
     **Basic** scheme, so paste the base64 as-is.

   Leave it empty to stay offline. To replace the key later, update the plugin's stored configuration.

4. **Or add the server yourself** (independent of the plugin — useful for a machine-wide setup, or
   when you'd rather not install the plugin's MCP at all):

   ```bash
   claude mcp add --scope user --transport http cloudtalk-voice-agents \
     https://mcp.cloudtalk.io/voice-agents \
     -H "Authorization: Basic <base64 of API_KEY_ID:API_KEY_SECRET>"
   ```

> **Adding the server as your own custom connector** (outside the plugin) in claude.ai or Claude Desktop:
> the server authenticates via an `Authorization: Basic …` header, so this works only if the connector
> UI lets you set a custom Authorization header. Connector UIs that only accept a Bearer token cannot
> authenticate against it.

**No key? Everything still works.** With no key configured the bundled server simply doesn't
connect: it shows up as a failed entry in `/mcp` and in the plugin's Errors tab, which is harmless
and does not affect offline authoring. The skills still generate, fix, validate, and simulate
configs offline; you paste the result into Expert Mode yourself.

## Limitations

- **Authentication** is company API keys over HTTP Basic; OAuth is planned. The base64 step is
  yours to run once — the plugin stores the result, it does not compute it.
- **A non-admin API key is more limited than it looks.** It can list your VoiceAgents, but the other
  config reads (fetching one agent, listing knowledge bases or custom tools) and **every** write fail
  with an authorization error. If one list works and nothing else does, check the key's role
  (`cloudtalk_health_check` echoes it, along with `rollout_enabled` — which tells "this account isn't
  enabled for the MCP yet" apart from an auth problem).
- **Authorization** is account-wide today — finer role-based restriction of what a key can do
  through the MCP is still evolving.
- **Some operations stay in the dashboard** for now: inbound number routing, calendar
  connections, file-based knowledge bases, and looking up a ring group's extension.
- **Every account write is confirm-gated** (one no-op exception: an assign/unassign that changes
  nothing) — Claude always shows what it's about to change and waits for you; nothing is saved to
  your account silently.

## Updates & changelog

Each release carries a semver (in the plugin manifest and the marketplace catalog) and a matching
dated entry in [CHANGELOG.md](./CHANGELOG.md), bumped whenever the config schema or the generation
guidance materially changes. Updates follow the version: a new release reaches Claude Code when the
manifest version changes. Auto-update is off by default for third-party marketplaces, so either turn it
on (`/plugin` → **Marketplaces** → `cloudtalk` → **Enable auto-update**) or update by hand with **Update
now** on the plugin's **Installed** tab, or `claude plugin update voice-agent-config-generator@cloudtalk`.
The Claude app picks up new versions from the marketplace (**Check for updates**, or **Sync
automatically** for a marketplace you added yourself).

## Repo layout

```
marketplace/
├── .claude-plugin/
│   └── marketplace.json                 ← the catalog (lists every plugin)
└── plugins/
    └── voice-agent-config-generator/
        ├── .claude-plugin/
        │   └── plugin.json              ← plugin manifest (incl. the bundled MCP server)
        ├── icon.png                     ← directory-listing icon
        └── skills/
            ├── voice-agent-config-generator/
            │   ├── SKILL.md             ← skill entry point (trigger + router)
            │   └── …                    ← bundled refs, examples, validator
            └── simulate-conversation/
                ├── SKILL.md             ← caller-persona simulator + judge
                └── README.md            ← what it does, personas, rubric summary
```

## Contributing & license

Contributions are welcome — see [CONTRIBUTING.md](./CONTRIBUTING.md) for local test and
validation steps. Licensed under [Apache-2.0](./LICENSE).
