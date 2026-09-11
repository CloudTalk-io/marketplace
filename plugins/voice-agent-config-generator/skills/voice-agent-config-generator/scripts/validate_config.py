#!/usr/bin/env python3
"""
validate_config.py — structural + dependency validator for Voice Agent v2 (Expert Mode) configs.

Validates the JSON body pasted into the dashboard's Advanced/code tab to edit an agent — the platform's
Expert-Mode save; the same body is valid on create. It is the programmatic companion to
the corpus: it enforces what `schema.md` §3/§6/§7 and `fields.json` say is *structurally valid*,
adds the highest-value *behavioral* lints from `behavioral-guidance.md` §8, and reports the environment
values to reuse plus anything that still needs wiring (`generator-contract.md` / `referenced-resources.md`).

Stdlib only — runs anywhere Python 3.8+ exists.

Usage:
    python scripts/validate_config.py <config.json|config.jsonc>
    cat config.json | python scripts/validate_config.py -
    python scripts/validate_config.py <file> --json     # machine-readable report
    python scripts/validate_config.py <file> --strict    # exit non-zero on warnings too

Exit codes: 0 clean (ordinary behavioral warnings allowed); 1 errors OR a blocking warning — the
save-refusing wiring (outbound-leftover-default, outbound-automatic-no-failover, transfer-no-rules) or a
config with no enabled hangup scenario (no-hangup, the non-negotiable end_call rule); the severity of
those stays WARN in the report; 2 unreadable/unparseable input.

Behavioral thresholds (all WARNs): temperature > 0.7; transfer-rule condition > 120 chars;
maxCallDuration <= 2 min (too tight) / > 30 min outbound / > 60 min inbound / > 120 min (a recommendation
only — there is no hard API cap); goalPrompt a one-liner (< 10 words) — length itself is not flagged, the
soft target is up to ~250 words; non-empty guardrails (accepted but inert at runtime); dialTime > 90 s
(saves, but call dispatch rejects it when the call is placed).

Accepts JSON or JSONC (// and /* */ comments and forgiving trailing commas) so it can validate the
bundled examples/ too. Enforces **paste-ready**: any non-schema top-level key (including a
`_requiredResources` block) and any placeholder/sentinel ID is an ERROR — the body must be schema-only
and run as-is.
"""

import argparse
import json
import os
import re
import sys

# ---------------------------------------------------------------------------
# Enumerations sourced from schema.md (kept here so the validator is self-contained).
# schema.md §4.3 — provider language sets. ElevenLabs' real accepted set is far wider than this (~66
# codes, essentially every plain two-letter one), so a code missing from here is NOT proof of an invalid
# language: unknown codes WARN, and the platform validates the authoritative set on save.
ELEVENLABS_LANGS = {
    "ar", "bg", "zh", "hr", "cs", "da", "nl", "en", "fi", "fr", "de", "el", "hu", "hi", "id",
    "it", "ja", "ko", "ms", "no", "pl", "pt", "ro", "ru", "sk", "es", "sv", "ta", "tr", "uk", "vi",
}
DEEPGRAM_LANGS = {
    "multi", "en", "en-US", "en-AU", "en-GB", "en-NZ", "en-IN", "bg", "ca", "zh", "zh-CN", "zh-Hans",
    "zh-TW", "zh-Hant", "zh-HK", "cs", "da", "da-DK", "nl", "et", "fi", "nl-BE", "fr", "fr-CA", "de",
    "de-CH", "el", "hi", "hu", "id", "it", "ja", "ko", "lv", "lt", "ms", "no", "pl", "pt", "pt-BR",
    "pt-PT", "ro", "ru", "sk", "es", "es-419", "sv", "th", "tr", "uk", "vi",
}
# schema.md §4.3/§5 — ElevenLabs takes every plain two-letter code, so provider auto-selection cannot key
# off absence from the short list above: the codes only Deepgram has are the NON-plain ones (`multi` and
# the regional variants, en-US / pt-BR / es-419 / zh-Hans …). Deriving the exclusive set keeps the two
# lists from disagreeing when a code is added to DEEPGRAM_LANGS.
PLAIN_LANG_CODE_RE = re.compile(r"^[a-z]{2}$")
DEEPGRAM_EXCLUSIVE_LANGS = {c for c in DEEPGRAM_LANGS if not PLAIN_LANG_CODE_RE.match(c)}

# schema.md §4.2 — canonical LLM IDs offered per provider (the only valid `llmOverride` values).
ELEVENLABS_MODELS = {
    "openai - gpt-4o-mini", "openai - gpt-4o", "openai - gpt-4.1", "openai - gpt-4.1-mini",
    "openai - gpt-4.1-nano", "openai - gpt-5", "openai - gpt-5-mini", "openai - gpt-5-nano",
    "openai - gpt-5.1", "openai - gpt-5.2", "openai - gpt-5.4", "openai - gpt-5.4-mini",
    "openai - gpt-5.4-nano", "openai - gpt-5.5", "anthropic - claude-haiku-4-5",
    "anthropic - claude-sonnet-4-5", "anthropic - claude-sonnet-4-6", "google - gemini-2.5-flash",
    "google - gemini-2.5-flash-lite", "google - gemini-3-flash-preview",
    "google - gemini-3.1-flash-lite", "google - gemini-3.5-flash", "google - gemini-3.6-flash",
    "qwen - qwen36-35b-a3b", "qwen - qwen35-397b-a17b",
}
DEEPGRAM_MODELS = {
    "openai - gpt-4o-mini", "openai - gpt-4o", "openai - gpt-4.1", "openai - gpt-4.1-mini",
    "openai - gpt-4.1-nano", "openai - gpt-5-mini", "openai - gpt-5-nano", "openai - gpt-5.4-mini",
    "openai - gpt-5.4-nano", "anthropic - claude-haiku-4-5", "google - gemini-2.5-flash",
    "google - gemini-3-flash-preview", "google - gemini-3.1-flash-lite", "google - gemini-3.5-flash",
}
# schema.md §4.2 — legacy aliases: accepted on input but normalized to a canonical ID on save.
LEGACY_LLM_ALIASES = {
    "open_ai - gpt-4.1-2025-04-14": "openai - gpt-4.1",
    "open_ai - gpt-4.1-mini-2025-04-14": "openai - gpt-4.1-mini",
    "open_ai - gpt-4.1-nano-2025-04-14": "openai - gpt-4.1-nano",
    "open_ai - gpt-4o-2024-08-06": "openai - gpt-4o",
    "open_ai - gpt-5-mini-2025-08-07": "openai - gpt-5-mini",
    "open_ai - gpt-5-nano-2025-08-07": "openai - gpt-5-nano",
    "anthropic - claude-4-5-haiku-latest": "anthropic - claude-haiku-4-5",
    "anthropic - claude-3-haiku": "anthropic - claude-haiku-4-5",
    "anthropic - claude-3-haiku-20240307": "anthropic - claude-haiku-4-5",
    "anthropic - claude-3-7-sonnet": "anthropic - claude-sonnet-4-5",
    "google - gemini-2.0-flash-lite": "google - gemini-2.5-flash-lite",
    "google - gemini-1.5-pro": "google - gemini-2.5-flash",
}

# schema.md §4.4 — built-in premade voice IDs (global, self-contained). These four are usable on BOTH
# providers (CloudTalk serves ElevenLabs voices for every provider); the full catalog lives in the
# dashboard voice picker.
KNOWN_VOICE_IDS = {
    "cgSgspJ2msm6clMCkdW9", "IKne3meq5aSn9XLyUdCD", "cjVigY5qzO86Huf0OWal", "iP95p4xoKVk53GoZ742B",
}

PROPERTY_TYPES = {"STRING", "NUMBER", "BOOLEAN", "ARRAY"}      # schema.md §6.3 (UPPERCASE)
KNOWN_SKILLS = {                                               # schema.md §6 — the whole skill set
    "transferToHuman", "takeMessage", "extractData", "custom", "answerQuestions", "appointmentBooking",
}
SCENARIO_ACTIONS = {"toolCall", "sendSms", "hangup"}           # schema.md §7.1
SCENARIO_TRIGGER_TYPES = {"custom", "booking_confirmed"}       # schema.md §7.1
# schema.md §6.1 — plus "" as the legal "target not decided yet" value on a switched-off skill.
TRANSFER_DESTINATIONS = {"agent", "group", "call_flow"}
ANSWER_ACTIONS = {"admitUncertainty", "offerAlternative", "transferToHuman"}  # schema.md §6.5
TURN_EAGERNESS = {"patient", "normal", "eager"}                # schema.md §10
TURN_MODEL = {"turn_v2", "turn_v3"}                            # schema.md §10
BACKGROUND_SOUND_PRESETS = {                                   # schema.md §10
    "office", "office2", "restaurant", "city", "typing", "elevator", "elevator2", "elevator3", "elevator4",
}
BACKGROUND_SOUND_FIELDS = ("preset", "volume", "crossfadeLoop")  # schema.md §10 — preset required
TONE_PRESETS = {"professional", "friendly", "casual", "calm", "empathetic", "direct"}  # schema.md §11
VERBOSITIES = {"concise", "standard", "thorough"}              # schema.md §11
# schema.md §10 — the object's documented sub-fields and the shape each one takes: "bool", "str[]",
# "object", or a set of allowed strings. Nothing downstream type-checks these, so a plausible-looking
# wrong shape (an object where a flag belongs) would otherwise reach the API unremarked.
ELEVENLABS_SETTING_SHAPES = {
    "speculativeTurn": "bool",
    "turnEagerness": TURN_EAGERNESS,
    "turnModel": TURN_MODEL,
    "vad": "bool",
    "asrKeywords": "str[]",
    "interruptionIgnoreTerms": "str[]",
    "interruptionIgnoreTermLanguages": "str[]",
    "backgroundSound": "object",
}


# `skills` is the container key for the whole skills section, so it has no fields.json topLevel row of
# its own (the section lives under the frozen top-level `skills` block); patch it in here.
EXTRA_TOPLEVEL_KEYS = {"skills"}

# fields.json `forbidden` rows the platform EMITS rather than accepts. Like the system-managed keys they
# ride along on a read, so an echoed export is a note (INFO), not an unknown-field error. (`upgradeSummary`
# is NOT here — no such field exists.)
RESPONSE_ONLY_DIAGNOSTIC_KEYS = {"warnings", "errorCodes", "upgradeAvailable"}

# Obvious placeholder/sentinel ID markers — these must never appear in a paste-ready body.
HEX_SENTINEL_RE = re.compile(r"^0{18,23}[0-9a-fA-F]{1,6}$")     # 24-hex starting with many zeros

# fields.json rows that name a DIRECT sub-key of a skill object: `skills.<skill>.<key>` or, for the
# list-shaped `custom` skill, `skills.custom[].<key>`. Rows that dive deeper
# (`skills.transferToHuman.rules[].condition`) describe a nested shape, not a key of the skill itself.
SKILL_SUBKEY_RE = re.compile(r"^skills\.(?P<skill>[A-Za-z]+)(?:\[\])?\.(?P<key>[A-Za-z][A-Za-z0-9]*)$")

# WARN codes where the backend refuses the save outright.
SAVE_REFUSED_CODES = {"outbound-leftover-default", "outbound-automatic-no-failover",
                      "transfer-no-rules"}
# The gate for "nothing else to wire" and for the non-zero exit: the save-refusing wiring above, plus
# `no-hangup` — that one saves fine, but the runtime then tells the agent it cannot end a call, which is
# never a config worth pasting. Its severity stays WARN in the report; only this gate treats it as fatal.
SAVE_BLOCKING_CODES = SAVE_REFUSED_CODES | {"no-hangup"}

# Severity glyphs for the human report. Windows consoles default to cp1252/cp437, where printing one of
# these raises UnicodeEncodeError and the whole report is lost — hence the ASCII twin.
GLYPHS = {"ERROR": "✗", "WARN": "⚠", "INFO": "ℹ", "ok": "✅", "bullet": "•"}
GLYPHS_ASCII = {"ERROR": "x", "WARN": "!", "INFO": "i", "ok": "[ok]", "bullet": "-"}


# ---------------------------------------------------------------------------
class Issue:
    __slots__ = ("level", "code", "where", "msg")

    def __init__(self, level, code, where, msg):
        self.level = level    # ERROR | WARN | INFO
        self.code = code      # short stable code
        self.where = where    # JSON path
        self.msg = msg

    def as_dict(self):
        return {"level": self.level, "code": self.code, "where": self.where, "message": self.msg}


class Report:
    def __init__(self):
        self.issues = []
        self.references = []   # referenced company resources (KB, tool, agent/group, calendar, sms)
        self.env_refs = []     # environment values to REUSE from the agent (outbound number)

    def err(self, code, where, msg):
        self.issues.append(Issue("ERROR", code, where, msg))

    def warn(self, code, where, msg):
        self.issues.append(Issue("WARN", code, where, msg))

    def info(self, code, where, msg):
        self.issues.append(Issue("INFO", code, where, msg))

    def at(self, level, code, where, msg):
        """Emit at a caller-chosen level. Used to downgrade the *completeness* checks of a disabled unit
        to a non-blocking note — a switched-off skill's unfinished target can't reach a live call, so it
        is something to finish in the dashboard. Structural keys are a different matter and stay ERRORs
        whatever `enabled` says: a missing `enabled` or `rules` still 422s the save."""
        self.issues.append(Issue(level, code, where, msg))

    def reference(self, field_path, kind, what, pending=False):
        """Record a company-scoped resource the config points at. `pending` means the config carries no
        value yet, so someone must go create or select one; the default is a value that IS present and
        only needs to exist (and be active/owned) in the target company. Only pending work can make a
        config "not ready" — a supplied id is wiring already done, however much it still deserves a look."""
        self.references.append((field_path, kind, what, pending))

    def environment(self, field_path, kind, what):
        self.env_refs.append((field_path, kind, what))

    @property
    def n_errors(self):
        return sum(1 for i in self.issues if i.level == "ERROR")

    @property
    def n_warnings(self):
        return sum(1 for i in self.issues if i.level == "WARN")


# ---------------------------------------------------------------------------
def strip_jsonc(text):
    """Remove // line comments and /* */ block comments, respecting double-quoted JSON strings."""
    out = []
    i, n = 0, len(text)
    in_string = False
    while i < n:
        c = text[i]
        if in_string:
            out.append(c)
            if c == "\\" and i + 1 < n:          # keep escaped char verbatim
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_string = False
            i += 1
            continue
        if c == '"':
            in_string = True
            out.append(c)
            i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def strip_trailing_commas(text):
    """Drop a comma that directly precedes a closing `}`/`]` (whitespace between allowed), but only
    outside double-quoted strings — a comma inside a string value (a goalPrompt/reply/message ending in
    ", }" or containing ", ]") must survive untouched. Mirrors strip_jsonc's string-state tracking."""
    out = []
    i, n = 0, len(text)
    in_string = False
    while i < n:
        c = text[i]
        if in_string:
            out.append(c)
            if c == "\\" and i + 1 < n:          # keep escaped char verbatim
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_string = False
            i += 1
            continue
        if c == '"':
            in_string = True
            out.append(c)
            i += 1
            continue
        if c == ",":
            j = i + 1
            while j < n and text[j] in " \t\r\n":
                j += 1
            if j < n and text[j] in "}]":
                i += 1                           # drop the comma; keep the whitespace + bracket
                continue
        out.append(c)
        i += 1
    return "".join(out)


def parse_config(raw):
    """Parse JSON or JSONC. Returns the config dict."""
    stripped = strip_jsonc(raw)
    try:
        obj = json.loads(stripped)
    except json.JSONDecodeError:
        obj = json.loads(strip_trailing_commas(stripped))   # forgiving retry
    if not isinstance(obj, dict):
        raise ValueError("Top-level JSON must be an object.")
    return obj


def load_fields(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def looks_sentinel(value):
    """True only for *unambiguous* placeholders that cannot collide with real data: a long
    all-leading-zero hex ObjectId, a REPLACE_WITH_* token, or an all-zero E.164. We deliberately do
    NOT guess from numeric values — real CloudTalk agent/group/number IDs are small integers, so a
    value like 101 or 201 is a perfectly valid real ID. Whether a real ID *exists* is the backend's
    job (the /validate endpoint), not this static check."""
    if isinstance(value, str):
        if HEX_SENTINEL_RE.match(value):
            return True
        if value.strip().upper().startswith("REPLACE_WITH"):
            return True
        if value.startswith("+") and value.replace("+", "").strip("0") == "":  # all-zero E.164, e.g. +00000000000
            return True
    return False


def flag_sentinels(cfg, rep):
    """ERROR: a placeholder/sentinel ID in the body is not paste-ready — the config will fail to import
    or won't function. Replace it with a real company ID, use a zero-touch substitute (e.g. call_flow),
    or omit the feature (generator-contract.md reference decision tree).
    """
    def check(where, value):
        if looks_sentinel(value):
            rep.err("sentinel-placeholder", where,
                    "%r is a placeholder/sentinel ID — not paste-ready. Use a real company ID, a "
                    "zero-touch substitute, or omit the feature (generator-contract.md)." % value)

    don = cfg.get("defaultOutboundNumberId")
    if don not in (1, None):                          # only 1 is a magic selector; 2 is a literal ID
        check("defaultOutboundNumberId", don)
    check("failoverOutboundNumberId", cfg.get("failoverOutboundNumberId"))
    kbs = cfg.get("knowledgeBaseIds")
    if isinstance(kbs, list):
        for i, k in enumerate(kbs):
            check("knowledgeBaseIds[%d]" % i, k)
    skills = cfg.get("skills")
    if isinstance(skills, dict):
        th = skills.get("transferToHuman")
        if isinstance(th, dict):
            for i, rule in enumerate(th.get("rules") or []):
                if isinstance(rule, dict):
                    for key in ("agentId", "agentExtension", "groupId", "groupExtension"):
                        check("skills.transferToHuman.rules[%d].%s" % (i, key), rule.get(key))
        ab = skills.get("appointmentBooking")
        if isinstance(ab, dict):
            check("skills.appointmentBooking.integrationId", ab.get("integrationId"))
            check("skills.appointmentBooking.calendarId", ab.get("calendarId"))
    scenarios = cfg.get("scenarios")
    if isinstance(scenarios, list):
        for i, s in enumerate(scenarios):
            if isinstance(s, dict):
                check("scenarios[%d].toolReferenceId" % i, s.get("toolReferenceId"))
                params = s.get("params")
                if isinstance(params, dict):
                    check("scenarios[%d].params.senderNumber" % i, params.get("senderNumber"))


def check_background_sound(val, where, rep):
    """backgroundSound sub-object (schema §10); nothing downstream type-checks it, so a wrong shape reaches the API unremarked."""
    if not isinstance(val, dict):
        rep.err("bad-type", where, "Expected an object {preset, volume?, crossfadeLoop?} (schema §10).")
        return
    preset = val.get("preset")
    if preset is None or (isinstance(preset, str) and not preset.strip()):
        rep.err("missing-required", "%s.preset" % where,
                "Required when backgroundSound is present (schema §10).")
    elif not isinstance(preset, str):
        rep.err("bad-type", "%s.preset" % where, "Expected a preset label string (schema §10).")
    elif preset not in BACKGROUND_SOUND_PRESETS:
        rep.err("bad-enum", "%s.preset" % where,
                "Must be one of %s (schema §10)." % sorted(BACKGROUND_SOUND_PRESETS))
    if "volume" in val:
        if not is_num(val["volume"]):
            rep.err("bad-type", "%s.volume" % where, "If set, must be a number in [0, 1] (schema §10).")
        elif not (0 <= val["volume"] <= 1):
            rep.err("out-of-range", "%s.volume" % where, "Must be in [0, 1] (schema §10).")
    if "crossfadeLoop" in val and not isinstance(val["crossfadeLoop"], bool):
        rep.err("bad-type", "%s.crossfadeLoop" % where, "Expected true or false (schema §10).")
    for k in val:
        if k not in BACKGROUND_SOUND_FIELDS:
            rep.err("unknown-field", "%s.%s" % (where, k),
                    "Not a documented backgroundSound field — the /validate endpoint (and this validator) "
                    "reject unknown keys, including nested ones; the save silently drops them (schema §10).")


# ---------------------------------------------------------------------------
def validate(cfg, fields, rep):
    toplevel = {f["path"]: f for f in fields.get("topLevel", [])}
    forbidden = {f["path"]: f.get("reason", "") for f in fields.get("forbidden", [])}
    required = [p for p, f in toplevel.items() if f.get("required") is True]

    # -- required fields -----------------------------------------------------
    for p in required:
        v = cfg.get(p)
        if v is None or (isinstance(v, str) and not v.strip()):
            rep.err("missing-required", p, "Required field is missing, null, or empty (schema §2).")

    # -- unknown / legacy / forbidden top-level keys -------------------------
    # NOTE: an unrecognized key is an ERROR here because the /validate endpoint (and this validator, its
    # offline twin) reject unknown keys. The create/update SAVE is more lenient — it relaxes
    # additionalProperties and SILENTLY DROPS an unknown/misspelled key rather than failing — which is
    # exactly why flagging it here matters: a typo the save would swallow (losing the field, unremarked)
    # is caught before it ships. fields.json must track the live v2 schema so a genuinely new v2 field is
    # not mistaken for a typo.
    recognized = set(toplevel) | EXTRA_TOPLEVEL_KEYS | set(forbidden)
    for key in cfg:
        if key in forbidden:
            reason = forbidden[key]
            if key == "firstMessage":
                rep.warn("forbidden-field", key,
                         "There is no `firstMessage` field in v2 — the opening line is `greeting`. "
                         "Move the text to `greeting` (schema §2 greeting note).")
            elif key in ("companyId", "environmentName"):
                rep.info("export-tag", key,
                         "Frontend export tag — the API ignores it, but if it differs from the target "
                         "company the UI treats this as a cross-company import (strips toolCall/sendSms, "
                         "replaces number IDs). Remove for a clean paste (schema §8).")
            elif key in ("hasOverrides", "presetType", "status", "lastConfigurationStep"):
                rep.info("system-managed", key,
                         "System-managed field — the platform owns it: on Expert-Mode save the editor sets it "
                         "from the loaded agent (and forces hasOverrides=true), and the server defaults or "
                         "recomputes the rest. Harmless in an export; the generator omits it (schema §2).")
            elif key in RESPONSE_ONLY_DIAGNOSTIC_KEYS:
                rep.info("response-only", key,
                         "Server-emitted diagnostic — the platform writes this key, you don't: it reports "
                         "what a read or a save found (and a SUCCESSFUL save can carry errorCodes; "
                         "upgradeAvailable is recomputed server-side). Echoing it back has no effect; the "
                         "generator omits it (schema §1/§2).")
            else:
                rep.warn("forbidden-field", key,
                         "Do not author this field (%s). It is ignored or stripped on import (schema §1/§5)." % reason)
        elif key not in recognized:
            rep.err("unknown-field", key,
                    "Not a recognized v2 field — remove it. The /validate endpoint (and this validator) "
                    "reject unknown keys; the create/update save is worse, silently DROPPING them, so a typo "
                    "or a legacy v1 field (voiceAgentPrompt/extractionPrompt/transferEnabled/hangupEnabled/"
                    "resultsEndpoint) or a `_requiredResources` block would vanish unremarked (schema §1/§9).")

    # -- top-level enums -----------------------------------------------------
    for p, f in toplevel.items():
        if "enum" not in f or cfg.get(p) is None:
            continue
        # On an array field the enum constrains each ELEMENT, not the list itself (tone); those are
        # checked per element below, so a scalar membership test here would reject every valid list.
        if str(f.get("type", "")).endswith("[]"):
            continue
        if cfg[p] not in f["enum"]:
            rep.err("bad-enum", p, "Value %r not in %s (schema §2)." % (cfg[p], f["enum"]))

    # -- numeric ranges ------------------------------------------------------
    for p, f in toplevel.items():
        if "range" in f and cfg.get(p) is not None:
            v = cfg[p]
            lo, hi = f["range"]
            if not is_num(v):
                rep.err("bad-type", p, "Expected a number in [%s, %s] (schema §3)." % (lo, hi))
            else:
                if f.get("type") == "int" and not float(v).is_integer():
                    rep.err("bad-type", p, "Must be an integer (schema §3).")
                if v < lo or v > hi:
                    rep.err("out-of-range", p, "%s out of range [%s, %s] (schema §3)." % (v, lo, hi))

    # -- types the enum/range loops above cannot reach ------------------------
    # A JSON string where a number belongs ("20") passes the required-field check and skips every range
    # check, which only runs on values that are already numbers — so it would reach the API unremarked.
    if cfg.get("agentName") is not None and not isinstance(cfg["agentName"], str):
        rep.err("bad-type", "agentName", "Expected a string (schema §2).")
    for p in ("maxCallDuration", "dialTime", "defaultOutboundNumberId", "failoverOutboundNumberId"):
        if cfg.get(p) is not None and not is_num(cfg[p]):
            rep.err("bad-type", p, "Expected a number, not %s (schema §2)." % type(cfg[p]).__name__)
    # The integer check in the range loop above only runs on fields that declare a `range`, so an
    # int-typed field without one (maxCallDuration, dialTime, the number IDs) would accept 30.5.
    for p, f in toplevel.items():
        if f.get("type") != "int" or "range" in f or cfg.get(p) is None:
            continue
        if is_num(cfg[p]) and not float(cfg[p]).is_integer():
            rep.err("bad-type", p, "Must be an integer (schema §3).")

    # -- outbound number dependency rules (schema §3.1-3.2) ------------------
    # Only 1 is magic (Automatic). Every other value -- including 2 -- is a literal company-owned
    # number ID; there is no backend "Random". Automatic (1) requires a real owned failover in BOTH
    # directions -- there is no inbound carve-out and no self-heal (schema §3, §8).
    direction = cfg.get("direction")
    don = cfg.get("defaultOutboundNumberId")
    if "failoverOutboundNumberId" in cfg and cfg["failoverOutboundNumberId"] is None:
        rep.err("null-failover", "failoverOutboundNumberId",
                "Omit the key instead of sending null — an explicit null is not a supported value, and on "
                "import it means exactly what an absent key means (referenced-resources.md#environment).")
    if don is not None:
        if don == 0:
            rep.err("number-zero", "defaultOutboundNumberId", "Must not be 0 (schema §3.1).")
        elif don == 1:
            if "failoverOutboundNumberId" not in cfg:
                rep.warn("outbound-automatic-no-failover", "failoverOutboundNumberId",
                         "Automatic (1) requires a real owned failoverOutboundNumberId in BOTH directions — "
                         "the save 400s without one and nothing self-heals it. Set a real owned number id "
                         "here (cloudtalk_list_numbers or the dashboard), or set defaultOutboundNumberId to a "
                         "real owned number id instead of 1 (referenced-resources.md#environment).")
            rep.environment("defaultOutboundNumberId", "phoneNumber",
                            "Automatic (1) — must be paired with a real owned failoverOutboundNumberId in "
                            "both directions. Reuse the agent's current failover; the config save does not "
                            "auto-pick a number (referenced-resources.md#environment).")
        else:
            if don == 2:
                rep.warn("outbound-leftover-default", "defaultOutboundNumberId",
                         "defaultOutboundNumberId is 2, which is NOT a backend \"Random\" selector — only 1 is "
                         "magic. 2 is a literal phone-number ID your company almost certainly doesn't own, so "
                         "the save is refused by name (\"outbound number 2 does not exist or does not belong to "
                         "the company\"). Set a real owned number id (cloudtalk_list_numbers or the dashboard) "
                         "(referenced-resources.md#environment).")
            rep.environment("defaultOutboundNumberId", "phoneNumber",
                            "Specific outbound number ID — must be a real number your company owns; obtain it "
                            "from cloudtalk_list_numbers or reuse the one already on your agent "
                            "(referenced-resources.md#environment).")

    # -- inbound must speak first (schema §3.3) ------------------------------
    if direction == "inbound" and cfg.get("startSpeakingFirst") is not True:
        rep.err("inbound-speak-first", "startSpeakingFirst",
                "Must be true when direction == \"inbound\" (schema §3.3).")
    elif direction == "outbound" and cfg.get("startSpeakingFirst") is False:
        rep.warn("outbound-speak-first", "startSpeakingFirst",
                 "An outbound agent with startSpeakingFirst: false stays silent until the contact it just "
                 "called speaks — the call opens with dead air. Set true and give it an identifying "
                 "greeting (behavioral §6).")

    # -- provider / language / llm consistency (schema §4-5) -----------------
    provider = resolve_provider(cfg)
    lang = cfg.get("language")
    if isinstance(lang, str):
        if lang not in (ELEVENLABS_LANGS | DEEPGRAM_LANGS):
            rep.warn("unknown-language", "language",
                     "%r is not in the validator's known language list, which trails the platform's — the "
                     "authoritative set is validated on save, so a plain two-letter code is likely fine "
                     "and a typo is not (schema §4.3)." % lang)
        else:
            supported = (elevenlabs_supports_language(lang) if provider == "elevenlabs"
                         else lang in DEEPGRAM_LANGS)
            if not supported:
                rep.warn("language-provider-mismatch", "language",
                         "Language %r is not in the resolved provider's set (%s). This usually comes from a "
                         "providerOverride that doesn't support the language (schema §4.3/§5)." % (lang, provider))

    sec = cfg.get("secondaryLanguages")
    ov = cfg.get("providerOverride")
    if sec:
        if provider == "deepgram":
            rep.err("deepgram-multilingual", "secondaryLanguages",
                    "Deepgram has no multilingual mode — secondaryLanguages with a Deepgram-resolved provider "
                    "is rejected (schema §3.7). Use ElevenLabs or drop secondaryLanguages.")
        elif ov != "elevenlabs":
            rep.err("multilingual-needs-elevenlabs-pin", "providerOverride",
                    "secondaryLanguages is set — pin providerOverride: 'elevenlabs'. Multilingual requires "
                    "ElevenLabs; pinning it stops an edited agent whose stored provider is Deepgram from "
                    "preserving it and rejecting the save (schema §5).")
    if isinstance(sec, list):
        for i, code in enumerate(sec):
            if not isinstance(code, str):
                rep.err("bad-type", "secondaryLanguages[%d]" % i,
                        "Expected a language-code string, not %s (schema §4.3)." % type(code).__name__)
            elif not elevenlabs_supports_language(code):
                # Same helper as the primary language, so a plain code (ca/et/lv/lt/th/af…) is accepted
                # here too. Which codes may join a given multilingual COMBINATION is server-validated —
                # this check only judges the code itself.
                rep.warn("bad-secondary-language", "secondaryLanguages[%d]" % i,
                         "%r is not a plain two-letter code and is not in the validator's known "
                         "ElevenLabs language list, which trails the platform's — the authoritative set "
                         "(and which codes may join a multilingual combination) is validated on save "
                         "(schema §4.3)." % code)
    elif sec is not None:
        rep.err("bad-type", "secondaryLanguages", "Expected a list of language codes (schema §3.7).")

    llm = cfg.get("llmOverride")
    if isinstance(llm, str) and llm:
        canonical = LEGACY_LLM_ALIASES.get(llm, llm)
        if canonical != llm:
            rep.info("llm-legacy-alias", "llmOverride",
                     "%r is a legacy alias — accepted but normalized to %r on save; prefer the canonical ID (schema §4.2)." % (llm, canonical))
        offered = ELEVENLABS_MODELS if provider == "elevenlabs" else DEEPGRAM_MODELS
        if canonical not in offered:
            if canonical in (ELEVENLABS_MODELS | DEEPGRAM_MODELS):
                rep.err("llm-provider-mismatch", "llmOverride",
                        "%r is not offered by the resolved provider (%s) — server returns 400 (schema §4.2)." % (canonical, provider))
            else:
                rep.warn("llm-unknown", "llmOverride",
                         "%r is not a canonical model ID in schema §4.2 (it may still be an accepted native mask)." % llm)

    # -- dialTime (schema §3.8) ----------------------------------------------
    dt = cfg.get("dialTime")
    if dt is not None and is_num(dt) and dt != 0:
        if not (5 <= dt <= 120):
            rep.err("dial-time", "dialTime", "If non-zero, must be 5-120 s (schema §3.8).")
        elif dt > 90:
            # The save accepts the whole 5-120 range; the dispatcher that actually places the call does
            # not, so a stored 120 means every outbound attempt is refused at dial time.
            rep.warn("dialtime-dispatch-limit", "dialTime",
                     "%s s saves fine but call dispatch rejects anything above 90 s — the call is never "
                     "placed. Keep dialTime at 90 or below (schema §3.8)." % dt)

    # -- elevenLabsSettings (schema §10) -------------------------------------
    els = cfg.get("elevenLabsSettings")
    if els is not None and not isinstance(els, dict):
        rep.err("bad-type", "elevenLabsSettings", "Expected an object (schema §10).")
    if isinstance(els, dict):
        for key, val in els.items():
            shape = ELEVENLABS_SETTING_SHAPES.get(key)
            where = "elevenLabsSettings.%s" % key
            if shape is None:
                # The /validate endpoint (and this validator) reject unknown keys recursively; the save
                # silently drops them. Flagging here catches what the save would swallow unremarked.
                rep.err("unknown-field", where,
                        "Not a documented elevenLabsSettings field — the /validate endpoint (and this "
                        "validator) reject unknown keys, including nested ones; the save silently drops them. "
                        "Allowed: %s (schema §10)." % ", ".join(sorted(ELEVENLABS_SETTING_SHAPES)))
            elif shape == "bool" and not isinstance(val, bool):
                rep.err("bad-type", where, "Expected true or false, not %s (schema §10)."
                        % type(val).__name__)
            elif isinstance(shape, (set, frozenset)):
                # Type before membership — an unhashable value must report, not crash the checker.
                if not isinstance(val, str):
                    rep.err("bad-type", where, "Expected a string (schema §10).")
                elif val not in shape:
                    rep.err("bad-enum", where, "Must be one of %s (schema §10)." % sorted(shape))
            elif shape == "str[]" and (not isinstance(val, list)
                                       or not all(isinstance(k, str) and k.strip() for k in val)):
                rep.err("bad-type", where, "Expected a list of non-empty strings (schema §10).")
            elif shape == "object":
                check_background_sound(val, where, rep)
        terms = els.get("interruptionIgnoreTerms")
        if isinstance(terms, list) and terms and not els.get("interruptionIgnoreTermLanguages"):
            rep.warn("interruption-terms-no-languages", "elevenLabsSettings.interruptionIgnoreTermLanguages",
                     "interruptionIgnoreTerms is set but interruptionIgnoreTermLanguages is empty — set the "
                     "two together (especially on a multilingual agent); a half-configured ignore-terms set "
                     "silently does nothing at runtime (schema §10).")
        if provider != "elevenlabs":
            rep.warn("elevenlabs-settings-ignored", "elevenLabsSettings",
                     "Resolved provider is %s — elevenLabsSettings is ignored (schema §10)." % provider)

    # -- voice ---------------------------------------------------------------
    voice = cfg.get("voice")
    if isinstance(voice, str) and voice and voice not in KNOWN_VOICE_IDS:
        rep.warn("voice-unknown", "voice",
                 "Voice ID is not in the documented default set (schema §4.4). Valid if it exists in the "
                 "voice library — pick from the dashboard voice picker for the full catalog — otherwise "
                 "import fails (schema §3.5).")

    # -- tone / verbosity (identity presets, schema §11) ---------------------
    tone = cfg.get("tone")
    if isinstance(tone, list):
        for i, t in enumerate(tone):
            if not isinstance(t, str) or t not in TONE_PRESETS:
                rep.err("bad-enum", "tone[%d]" % i,
                        "%r is not a tone preset — tone is a fixed 6-label allowlist %s, no free text (schema §11)."
                        % (t, sorted(TONE_PRESETS)))
        # Advisory only: the save accepts any number of allowlisted labels, and duplicates are deduped
        # server-side, so the count that matters is the distinct one.
        distinct_labels = {t for t in tone if isinstance(t, str)}
        if len(distinct_labels) > 2:
            rep.warn("tone-many-labels", "tone",
                     "%d distinct tone labels — prefer one or two: only one- and two-label combinations "
                     "have been validated, and a wider blend expresses each preset more weakly "
                     "(schema §11)." % len(distinct_labels))
    elif tone is not None:
        rep.err("bad-type", "tone", "Expected a list of tone presets (schema §11).")

    # verbosity accepts "" (unset), mirroring the empty-triggerType parity.
    verbosity = cfg.get("verbosity")
    if verbosity not in ("", None):
        if not isinstance(verbosity, str):
            rep.err("bad-type", "verbosity", "Expected a verbosity string (schema §11).")
        elif verbosity not in VERBOSITIES:
            rep.err("bad-enum", "verbosity",
                    "Value %r not in %s (schema §11)." % (verbosity, sorted(VERBOSITIES)))

    # -- skills / scenarios / behavioral -------------------------------------
    validate_skills(cfg, rep, direction, fields)
    validate_scenarios(cfg, rep)
    validate_guardrails(cfg, rep)
    behavioral_lints(cfg, rep, direction, provider)
    flag_sentinels(cfg, rep)

    # -- knowledge base reference --------------------------------------------
    kbs = cfg.get("knowledgeBaseIds")
    if isinstance(kbs, list):
        for i, k in enumerate(kbs):
            if not isinstance(k, str) or not k.strip():
                rep.err("bad-type", "knowledgeBaseIds[%d]" % i,
                        "Expected a non-empty knowledge-base ID string (schema §2).")
        if kbs:
            rep.reference("knowledgeBaseIds", "knowledgeBase",
                          "Each ID must be an ACTIVE knowledge base in the target company; create it first "
                          "(referenced-resources.md#knowledge-bases).")
    elif kbs is not None:
        rep.err("bad-type", "knowledgeBaseIds",
                "Expected a list of knowledge-base ID strings (schema §2).")


# ---------------------------------------------------------------------------
def elevenlabs_supports_language(code):
    """schema.md §4.3 — ElevenLabs' accepted set is ~66 codes: essentially every plain two-letter one,
    so a plain code counts as supported even when ELEVENLABS_LANGS (a documented subset) omits it."""
    return isinstance(code, str) and (bool(PLAIN_LANG_CODE_RE.match(code)) or code in ELEVENLABS_LANGS)


def resolve_provider(cfg):
    """V3 provider auto-selection (schema.md §5), honoring providerOverride."""
    ov = cfg.get("providerOverride")
    if ov in ("elevenlabs", "deepgram"):
        return ov
    if cfg.get("secondaryLanguages"):
        return "elevenlabs"
    lang = cfg.get("language")
    if isinstance(lang, str) and lang.strip():
        if lang in DEEPGRAM_EXCLUSIVE_LANGS:
            return "deepgram"             # `multi` or a regional variant ElevenLabs lacks (en-US, pt-BR…)
        # Every plain two-letter code resolves to ElevenLabs (schema §5 rule 3) — including ca/et/lv/lt
        # and any other code this file's documented subset has not caught up with.
        if PLAIN_LANG_CODE_RE.match(lang):
            return "elevenlabs"
        # schema §5 rule 4: anything left is a non-plain code ElevenLabs does not take — an unlisted
        # regional variant or a malformed value. Falling through to ElevenLabs here made rule 4
        # unreachable and suppressed the consequences (elevenlabs-settings-ignored, model mismatch).
        return "deepgram"
    return "elevenlabs"


def _check_properties(props, where, rep, level="ERROR"):
    if not isinstance(props, list):
        rep.at(level, "bad-type", where, "Expected a list of {name, type, description}.")
        return
    for idx, p in enumerate(props):
        loc = "%s[%d]" % (where, idx)
        if not isinstance(p, dict):
            rep.at(level, "bad-type", loc, "Each property must be an object {name, type, description}.")
            continue
        for k in ("name", "type", "description"):
            if not p.get(k):
                rep.at(level, "missing-required", "%s.%s" % (loc, k), "Required (schema §6.3).")
        t = p.get("type")
        if t is not None and (not isinstance(t, str) or t not in PROPERTY_TYPES):
            rep.at(level, "bad-enum", "%s.type" % loc,
                   "Must be UPPERCASE one of %s (schema §6.3); got %r." % (sorted(PROPERTY_TYPES), t))


def _check_transfer_destination(rule, where, rep, enabled=True, direction=None):
    """schema §6.1. A direct destination needs BOTH halves of its pair — agentId + agentExtension, or
    groupId + groupExtension — because the extension is part of the dial. Nothing downstream checks the
    values: the frontend forwards them verbatim, the API has no agent/group ownership check, and the
    runtime dials them raw, so a wrong or half-set target fails only mid-call — where advanced transfer is
    enabled the AI announces the failure and resumes, but on a cold fallback the caller is dropped
    silently. Hence: never guess a value, an empty string is worse than an absent key, and an incomplete
    target on a switched-off skill is something to finish in the dashboard rather than an import error."""
    if "destination" not in rule:
        rep.err("missing-required", "%s.destination" % where,
                "Required on every rule the config carries — a rule without the key is rejected on import "
                "(422). Use \"\" while the target is undecided (schema §6.1).")
        return
    dest = rule.get("destination")
    if not isinstance(dest, str):
        # Type before membership — an unhashable value must report, not crash the checker.
        rep.err("bad-type", "%s.destination" % where,
                "Expected a string — one of %s, or \"\" while undecided (schema §6.1)."
                % sorted(TRANSFER_DESTINATIONS))
        return
    if not dest.strip():
        # Unset is only legal while the skill is off; an enabled rule with nowhere to go is an error the
        # same way the API treats it (disabled unit → warning, enabled unit → error).
        if enabled:
            rep.err("missing-required", "%s.destination" % where,
                    "An enabled transfer rule needs a real destination — \"\" means \"not decided yet\", which "
                    "is only legal while the skill is switched off. Set agent/group (with the id AND the "
                    "extension), or — if you have authored a real rule you can't fully ground yet — ship the "
                    "skill `enabled: false` and KEEP the rule (its condition, destination, and whatever id you "
                    "have), omitting only the identifier you're still missing; emptying `rules` discards real "
                    "work (schema §6.1).")
        else:
            rep.info("unfinished-transfer", where,
                     "destination is unset — pick the agent or ring group on the skill in the dashboard, then "
                     "switch the skill on (referenced-resources.md#direct-transfers).")
            rep.reference("%s.destination" % where, "agent_or_group", pending=True,
                          what="Undecided target: pick the real agent or ring group on the skill in the "
                          "dashboard, then switch it on (referenced-resources.md#direct-transfers).")
        return
    if dest not in TRANSFER_DESTINATIONS:
        rep.err("bad-enum", "%s.destination" % where,
                "Must be one of %s, or \"\" while undecided (schema §6.1)." % sorted(TRANSFER_DESTINATIONS))
        return
    if dest == "call_flow":
        if direction == "outbound":
            rep.warn("call-flow-outbound", "%s.destination" % where,
                     "call_flow is inbound-only — an outbound agent has no Call Flow to return to, so this "
                     "\"transfer\" just hangs up on the contact. Use a direct agent/group target instead "
                     "(behavioral §3.4).")
        rep.info("call-flow-handoff", where,
                 "CFD handoff — the agent hangs up and the Call Flow continues, so it only does something "
                 "when this agent runs as a step inside a Call Flow (for a standalone agent it just ends the "
                 "call). A direct agent/group transfer is the default way to reach a human (schema §6.1).")
        return
    id_key, ext_key = ("agentId", "agentExtension") if dest == "agent" else ("groupId", "groupExtension")
    missing = []
    # The id is an INTEGER field (*int, omitempty); the extension is a string. An empty STRING where the
    # integer id belongs is an INVALID_TYPE the save rejects even on a disabled skill — a draft OMITS the
    # id key, it never blanks it to "".
    id_val = rule.get(id_key)
    if isinstance(id_val, str):
        rep.err("empty-transfer-id", "%s.%s" % (where, id_key),
                "%s is an integer id — a string (here %r) is an invalid type the save rejects even on a "
                "disabled skill. OMIT the key on a draft; supply a real integer id when you enable the skill "
                "(schema §6.1)." % (id_key, id_val))
        missing.append(id_key)
    elif not id_val:
        # None (omitted), 0, false — nothing dialable, so the pair is incomplete however the key looks.
        missing.append(id_key)
    ext_val = rule.get(ext_key)
    if isinstance(ext_val, str) and not ext_val.strip():
        if enabled:
            rep.err("empty-transfer-target", "%s.%s" % (where, ext_key),
                    "An empty string is worse than an absent key on a LIVE skill: it passes backend "
                    "validation and the runtime's usability check, gets advertised to the LLM as a working "
                    "transfer, then dials nothing — dead air, and the caller is gone. Omit the key until you "
                    "have the real value (schema §6.1).")
        else:
            # A switched-off draft never reaches a live call, so an omitted or blank extension is the
            # scaffold shape the user completes in the dashboard — treat it like an unfilled half.
            missing.append(ext_key)
    elif not ext_val:
        missing.append(ext_key)
    if missing:
        if enabled:
            rep.err("missing-transfer-id", where,
                    "destination \"%s\" requires BOTH %s and %s (missing or unusable: %s). The API requires "
                    "the pair, and nothing validates the values later — a half-set target fails only during a "
                    "live call. Keep the rule you authored (its condition, destination, and any id you already "
                    "have) and ship the skill `enabled: false` — a disabled draft rule may leave the target "
                    "blank for the user to complete in the dashboard. Only when there is no destination worth "
                    "scaffolding at all should `rules` be empty; don't discard real work (schema §6.1)."
                    % (dest, id_key, ext_key, ", ".join(missing)))
        else:
            rep.info("unfinished-transfer", where,
                     "Switched-off transfer draft: the %s destination is scaffolded but its target isn't "
                     "filled in (%s) — finish setting up the transfer to your team on this skill in the "
                     "dashboard (it shows \"Requires configuration\"), then switch it on "
                     "(referenced-resources.md#direct-transfers)."
                     % (dest, ", ".join(missing)))
    # A half-set pair is work someone still has to do, wherever the enabled toggle sits; a complete
    # pair is wiring done — listed only so the user double-checks values nothing else will.
    rep.reference("%s.%s" % (where, id_key), dest, pending=bool(missing),
                  what="Needs a real %s id AND extension from your company. Nothing validates them — a wrong "
                  "value fails only during a live call; where advanced transfer is enabled the AI resumes, "
                  "but on a cold fallback the caller is dropped.%s "
                  "(referenced-resources.md#direct-transfers)."
                  % (dest, " Prefer a ring group: more targets can answer before an attended transfer falls back."
                     if dest == "agent" else ""))


def _skill_enabled(skill, where, rep):
    """Read a present skill's `enabled` flag — a REQUIRED plain bool on every skill object the config
    carries. Without it the import fails (422 `expected required property enabled to be present`) and
    the API's own /validate endpoint does NOT catch it, so this check is the only gate. Absent is
    treated as disabled here, which is what a stored config missing the key does at runtime."""
    val = skill.get("enabled")
    if not isinstance(val, bool):
        rep.err("missing-enabled", "%s.enabled" % where,
                "Required plain bool on every skill object present in the config — a missing `enabled` is "
                "rejected on import (422) and the API's own /validate endpoint does not flag it. Emit true "
                "to switch the skill on, false to ship it switched-off for the user to finish in the "
                "dashboard (schema §6).")
        return False
    return val


def declared_skill_subkeys(fields):
    """Per-skill set of direct sub-keys fields.json declares (the registry is the single source of
    truth for the field set, so the allowlist is derived rather than duplicated here)."""
    subkeys = {}
    for rows in (fields.get("skills") or {}).values():
        for row in rows:
            match = SKILL_SUBKEY_RE.match(row.get("path", ""))
            if match:
                subkeys.setdefault(match.group("skill"), set()).add(match.group("key"))
    return subkeys


def _check_skill_subkeys(obj, where, allowed, rep):
    """The /validate endpoint rejects unknown keys recursively; the save silently drops them — so a typo'd
    sub-key vanishes on save (losing the field) unless caught here first."""
    if not allowed:
        return
    for key in obj:
        if key not in allowed:
            rep.err("unknown-field", "%s.%s" % (where, key),
                    "Not a documented field on this skill — the /validate endpoint (and this validator) "
                    "reject unknown keys, including nested ones; the save silently drops them. Allowed: %s "
                    "(schema §6)." % ", ".join(sorted(allowed)))


def validate_skills(cfg, rep, direction, fields=None):
    skills = cfg.get("skills")
    if skills is None:
        return
    if not isinstance(skills, dict):
        rep.err("bad-type", "skills", "Expected an object (schema §6).")
        return

    # A misspelled skill name is dangerous: the /validate endpoint rejects it, but the save silently DROPS
    # it, quietly shipping an agent without the capability. The validator flags it so the typo surfaces.
    for key in skills:
        if key not in KNOWN_SKILLS:
            rep.err("unknown-skill", "skills.%s" % key,
                    "Not a v2 skill — the /validate endpoint (and this validator) reject unknown keys, but "
                    "the save silently drops a typo like transferToHumans, shipping an agent without the "
                    "capability. Allowed: %s (schema §6)." % ", ".join(sorted(KNOWN_SKILLS)))

    subkeys = declared_skill_subkeys(fields or {})
    for name, obj in skills.items():
        allowed = subkeys.get(name)
        if isinstance(obj, dict):
            _check_skill_subkeys(obj, "skills.%s" % name, allowed, rep)
        elif isinstance(obj, list):
            for idx, element in enumerate(obj):
                if isinstance(element, dict):
                    _check_skill_subkeys(element, "skills.%s[%d]" % (name, idx), allowed, rep)

    # transferToHuman
    th = skills.get("transferToHuman")
    if th is not None and not isinstance(th, dict):
        rep.err("bad-type", "skills.transferToHuman", "Expected an object (schema §6.1).")
    if isinstance(th, dict):
        th_on = _skill_enabled(th, "skills.transferToHuman", rep)
        rules = th.get("rules")
        if "rules" not in th:
            # Structural: `rules` is required as soon as the skill object exists (an omitted key 422s),
            # and [] is legal only on a switched-off skill shipped for the user to finish.
            rep.err("missing-rules", "skills.transferToHuman.rules",
                    "Required whenever the transferToHuman object is present — an omitted `rules` key is "
                    "rejected on import (422). Send [] only for a skill you are shipping switched-off (schema §6.1).")
        elif not isinstance(rules, list):
            rep.err("bad-type", "skills.transferToHuman.rules", "Expected a list (schema §6.1).")
        elif not rules:
            if th_on:
                rep.warn("transfer-no-rules", "skills.transferToHuman.rules",
                         "transferToHuman is ENABLED but has no rules — an enabled transfer needs at least one "
                         "rule and the save is refused without it. `rules: []` is legal only while the skill is "
                         "switched off (schema §6.1).")
            else:
                rep.reference("skills.transferToHuman", "agent_or_group",
                              pending=True, what="Transfer shipped switched-off: pick the real agent or ring group on the skill in "
                              "the dashboard (it shows \"Requires configuration\"), then switch it on — or supply "
                              "the id + extension pair and the next config ships it wired "
                              "(referenced-resources.md#direct-transfers).")
        else:
            for idx, rule in enumerate(rules):
                loc = "skills.transferToHuman.rules[%d]" % idx
                if not isinstance(rule, dict):
                    rep.err("bad-type", loc, "Each rule must be an object.")
                    continue
                cond = rule.get("condition")
                if "condition" not in rule:
                    rep.err("missing-required", "%s.condition" % loc,
                            "Required on every rule the config carries — a rule without the key is rejected "
                            "on import (422) (schema §6.1).")
                elif not isinstance(cond, str) or not cond.strip():
                    # Same treatment as a scenario `when`: a blank or non-string condition is no trigger at
                    # all. Blocking on an enabled rule; on a switched-off one it is part of the unfinished
                    # skill the user completes in the dashboard.
                    rep.at("ERROR" if th_on else "INFO", "transfer-no-condition", "%s.condition" % loc,
                           "Must be a non-empty string — a blank condition gives the rule no trigger to watch "
                           "for. Write a specific, enumerable one (<= 120 chars) (behavioral §3.4).")
                elif len(cond) > 120:
                    rep.warn("transfer-vague-condition", loc,
                             "condition is long (%d chars, limit 120) — keep it a specific, enumerable "
                             "trigger (behavioral §3.4)." % len(cond))
                _check_transfer_destination(rule, loc, rep, th_on, direction)
        inc = th.get("includeProperties")
        if isinstance(inc, list):
            bad = [x for x in inc if x not in ("callerName", "summary")]
            if bad:
                rep.err("bad-enum", "skills.transferToHuman.includeProperties",
                        "Only \"callerName\" and \"summary\" are valid; got extra %s (schema §6.1)." % bad)
        cps = th.get("customProperties")
        if cps is not None:
            _check_properties(cps, "skills.transferToHuman.customProperties", rep,
                              "ERROR" if th_on else "INFO")

    # takeMessage
    tm = skills.get("takeMessage")
    if tm is not None and not isinstance(tm, dict):
        rep.err("bad-type", "skills.takeMessage", "Expected an object (schema §6.2).")
    if isinstance(tm, dict):
        if _skill_enabled(tm, "skills.takeMessage", rep) and direction == "outbound":
            rep.warn("takemessage-outbound", "skills.takeMessage",
                     "Do not enable takeMessage on an outbound agent — the agent initiated the call (behavioral §3.3).")

    # extractData
    ed = skills.get("extractData")
    if ed is not None and not isinstance(ed, dict):
        rep.err("bad-type", "skills.extractData", "Expected an object (schema §6.3).")
    if isinstance(ed, dict):
        ed_on = _skill_enabled(ed, "skills.extractData", rep)
        _check_properties(ed.get("properties"), "skills.extractData.properties", rep,
                          "ERROR" if ed_on else "INFO")

    # custom
    custom = skills.get("custom")
    if custom is not None and not isinstance(custom, list):
        rep.err("bad-type", "skills.custom",
                "Expected a list of {enabled, name, prompt} objects (schema §6.4).")
    if isinstance(custom, list):
        if len(custom) > 6:
            rep.warn("custom-too-many", "skills.custom",
                     "%d custom skills — more than the 6 that stay manageable; keep to the recommended "
                     "2-4, each a genuinely separate capability (behavioral §2.2)." % len(custom))
        for idx, c in enumerate(custom):
            loc = "skills.custom[%d]" % idx
            if not isinstance(c, dict):
                rep.err("bad-type", loc, "Each custom skill must be an object {enabled, name, prompt}.")
                continue
            _skill_enabled(c, loc, rep)
            for k in ("name", "prompt"):
                if c.get(k) in (None, ""):
                    rep.err("missing-required", "%s.%s" % (loc, k), "Required (schema §6.4).")
            prompt = c.get("prompt")
            if isinstance(prompt, str):
                words = len(prompt.split())
                if words and words < 50:
                    rep.warn("custom-too-small", loc,
                             "Custom skill is short (%d words) — trivial rules belong in goalPrompt (behavioral §2.2)." % words)
                elif words > 2000:
                    rep.warn("custom-too-large", loc,
                             "Custom skill is large (%d words) — split, or move facts to a knowledge base (behavioral §2.2)." % words)

    # answerQuestions
    aq = skills.get("answerQuestions")
    if aq is not None and not isinstance(aq, dict):
        rep.err("bad-type", "skills.answerQuestions", "Expected an object (schema §6.5).")
    if isinstance(aq, dict):
        aq_on = _skill_enabled(aq, "skills.answerQuestions", rep)
        action = aq.get("action")
        if action is not None and (not isinstance(action, str) or action not in ANSWER_ACTIONS):
            rep.err("bad-enum", "skills.answerQuestions.action",
                    "Must be one of %s (schema §6.5)." % sorted(ANSWER_ACTIONS))
        if action == "transferToHuman":
            tc = aq.get("transferConfig")
            if not isinstance(tc, dict):
                rep.at("ERROR" if aq_on else "INFO", "missing-required",
                       "skills.answerQuestions.transferConfig",
                       "Required when action == \"transferToHuman\" (schema §6.5).")
                rep.reference("skills.answerQuestions.transferConfig", "agent_or_group", pending=True,
                              what="Undecided transfer target: pick the agent or ring group in the dashboard "
                              "(referenced-resources.md#direct-transfers).")
            else:
                _check_transfer_destination(tc, "skills.answerQuestions.transferConfig", rep, aq_on, direction)
            if aq_on and not cfg.get("knowledgeBaseIds") and not skills.get("custom"):
                rep.warn("answer-autotransfer", "skills.answerQuestions.action",
                         "action \"transferToHuman\" without a KB or custom skills to answer from first causes "
                         "excessive transfers — prefer admitUncertainty / offerAlternative (behavioral §3.2).")

    # appointmentBooking
    ab = skills.get("appointmentBooking")
    if ab is not None and not isinstance(ab, dict):
        rep.err("bad-type", "skills.appointmentBooking", "Expected an object (schema §6.6).")
    if isinstance(ab, dict):
        ab_on = _skill_enabled(ab, "skills.appointmentBooking", rep)
        level = "ERROR" if ab_on else "INFO"
        for k in ("integrationId", "calendarId", "eventName"):
            if not ab.get(k):
                rep.at(level, "missing-required", "skills.appointmentBooking.%s" % k,
                       "Required when appointmentBooking is enabled — a switched-off skill missing it is "
                       "unfinished: connect the calendar in the dashboard, then switch it on (schema §6.6).")
        dm = ab.get("durationMinutes")
        if dm is None or not is_num(dm) or dm <= 0:
            rep.at(level, "bad-duration", "skills.appointmentBooking.durationMinutes",
                   "Must be a number > 0 (schema §6.6).")
        for k in ("integrationType", "availabilityToolId", "bookingToolId", "errorCode"):
            if k in ab:
                rep.warn("server-managed-field", "skills.appointmentBooking.%s" % k,
                         "Server-managed — do not author; strip before import (schema §6.6).")
        rep.reference("skills.appointmentBooking.integrationId", "calendarIntegration",
                      pending=not all(ab.get(k) for k in ("integrationId", "calendarId", "eventName")),
                      what="Connect a calendar integration (OAuth) and use its ID + a calendarId within it "
                      "(referenced-resources.md#appointment-booking).")


def validate_scenarios(cfg, rep):
    scenarios = cfg.get("scenarios")
    if scenarios is not None and not isinstance(scenarios, list):
        rep.err("bad-type", "scenarios", "Expected a list (schema §7.1).")
        return
    # An absent `scenarios` key is walked as an empty list rather than skipped: no scenarios at all means
    # no hangup scenario either, and end_call coverage is exactly what the tally below reports.
    n_hangup = 0
    for idx, s in enumerate(scenarios or []):
        loc = "scenarios[%d]" % idx
        if not isinstance(s, dict):
            rep.err("bad-type", loc, "Each scenario must be an object.")
            continue
        # `enabled` is a REQUIRED plain bool on every scenario. The API's /validate endpoint green-lights
        # a missing one (the absent key decodes to disabled, so it only demotes the finding to a warning)
        # and the save then 422s — this check is the only place that catches it.
        if not isinstance(s.get("enabled"), bool):
            rep.err("missing-enabled", "%s.enabled" % loc,
                    "Required plain bool on every scenario — a missing `enabled` is rejected on import "
                    "(422), the API's own /validate endpoint does not flag it, and a stored scenario "
                    "without it never fires (schema §7.1).")
        # triggerType (schema §7.1). EffectiveTriggerType parity: missing/empty/"custom" all mean "custom"
        # (requires `when`); "booking_confirmed" may omit `when` (the API auto-fills "the booking is
        # confirmed"). Any other value is rejected (422) — report bad-enum only, and skip the missing-`when`
        # check for it (no double report).
        trigger = s.get("triggerType")
        if trigger in (None, "", "custom"):
            effective = "custom"
        elif trigger == "booking_confirmed":
            effective = "booking_confirmed"
        else:
            effective = None
            rep.err("bad-enum", "%s.triggerType" % loc,
                    "Must be one of %s (schema §7.1)." % sorted(SCENARIO_TRIGGER_TYPES))
        when = s.get("when")
        if effective == "custom" and (not isinstance(when, str) or not when.strip()):
            rep.err("missing-required", "%s.when" % loc,
                    "Required unless triggerType == \"booking_confirmed\" (schema §7.1).")
        reply = s.get("reply")
        action = s.get("action")
        if reply in (None, "") and action not in ("hangup", "sendSms"):
            rep.warn("scenario-no-reply", "%s.reply" % loc,
                     "No reply text — the agent has nothing to say for this scenario (schema §7.1).")
        if isinstance(reply, str) and reply:
            _lint_reply(reply, "%s.reply" % loc, rep)
        if action is not None:
            if not isinstance(action, str) or action not in SCENARIO_ACTIONS:
                rep.err("bad-enum", "%s.action" % loc,
                        "Must be one of %s (schema §7.1)." % sorted(SCENARIO_ACTIONS))
            elif action == "hangup":
                # Only an explicitly enabled scenario grants end_call: a missing `enabled` decodes to
                # disabled, exactly like `false`.
                if s.get("enabled") is True:
                    n_hangup += 1
            elif action == "toolCall":
                if not s.get("toolReferenceId"):
                    rep.err("missing-tool-ref", "%s.toolReferenceId" % loc,
                            "Required when action == \"toolCall\" (schema §7.1).")
                rep.reference("%s.toolReferenceId" % loc, "customTool",
                              "Create the custom tool, copy its ID, and RE-ADD the toolCall action in the UI "
                              "after a cross-company paste (referenced-resources.md#custom-tools).")
            elif action == "sendSms":
                params = s.get("params")
                if not isinstance(params, dict) or not params.get("senderNumber") or not params.get("message"):
                    rep.err("missing-sms-params", "%s.params" % loc,
                            "action \"sendSms\" requires params.senderNumber and params.message (schema §7.1).")
                rep.reference("%s.params.senderNumber" % loc, "smsSenderNumber",
                              "Use a real company-owned E.164 sender and RE-ADD the sendSms action in the UI "
                              "after a cross-company paste (referenced-resources.md#send-sms).")
    if n_hangup == 0:
        rep.warn("no-hangup", "scenarios",
                 "No hangup scenario — the runtime then tells the agent it cannot end the call. Add at least one "
                 "scenario with action \"hangup\" for normal completion (+ silence, + voicemail if outbound) (behavioral §4.1).")


def validate_guardrails(cfg, rep):
    guardrails = cfg.get("guardrails")
    if guardrails is None:
        return
    if not isinstance(guardrails, list):
        rep.err("bad-type", "guardrails", "Expected a list (schema §7.2).")
        return
    if guardrails:
        # Accepted and stored by the config API, but INERT at runtime: the runtime model carries no
        # `enabled` field, so every stored guardrail decodes to disabled and is silently skipped — the
        # feature is not yet honored end-to-end. Steer authors toward an empty array; the shape checks
        # below still run so a populated one that slips through is at least structurally sound.
        rep.warn("guardrails-inert", "guardrails",
                 "guardrails are accepted and stored but do NOT take effect yet — the runtime has no "
                 "`enabled` field for them, so each one decodes to disabled and is silently skipped. Do not "
                 "emit guardrails; keep the array empty and put always-on safety rules in the goalPrompt "
                 "`## Guardrails` prose section instead (behavioral §2.1).")
    for idx, g in enumerate(guardrails):
        loc = "guardrails[%d]" % idx
        if not isinstance(g, dict):
            rep.err("bad-type", loc, "Each guardrail must be an object {enabled, when, reply}.")
            continue
        if not isinstance(g.get("enabled"), bool):
            rep.err("missing-enabled", "%s.enabled" % loc,
                    "Required plain bool on every guardrail — a missing `enabled` is rejected on import "
                    "(422) and a stored guardrail without it never fires (schema §7.2).")
        for k in ("when", "reply"):
            v = g.get(k)
            if not isinstance(v, str) or not v.strip():
                rep.err("missing-required", "%s.%s" % (loc, k), "Required (schema §7.2).")
        if isinstance(g.get("reply"), str) and g["reply"]:
            _lint_reply(g["reply"], "%s.reply" % loc, rep)


_REPLY_BAD_EXACT = {".", "nothing", "say nothing", "none"}


def _lint_reply(reply, where, rep):
    """Behavioral §4.2: reply must be the literal spoken sentence, not a meta-instruction."""
    stripped = reply.strip()
    low = stripped.lower()
    if low in _REPLY_BAD_EXACT:
        rep.warn("reply-meta", where,
                 "Reply %r is a placeholder/meta-instruction, not spoken text — it gets read aloud. Use a real "
                 "sentence or an empty string (behavioral §4.2)." % reply)
    if re.match(r'^\s*say\s*[:\"]', low):
        rep.warn("reply-meta", where,
                 "Reply looks like a meta-instruction (\"Say: ...\") — the quoted fragment is spoken verbatim "
                 "(behavioral §4.2). Write just the sentence to speak.")
    if re.search(r"\(\s*if\b.*\(\s*if\b", low) or re.search(r"\(\s*if\s+not\b", low):
        rep.warn("reply-conditional", where,
                 "Reply embeds branching conditional logic ((if X) … (if not) …) — parentheticals get read "
                 "aloud. Use one scenario per branch (behavioral §4.2).")


def behavioral_lints(cfg, rep, direction, provider):
    # maxCallDuration — a hard ceiling (call cut off when reached), not a conversation timer (§4.4)
    mcd = cfg.get("maxCallDuration")
    if is_num(mcd):
        if mcd > 120:
            rep.warn("maxcall-over-limit", "maxCallDuration",
                     "%s min is very high — there is no hard API cap, but keep maxCallDuration to 120 or "
                     "below (~20-30 min is typical); a call ceiling that high is a safety net nobody needs "
                     "(behavioral §4.4)." % mcd)
        if mcd <= 2:
            rep.warn("maxcall-tight", "maxCallDuration",
                     "%s min is a very tight hard cap — it will truncate legitimate calls. maxCallDuration is a "
                     "safety ceiling, not a length control; use generous headroom (behavioral §4.4)." % mcd)
        elif direction == "outbound" and mcd > 30:
            rep.warn("maxcall-outbound", "maxCallDuration",
                     "%s min is high for outbound — ~10-15 min headroom recommended (behavioral §4.4)." % mcd)
        elif direction == "inbound" and mcd > 60:
            rep.warn("maxcall-inbound", "maxCallDuration",
                     "%s min is high for inbound — ~20-30 min recommended (behavioral §4.4)." % mcd)

    # optimizeStreamingLatency == 4
    if cfg.get("optimizeStreamingLatency") == 4:
        rep.warn("latency-4", "optimizeStreamingLatency",
                 "Level 4 disables the TTS text normalizer (numbers/dates mispronounced). Use the baseline 2 (behavioral §7a-bis).")

    # temperature — 0.4-0.7 is the legitimate band for a deliberately conversational agent, so the warn
    # only fires above it (behavioral §7a-bis).
    temp = cfg.get("temperature")
    if is_num(temp) and temp > 0.7:
        rep.warn("temperature-high", "temperature",
                 "temperature %s is above the 0.4-0.7 conversational band; use 0.1-0.3 for structured/"
                 "professional agents (behavioral §7a-bis)." % temp)

    # greeting expectations
    greeting = cfg.get("greeting")
    if not greeting:
        if direction == "inbound":
            rep.warn("inbound-greeting", "greeting",
                     "Inbound agents should have a concrete greeting (else a generic server default is used) (behavioral §6).")
        elif direction == "outbound":
            rep.warn("outbound-greeting", "greeting",
                     "Outbound with an empty greeting opens with dead air — add an identifying greeting (behavioral §6).")

    # goalPrompt presence/size sanity (the 5-component coverage is for the LLM self-check, not lintable).
    # A soft target is up to ~250 words; length itself is not flagged. Only a genuinely empty or one-line
    # prompt is too thin to carry the five components at all.
    gp = cfg.get("goalPrompt")
    if isinstance(gp, str) and gp.strip() and len(gp.split()) < 10:
        rep.warn("goalprompt-thin", "goalPrompt",
                 "goalPrompt is a one-liner — too thin to cover identity, style, response guidelines, task "
                 "flow, and ending. Aim for a structured prompt (a soft target of up to ~250 words) "
                 "(behavioral §2.1).")


# ---------------------------------------------------------------------------
def report_glyphs(stream=None):
    """Glyphs for the human report, downgraded to ASCII when the console cannot carry them.

    Windows consoles default to cp1252/cp437, where an unencodable glyph makes print() raise
    UnicodeEncodeError and the whole report is lost. `errors="replace"` keeps the remaining non-ASCII in
    the messages (§, em dashes) printable; the ASCII set keeps the severity column readable rather than
    a row of "?". Streams with no encoding at all (StringIO under a redirect) need neither.
    """
    stream = sys.stdout if stream is None else stream
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is not None:
        try:
            reconfigure(errors="replace")
        except (ValueError, OSError):
            pass
    encoding = getattr(stream, "encoding", None)
    if not encoding:
        return GLYPHS
    try:
        "".join(GLYPHS.values()).encode(encoding)
    except (UnicodeEncodeError, LookupError):
        return GLYPHS_ASCII
    return GLYPHS


def print_human(rep, src_label):
    order = {"ERROR": 0, "WARN": 1, "INFO": 2}
    glyph = report_glyphs()
    bullet = glyph["bullet"]
    issues = sorted(rep.issues, key=lambda i: (order[i.level], i.where))
    print("Voice Agent v2 config validation — %s" % src_label)
    print("=" * 64)
    if not issues:
        print("No structural or behavioral issues found.")
    for i in issues:
        print("%s %-5s %-26s %s" % (glyph[i.level], i.level, i.where, i.msg))

    print("-" * 64)
    if rep.env_refs:
        print("Outbound number — reuse your agent's real value when you have one (never invent one):")
        for field_path, kind, what in rep.env_refs:
            print("  %s [%s] %s" % (bullet, kind, field_path))
            print("      %s" % what)
    save_refused = any(i.code in SAVE_REFUSED_CODES for i in rep.issues)
    save_blocked = any(i.code in SAVE_BLOCKING_CODES for i in rep.issues)
    pending = [r for r in rep.references if r[3]]
    supplied = [r for r in rep.references if not r[3]]
    if supplied:
        print("Already wired — confirm each one is real, active, and owned by the target company:")
        for field_path, kind, what, _ in supplied:
            print("  %s [%s] %s" % (bullet, kind, field_path))
            print("      %s" % what)
    if pending:
        print("Needs %d resource(s) you must create/select in your company:" % len(pending))
        for field_path, kind, what, _ in pending:
            print("  %s [%s] %s" % (bullet, kind, field_path))
            print("      %s" % what)
    elif not save_blocked:
        print("Nothing else to wire %s — reuses your existing setup; no new resources to create."
              % glyph["ok"])
    # Independent of any resource list: a blocking warning must always be said out loud.
    if save_refused:
        print("%s The warning above blocks the save — fix it before pasting (the message names the way out)."
              % glyph["WARN"])
    elif save_blocked:
        print("%s The warning above must be fixed before pasting — the config saves, but ships an agent "
              "that cannot end a call (the message names the way out)." % glyph["WARN"])

    print("-" * 64)
    print("Summary: %d error(s), %d warning(s)." % (rep.n_errors, rep.n_warnings))
    print("Reminder: save once to confirm it sticks. A 'Failed to update VoiceAgent' error means a referenced resource isn't provisioned in your company (deprecated voice, unowned sendSms number, custom tool missing its ElevenLabs ID, or a provider/language mismatch) — fix the reference; re-saving won't clear it.")
    if rep.n_errors:
        print("Result: ERRORS present — fix before importing (likely 400/422).")
    elif save_refused:
        print("Result: NOT save-ready — a warning above blocks the save; fix it first.")
    elif save_blocked:
        print("Result: NOT paste-ready — a blocking warning above; fix it first.")
    elif rep.n_warnings:
        print("Result: structurally OK — review warnings for behavioral quality.")
    else:
        print("Result: clean.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate a Voice Agent v2 (Expert Mode) config.")
    parser.add_argument("config", help="Path to the config JSON/JSONC, or - for stdin.")
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable JSON report.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if there are warnings too.")
    parser.add_argument("--fields", help="Path to fields.json (default: sibling of this script's parent).")
    args = parser.parse_args(argv)

    here = os.path.dirname(os.path.abspath(__file__))
    fields_path = args.fields or os.path.join(here, "..", "fields.json")

    try:
        raw = sys.stdin.read() if args.config == "-" else open(args.config, "r", encoding="utf-8").read()
    except OSError as e:
        print("Could not read config: %s" % e, file=sys.stderr)
        return 2

    try:
        cfg = parse_config(raw)
    except (json.JSONDecodeError, ValueError) as e:
        print("Could not parse config as JSON/JSONC: %s" % e, file=sys.stderr)
        return 2

    try:
        fields = load_fields(fields_path)
    except OSError as e:
        print("Could not read fields.json (%s): %s" % (fields_path, e), file=sys.stderr)
        return 2

    rep = Report()
    validate(cfg, fields, rep)

    if args.json:
        save_blocking = any(i.code in SAVE_BLOCKING_CODES for i in rep.issues)
        out = {
            "errors": rep.n_errors,
            "warnings": rep.n_warnings,
            "saveBlocking": save_blocking,
            "nothingElseToWire": not any(r[3] for r in rep.references) and not save_blocking,
            "issues": [i.as_dict() for i in rep.issues],
            "references": [{"field": f, "resourceKind": k, "howToWire": w, "pending": p}
                           for f, k, w, p in rep.references],
            "environment": [{"field": f, "resourceKind": k, "reuse": w} for f, k, w in rep.env_refs],
        }
        print(json.dumps(out, indent=2))
    else:
        label = "stdin" if args.config == "-" else os.path.basename(args.config)
        print_human(rep, label)

    if rep.n_errors:
        return 1
    # A save-blocking warning means the paste will be refused — automation reading only the exit code
    # must not treat that as a pass. Ordinary behavioral warnings stay non-blocking without --strict.
    if any(i.code in SAVE_BLOCKING_CODES for i in rep.issues):
        return 1
    if args.strict and rep.n_warnings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
