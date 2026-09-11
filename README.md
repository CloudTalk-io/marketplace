# CloudTalk Claude Plugins

CloudTalk's Claude plugin marketplace — plugins for building and testing
[CloudTalk](https://www.cloudtalk.io) **AI voice agents** with Claude.

The `voice-agent-config-generator` plugin bundles two skills:

| Skill | What it does |
|---|---|
| [`voice-agent-config-generator`](./plugins/voice-agent-config-generator/skills/voice-agent-config-generator) | Generate, fix, and validate **Voice Agent v2 (Expert Mode)** JSON configurations for any inbound/outbound use case, with a structural + behavioral validator run before every hand-back. |
| [`simulate-conversation`](./plugins/voice-agent-config-generator/skills/simulate-conversation/README.md) | Roleplay a caller persona against a config and score the transcript with an automated judge — test an agent before it takes real calls. |

It works two ways:

- **Standalone (offline).** No account connection needed. Describe the agent you want; the skill
  generates a validated, save-ready JSON config that you paste into the CloudTalk dashboard's
  **Expert Mode** (Advanced/code tab).
- **Connected (CloudTalk MCP).** Connect the CloudTalk MCP and Claude can also read and operate
  your real account — numbers, knowledge bases, tools, and voice agents — and save configs for you.
  **Every write to your account requires your explicit confirmation** (one no-op exception: an
  assign/unassign that changes nothing).

## Install (Claude Code)

```
/plugin marketplace add CloudTalk-io/marketplace
/plugin install voice-agent-config-generator@cloudtalk
```

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

3. **Easiest path — let the plugin ask.** The plugin bundles the MCP server and declares the key
   as plugin configuration, so **Claude Code prompts you for it when the plugin is enabled**. Paste
   the base64 string from step 2 into that prompt: the input is masked, and the value goes into
   your OS keychain (or `~/.claude/.credentials.json` where there is no keychain) rather than into
   a settings file or a shell profile. Nothing to export, nothing to keep in a dotfile.

   Leave the prompt empty to stay offline. To replace the key later, update the plugin's stored
   configuration from the `/plugin` manager.

   **This needs a recent Claude Code** — `userConfig` prompting landed in **2.1.207**. On an older CLI
   the placeholder is left unresolved, so add the server yourself instead (step 4).

4. **Or add the server yourself** (independent of the plugin — useful for a machine-wide setup, or
   when you'd rather not install the plugin's MCP at all):

   ```bash
   claude mcp add --scope user --transport http cloudtalk-voice-agents \
     https://mcp.cloudtalk.io/voice-agents \
     -H "Authorization: Basic <base64 of API_KEY_ID:API_KEY_SECRET>"
   ```

> **claude.ai / Claude Desktop connectors:** the server authenticates via a custom
> `Authorization: Basic …` header. A custom connector works only if the connector UI lets you set
> a custom Authorization header — connector UIs that only accept a Bearer token cannot
> authenticate against it.

**No key? Everything still works.** With no key configured the bundled server simply doesn't
connect: it shows up as a failed entry in `/mcp` and in the plugin's Errors tab, which is harmless
and does not affect offline authoring. The skills still generate, fix, validate, and simulate
configs offline; you paste the result into Expert Mode yourself.

## Limitations

- **Authentication** is company API keys over HTTP Basic; OAuth is planned. The base64 step is
  yours to run once — the plugin stores the result, it does not compute it.
- **A non-admin API key is more limited than it looks.** It can list your voice agents, but the other
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
guidance materially changes. Installs still track the latest `main` — Claude Code picks changes up
via `/plugin marketplace update cloudtalk` (or its background auto-update); the version is a marker,
not a pin.

## Repo layout

```
marketplace/
├── .claude-plugin/
│   └── marketplace.json                 ← the catalog (lists every plugin)
└── plugins/
    └── voice-agent-config-generator/
        ├── .claude-plugin/
        │   └── plugin.json              ← plugin manifest (incl. the bundled MCP server)
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
