#!/usr/bin/env python3
"""Smoke tests for validate_config.py — the paste-ready gate.

Three halves:
  1. POSITIVE — every bundled examples/E*.jsonc must validate with zero errors, and only E2 (outbound
     behind Automatic with no failover) may carry a warning: its documented save-blocking one.
  2. NEGATIVE — the violations this validator exists to catch must each produce a specific ERROR
     (a `_requiredResources` block, an unambiguous placeholder ID, a legacy v1 field, a missing
     `enabled`, a half-set transfer target), AND a config that bakes in a *real* small-integer ID must
     NOT be flagged (regression guard: real group/agent IDs are small integers, so they are valid —
     not sentinels).
  3. CONTRACTS — the shapes the generator is supposed to emit must stay clean: Automatic with no
     failover inbound, a switched-off transfer skill, a complete direct transfer.

Stdlib only. Run: python3 scripts/test_validate.py   (exit 0 = all pass, 1 = a check failed)
"""
import contextlib
import copy
import io
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import validate_config as V  # noqa: E402

FIELDS = V.load_fields(os.path.join(HERE, "..", "fields.json"))

# A minimal, clean, valid inbound config (zero errors, zero warnings). Its number wiring is the clean shape
# both directions now need: Automatic paired with a real owned failover. Negative tests mutate a copy.
BASE = {
    "agentName": "Test Agent",
    "direction": "inbound",
    "defaultOutboundNumberId": 1,
    "failoverOutboundNumberId": 202,
    "language": "en",
    "maxCallDuration": 20,
    "temperature": 0.2,
    "voice": "cgSgspJ2msm6clMCkdW9",
    "optimizeStreamingLatency": 2,
    "stability": 0.5,
    "similarity": 0.75,
    "startSpeakingFirst": True,
    "greeting": "Hello, thanks for calling Acme. How can I help you today?",
    "goalPrompt": (
        "## Identity\nYou are a test receptionist for Acme.\n## Tone\nBe brief and warm; ask one "
        "question at a time and wait for the answer.\n## Task flow\nUnderstand why the caller is "
        "calling, answer from this prompt, and route them if needed.\n## Guardrails\nUse only this "
        "prompt; never guess. End the call cleanly once the caller is done."
    ),
    "scenarios": [
        {"enabled": True, "when": "the caller's request is handled and they have nothing else",
         "reply": "Thanks for calling Acme. Have a great day!", "action": "hangup"},
    ],
}

failures = []


def error_codes(cfg):
    rep = V.Report()
    V.validate(cfg, FIELDS, rep)
    return [i.code for i in rep.issues if i.level == "ERROR"]


def warn_codes(cfg):
    rep = V.Report()
    V.validate(cfg, FIELDS, rep)
    return [i.code for i in rep.issues if i.level == "WARN"]



def capture_human(rep):
    """The human report as a string, so a check can assert on what the user actually reads."""
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            V.print_human(rep, "test")
    except Exception as exc:                                # pragma: no cover - defensive
        failures.append("print_human raised %r" % exc)
        return ""
    return buf.getvalue()

# 1) POSITIVE: every bundled example validates clean. The one allowed warning is E2's — an outbound
# agent on Automatic with no failover, which is honest and documented in the example itself.
EXPECTED_EXAMPLE_WARNINGS = {"E2-outbound-confirmation-de.jsonc": ["outbound-automatic-no-failover"]}
for path in sorted(glob.glob(os.path.join(HERE, "..", "examples", "E*.jsonc"))):
    name = os.path.basename(path)
    cfg = V.parse_config(open(path, encoding="utf-8").read())
    codes = error_codes(cfg)
    if codes:
        failures.append("%s: expected 0 errors, got %s" % (name, codes))
    warns = warn_codes(cfg)
    expected = EXPECTED_EXAMPLE_WARNINGS.get(name, [])
    if warns != expected:
        failures.append("%s: expected warnings %s, got %s" % (name, expected, warns))

# 2) BASE itself is clean — no errors, no warnings.
if error_codes(copy.deepcopy(BASE)) or warn_codes(copy.deepcopy(BASE)):
    failures.append("BASE fixture should validate with 0 errors and 0 warnings, got %s / %s"
                    % (error_codes(copy.deepcopy(BASE)), warn_codes(copy.deepcopy(BASE))))


def expect_error(name, mutate, code):
    cfg = copy.deepcopy(BASE)
    mutate(cfg)
    codes = error_codes(cfg)
    if code not in codes:
        failures.append("%s: expected error %r, got %s" % (name, code, codes))


def expect_no_code(name, mutate, code):
    cfg = copy.deepcopy(BASE)
    mutate(cfg)
    codes = error_codes(cfg)
    if code in codes:
        failures.append("%s: should NOT raise %r, got %s" % (name, code, codes))


def expect_warn(name, mutate, code):
    cfg = copy.deepcopy(BASE)
    mutate(cfg)
    codes = warn_codes(cfg)
    if code not in codes:
        failures.append("%s: expected warning %r, got %s" % (name, code, codes))


def expect_no_warn(name, mutate, code):
    cfg = copy.deepcopy(BASE)
    mutate(cfg)
    codes = warn_codes(cfg)
    if code in codes:
        failures.append("%s: should NOT warn %r, got %s" % (name, code, codes))


def expect_clean(name, mutate):
    """No ERRORs and no WARNs — the bar for a shape the generator is expected to emit."""
    cfg = copy.deepcopy(BASE)
    mutate(cfg)
    errs, warns = error_codes(cfg), warn_codes(cfg)
    if errs or warns:
        failures.append("%s: expected clean, got errors %s / warnings %s" % (name, errs, warns))


def set_kbs(val):
    return lambda c: c.__setitem__("knowledgeBaseIds", val)


def transfer_rule(**fields):
    """A transferToHuman skill with one rule, for the destination/target checks."""
    rule = {"condition": "the caller asks for sales"}
    rule.update(fields)
    enabled = rule.pop("_enabled", True)
    return lambda c: c.__setitem__("skills", {"transferToHuman": {"enabled": enabled, "rules": [rule]}})


def set_transfer_group(group_id):
    return transfer_rule(destination="group", groupId=group_id, groupExtension="2001")


# 3) NEGATIVE: violations the gate must catch.
expect_error("_requiredResources block", lambda c: c.__setitem__("_requiredResources", [{"field": "x"}]), "unknown-field")
expect_error("legacy v1 field", lambda c: c.__setitem__("transferEnabled", True), "unknown-field")
expect_error("hex placeholder KB id", set_kbs(["000000000000000000000001"]), "sentinel-placeholder")
expect_error("REPLACE_WITH placeholder KB id", set_kbs(["REPLACE_WITH_KB_ID"]), "sentinel-placeholder")

# 4) REGRESSION GUARD (finding from PR review): a real small-integer ID is NOT a sentinel.
expect_no_code("real groupId 201", set_transfer_group(201), "sentinel-placeholder")
expect_no_code("real specific outbound number 101", lambda c: c.__setitem__("defaultOutboundNumberId", 101), "sentinel-placeholder")

# 5) OUTBOUND DEFAULT: a bare defaultOutboundNumberId: 2 is the old broken default — only 1 is magic,
# so 2 is a literal ID that almost never exists. WARN (not a backend "Random"), but NOT an error.
expect_warn("bare outbound default 2", lambda c: c.__setitem__("defaultOutboundNumberId", 2), "outbound-leftover-default")
_two = copy.deepcopy(BASE)
_two["defaultOutboundNumberId"] = 2
if error_codes(_two):
    failures.append("defaultOutboundNumberId: 2 should produce no ERRORs (only a WARN), got %s" % error_codes(_two))

# A save-blocking WARN must NOT read as "nothing else to wire" even with no references (the green ✅ bug).
_two_rep = V.Report()
V.validate(_two, FIELDS, _two_rep)
if not _two_rep.references and not any(i.code in V.SAVE_BLOCKING_CODES for i in _two_rep.issues):
    failures.append("defaultOutboundNumberId: 2 must not read 'nothing else to wire' — the save fails")

# 6) triggerType (schema §7.1): booking_confirmed + sendSms is the booking-confirmation recipe.
def add_booking_confirmed_sms(c):
    c["scenarios"] = c["scenarios"] + [
        {"enabled": True, "triggerType": "booking_confirmed", "action": "sendSms",
         "params": {"senderNumber": "+15555550100",
                    "message": "You're booked for {{appointment.event_name}} on {{appointment.start_pretty}}."}}]

# A booking_confirmed sendSms scenario (no `when`) is valid — produces no ERRORs.
_bc = copy.deepcopy(BASE)
add_booking_confirmed_sms(_bc)
if error_codes(_bc):
    failures.append("booking_confirmed sendSms scenario should validate with 0 errors, got %s" % error_codes(_bc))
# ...and specifically must NOT be flagged for a missing `when` (booking_confirmed may omit it).
expect_no_code("booking_confirmed omits when", add_booking_confirmed_sms, "missing-required")
# ...and must be WARNING-free re scenario-no-reply — a sendSms scenario's output is the SMS, not speech.
if "scenario-no-reply" in warn_codes(_bc):
    failures.append("booking_confirmed sendSms scenario should not raise scenario-no-reply, got %s" % warn_codes(_bc))

# An unknown triggerType value is rejected (422 at the API → bad-enum here).
expect_error("invalid triggerType", lambda c: c["scenarios"][0].__setitem__("triggerType", "on_hangup"), "bad-enum")

# triggerType "" == omitted == custom (EffectiveTriggerType parity): empty string is NOT a bad enum.
expect_no_code("empty triggerType is not bad-enum",
               lambda c: c["scenarios"][0].__setitem__("triggerType", ""), "bad-enum")
# ...but empty triggerType (custom) without `when` is still missing-required.
expect_error("empty triggerType without when",
             lambda c: c.__setitem__("scenarios", [{"enabled": True, "triggerType": "", "reply": "Bye!", "action": "hangup"}]),
             "missing-required")

# A custom scenario (default) without `when` is still an error.
def custom_without_when(c):
    c["scenarios"] = [{"enabled": True, "triggerType": "custom", "reply": "Thanks, goodbye!", "action": "hangup"}]
expect_error("custom triggerType without when", custom_without_when, "missing-required")

# ...and the same when triggerType is OMITTED entirely (default == custom) — the invariant that a bare
# scenario still requires `when`.
expect_error("omitted triggerType without when",
             lambda c: c.__setitem__("scenarios", [{"enabled": True, "reply": "Thanks, goodbye!", "action": "hangup"}]),
             "missing-required")

# An invalid triggerType WITHOUT `when` reports bad-enum ONLY — no double-report of missing-required.
def invalid_trigger_no_when(c):
    c["scenarios"] = [{"enabled": True, "triggerType": "on_hangup", "reply": "Bye!", "action": "hangup"}]
expect_error("invalid triggerType without when → bad-enum", invalid_trigger_no_when, "bad-enum")
expect_no_code("invalid triggerType without when → no missing-required", invalid_trigger_no_when, "missing-required")

# 7) A `when` that is whitespace-only or non-string is treated as missing (the API trims custom triggers;
# non-strings fail JSON decode). Matches the validator's isinstance+strip convention for required fields.
expect_error("custom when whitespace-only",
             lambda c: c.__setitem__("scenarios", [{"enabled": True, "triggerType": "custom", "when": "   ", "reply": "Bye!", "action": "hangup"}]),
             "missing-required")
expect_error("custom when non-string",
             lambda c: c.__setitem__("scenarios", [{"enabled": True, "triggerType": "custom", "when": 123, "reply": "Bye!", "action": "hangup"}]),
             "missing-required")

# Guardrails have the identical gap: whitespace-only / non-string when|reply is missing.
expect_error("guardrail when whitespace-only",
             lambda c: c.__setitem__("guardrails", [{"enabled": True, "when": "   ", "reply": "Let's keep it respectful."}]),
             "missing-required")
expect_error("guardrail reply whitespace-only",
             lambda c: c.__setitem__("guardrails", [{"enabled": True, "when": "the caller is abusive", "reply": "   "}]),
             "missing-required")
# ...but a guardrail with real strings raises no structural error (no false positive).
expect_no_code("well-formed guardrail raises no structural error",
               lambda c: c.__setitem__("guardrails", [{"enabled": True, "when": "the caller is abusive", "reply": "Let's keep it respectful, please."}]),
               "missing-required")

# Guardrails are accepted but INERT at runtime (no runtime `enabled` field), so a POPULATED array is
# steered toward empty with a non-blocking warning; an empty array is the desired shape and is not flagged.
expect_warn("populated guardrails are flagged inert",
            lambda c: c.__setitem__("guardrails", [{"enabled": True, "when": "the caller is abusive", "reply": "Let's keep it respectful."}]),
            "guardrails-inert")
expect_no_warn("an empty guardrails array is not flagged",
               lambda c: c.__setitem__("guardrails", []), "guardrails-inert")
if "guardrails-inert" in V.SAVE_BLOCKING_CODES:
    failures.append("guardrails-inert must stay non-blocking — a populated guardrails array still saves")

# 8) OUTBOUND NUMBER: Automatic (1) requires a real owned failover in BOTH directions (schema §3.2).
# BASE is inbound Automatic WITH a real failover — the clean shape (check 2). Removing the failover from an
# inbound agent now fails the gate too (no inbound carve-out).
expect_warn("inbound Automatic without failover", lambda c: c.pop("failoverOutboundNumberId", None),
            "outbound-automatic-no-failover")


def specific_number_no_failover(c):
    """A real non-1 defaultOutboundNumberId needs no failover key — omitting it is clean."""
    c["defaultOutboundNumberId"] = 101
    c.pop("failoverOutboundNumberId", None)


expect_clean("inbound specific number, no failover needed", specific_number_no_failover)
expect_clean("inbound specific number + failover", lambda c: c.update({"defaultOutboundNumberId": 101,
                                                                       "failoverOutboundNumberId": 202}))


def outbound(c):
    """Turn BASE into a minimal outbound agent on Automatic WITHOUT a failover — the save-blocking shape."""
    c["direction"] = "outbound"
    c["maxCallDuration"] = 10
    c.pop("failoverOutboundNumberId", None)


expect_warn("outbound Automatic without failover", outbound, "outbound-automatic-no-failover")
_ob = copy.deepcopy(BASE)
outbound(_ob)
if error_codes(_ob):
    failures.append("outbound Automatic without failover should produce no ERRORs, got %s" % error_codes(_ob))
_ob_rep = V.Report()
V.validate(_ob, FIELDS, _ob_rep)
if not any(i.code in V.SAVE_BLOCKING_CODES for i in _ob_rep.issues):
    failures.append("outbound Automatic without failover must not read 'nothing else to wire'")


def outbound_with_failover(c):
    outbound(c)
    c["failoverOutboundNumberId"] = 202


expect_clean("outbound Automatic with a real failover", outbound_with_failover)

# An explicit null is never right: it is unsupported and means the same as an absent key on import.
expect_error("null failover", lambda c: c.__setitem__("failoverOutboundNumberId", None), "null-failover")

# 9) `enabled` is required on every scenario, guardrail and present skill object (schema §6/§7).
expect_error("scenario without enabled",
             lambda c: c["scenarios"][0].pop("enabled"), "missing-enabled")
expect_error("guardrail without enabled",
             lambda c: c.__setitem__("guardrails", [{"when": "the caller is abusive", "reply": "Let's keep it civil."}]),
             "missing-enabled")
expect_error("skill without enabled",
             lambda c: c.__setitem__("skills", {"takeMessage": {"prompt": "Take a name and number."}}),
             "missing-enabled")
expect_error("custom skill without enabled",
             lambda c: c.__setitem__("skills", {"custom": [{"name": "verify", "prompt": "Verify the caller."}]}),
             "missing-enabled")
# A non-bool `enabled` is the same failure (the platform wants a plain bool).
expect_error("scenario enabled as string",
             lambda c: c["scenarios"][0].__setitem__("enabled", "true"), "missing-enabled")

# 10) TRANSFERS: a direct destination needs BOTH halves of its pair; an unfinished skill ships off.
expect_clean("direct group transfer with id + extension",
             transfer_rule(destination="group", groupId=456, groupExtension="2001"))
expect_error("agent transfer with the id only",
             transfer_rule(destination="agent", agentId=123), "missing-transfer-id")
expect_error("agent transfer with the extension only",
             transfer_rule(destination="agent", agentExtension="1001"), "missing-transfer-id")
# An empty string on a LIVE (enabled) transfer is worse than an absent key — it is advertised to the LLM,
# then dials nothing — so it stays a hard error there.
expect_error("empty extension on an enabled transfer",
             transfer_rule(destination="agent", agentId=123, agentExtension=""), "empty-transfer-target")
# ...but a switched-off draft never reaches a live call, so a blank target is the scaffold shape the user
# completes in the dashboard: no empty-transfer-target error, just an unfinished-transfer INFO.
expect_no_code("empty extension on a switched-off transfer is a draft, not an error",
               transfer_rule(destination="agent", agentId=123, agentExtension="", _enabled=False),
               "empty-transfer-target")
# The switched-off shape the generator emits when it has no real target.
expect_clean("switched-off transfer with rules: []",
             lambda c: c.__setitem__("skills", {"transferToHuman": {"enabled": False, "rules": []}}))
# ...and it must still read as one thing left to wire, not a green "nothing else to wire".
_off = copy.deepcopy(BASE)
_off["skills"] = {"transferToHuman": {"enabled": False, "rules": []}}
_off_rep = V.Report()
V.validate(_off, FIELDS, _off_rep)
if not _off_rep.references:
    failures.append("a switched-off transfer skill must be reported as something to finish in the dashboard")
# A switched-off rule whose target isn't decided yet is legal (destination "" / absent target fields).
expect_clean("switched-off rule with an undecided destination",
             transfer_rule(destination="", _enabled=False))
expect_clean("switched-off rule missing its target",
             transfer_rule(destination="group", _enabled=False))
# A FILLED-but-partial draft is legal too: a switched-off group rule that HAS its groupId but omits the
# extension is a valid draft, not an error — the shape the generator keeps rather than collapsing to
# `rules: []`, reported as unfinished-transfer INFO.
expect_clean("switched-off group rule with id but no extension",
             transfer_rule(destination="group", groupId=88337, _enabled=False))
_draft = copy.deepcopy(BASE)
transfer_rule(destination="group", groupId=88337, _enabled=False)(_draft)
_draft_rep = V.Report()
V.validate(_draft, FIELDS, _draft_rep)
if not any(i.code == "unfinished-transfer" for i in _draft_rep.issues):
    failures.append("a switched-off group rule with an id but no extension must report unfinished-transfer INFO")
# The default transfer scaffold: a switched-off group rule with the id/extension keys OMITTED for the user
# to complete in the dashboard. It must NOT hard-error — no error at all — and read as unfinished-transfer
# INFO plus pending wiring.
expect_clean("switched-off group rule with the id/extension omitted",
             transfer_rule(destination="group", _enabled=False))
_scaffold = copy.deepcopy(BASE)
transfer_rule(destination="group", _enabled=False)(_scaffold)
_scaffold_rep = V.Report()
V.validate(_scaffold, FIELDS, _scaffold_rep)
if any(i.code == "empty-transfer-target" for i in _scaffold_rep.issues):
    failures.append("a switched-off group draft with omitted target must not raise empty-transfer-target")
if not any(i.code == "unfinished-transfer" for i in _scaffold_rep.issues):
    failures.append("a switched-off group draft with omitted target must report unfinished-transfer INFO")
if not any(r[3] for r in _scaffold_rep.references):
    failures.append("an omitted-target group draft must be reported as pending wiring")
# groupId/agentId are INTEGERS: blanking one to "" is an INVALID_TYPE the save rejects even on a disabled
# skill — a draft OMITS the key, never blanks it. So "" is an error whether the skill is on or off.
expect_error("switched-off group rule with groupId blanked to \"\"",
             transfer_rule(destination="group", groupId="", groupExtension="", _enabled=False),
             "empty-transfer-id")
expect_error("enabled group rule with groupId blanked to \"\"",
             transfer_rule(destination="group", groupId="", groupExtension="2001"), "empty-transfer-id")
# `rules: []` is legal ONLY on a switched-off skill; an ENABLED transferToHuman needs >= 1 rule, and the
# empty-rules warning is save-refusing there.
expect_warn("enabled transfer with empty rules",
            lambda c: c.__setitem__("skills", {"transferToHuman": {"enabled": True, "rules": []}}),
            "transfer-no-rules")
if "transfer-no-rules" not in V.SAVE_REFUSED_CODES:
    failures.append("transfer-no-rules must be save-refusing — an enabled transfer needs >= 1 rule")
_enabled_no_rules = copy.deepcopy(BASE)
_enabled_no_rules["skills"] = {"transferToHuman": {"enabled": True, "rules": []}}
_enr_rep = V.Report()
V.validate(_enabled_no_rules, FIELDS, _enr_rep)
if not any(i.code in V.SAVE_BLOCKING_CODES for i in _enr_rep.issues):
    failures.append("an enabled transfer with empty rules must be save-blocking")

# Structure: `rules` is required as soon as the skill object exists; each rule needs condition + destination.
expect_error("transfer skill without the rules key",
             lambda c: c.__setitem__("skills", {"transferToHuman": {"enabled": False}}), "missing-rules")
expect_error("transfer rule without a destination",
             lambda c: c.__setitem__("skills", {"transferToHuman": {"enabled": True, "rules": [
                 {"condition": "the caller asks for sales"}]}}),
             "missing-required")
expect_error("transfer rule without a condition",
             lambda c: c.__setitem__("skills", {"transferToHuman": {"enabled": True, "rules": [
                 {"destination": "group", "groupId": 456, "groupExtension": "2001"}]}}),
             "missing-required")
# call_flow stays valid — it is the explicit-request path, reported as an environment note only.
expect_clean("call_flow destination", transfer_rule(destination="call_flow"))

# 11) An UNSET destination is only legal while the skill is off (the API's disabled-unit demotion): an
# enabled rule with nowhere to go must not read clean.
expect_error("enabled rule with an unset destination",
             transfer_rule(destination=""), "missing-required")
expect_error("enabled rule with a whitespace destination",
             transfer_rule(destination="  "), "missing-required")
expect_clean("switched-off rule with a whitespace destination",
             transfer_rule(destination="  ", _enabled=False))

# A falsy target value is not a target: 0 / false dial nothing, so the pair is still incomplete.
expect_error("agent transfer with agentId 0",
             transfer_rule(destination="agent", agentId=0, agentExtension="1001"), "missing-transfer-id")
expect_error("group transfer with groupExtension false",
             transfer_rule(destination="group", groupId=456, groupExtension=False), "missing-transfer-id")

# A rule `condition` gets the same isinstance+strip treatment as a scenario `when`.
expect_error("enabled rule with a whitespace condition",
             transfer_rule(condition="   ", destination="group", groupId=456, groupExtension="2001"),
             "transfer-no-condition")
expect_error("enabled rule with a non-string condition",
             transfer_rule(condition=42, destination="group", groupId=456, groupExtension="2001"),
             "transfer-no-condition")
expect_no_code("switched-off rule with a whitespace condition",
               transfer_rule(condition="   ", destination="", _enabled=False), "transfer-no-condition")

# 12) end_call coverage: only an explicitly enabled hangup scenario grants it (absent == disabled).
expect_warn("switched-off hangup scenario leaves no way to end the call",
            lambda c: c["scenarios"][0].__setitem__("enabled", False), "no-hangup")
_no_hangup = copy.deepcopy(BASE)
_no_hangup["scenarios"][0].pop("enabled")
if "no-hangup" not in warn_codes(_no_hangup):
    failures.append("a hangup scenario with no `enabled` must not count as end_call coverage (absent == disabled)")

# 13) A save-blocking warning must be reported even when the config also needs a resource — and must not
# be summarised as a mere behavioural warning.
_blocked_with_ref = copy.deepcopy(BASE)
outbound(_blocked_with_ref)
_blocked_with_ref["knowledgeBaseIds"] = ["66aa11bb22cc33dd44ee55ff"]
_bwr_rep = V.Report()
V.validate(_blocked_with_ref, FIELDS, _bwr_rep)
if not _bwr_rep.references:
    failures.append("outbound-no-failover + a KB should still list the KB as a resource")
if not any(i.code in V.SAVE_BLOCKING_CODES for i in _bwr_rep.issues):
    failures.append("outbound-no-failover + a KB must keep nothingElseToWire false")
_out = capture_human(_bwr_rep)
if "blocks the save" not in _out:
    failures.append("the save-blocking notice must print even when resources are listed")
if "review warnings for behavioral quality" in _out:
    failures.append("a save-blocking warning must not be summarised as a behavioural warning")

# 14) Supplied ids are wiring already done: they are listed for confirmation, but they never leave the
# config "not ready". Only a target nobody has picked yet is outstanding work.
_wired = copy.deepcopy(BASE)
_wired["knowledgeBaseIds"] = ["66aa11bb22cc33dd44ee55ff"]
_wired["skills"] = {"transferToHuman": {"enabled": True, "rules": [{
    "condition": "the caller wants to discuss an urgent issue with a specialist",
    "destination": "group",
    "groupId": 456,
    "groupExtension": "901",
}]}}
_wired_rep = V.Report()
V.validate(_wired, FIELDS, _wired_rep)
if any(r[3] for r in _wired_rep.references):
    failures.append("a supplied group id + KB id must not be reported as pending wiring")
if len(_wired_rep.references) != 2:
    failures.append("a supplied group id and KB id should both still be listed for confirmation")
_wired_out = capture_human(_wired_rep)
if "Already wired" not in _wired_out:
    failures.append("supplied references must print under the confirm-these heading")
if "you must create/select" in _wired_out:
    failures.append("a fully wired config must not claim resources still need creating")
if "Nothing else to wire" not in _wired_out:
    failures.append("a fully wired config must read as ready")

# A switched-off transfer has no target at all — that IS outstanding work.
_pending_rep = V.Report()
V.validate(_off, FIELDS, _pending_rep)
if not any(r[3] for r in _pending_rep.references):
    failures.append("a switched-off transfer with no rules must be reported as pending wiring")
_pending_out = capture_human(_pending_rep)
if "you must create/select" not in _pending_out:
    failures.append("pending wiring must print under the create/select heading")
if "Nothing else to wire" in _pending_out:
    failures.append("a config with pending wiring must not read as ready")

# 15) elevenLabsSettings sub-fields have documented shapes. Nothing downstream type-checks them, so the
# checker is the only thing standing between a plausible wrong shape and the API.
def els(**settings):
    return lambda c: c.__setitem__("elevenLabsSettings", settings)

expect_error("vad as an object instead of a flag", els(vad={"background_voice_detection": True}), "bad-type")
expect_error("speculativeTurn as a string", els(speculativeTurn="yes"), "bad-type")
expect_error("asrKeywords as a bare string", els(asrKeywords="Acme"), "bad-type")
expect_error("asrKeywords holding a blank entry", els(asrKeywords=["Acme", "  "]), "bad-type")
# An undocumented sub-field is flagged unknown-field: the /validate endpoint (and this validator) reject
# unknown keys recursively, while the save silently drops them (UNKNOWN_FIELD). `background_voice_detection`
# is exactly this case: ElevenLabs' nested shape is built server-side from the `vad` flag, never input.
expect_error("an undocumented elevenLabsSettings field", els(backgroundVoiceDetection=True), "unknown-field")
expect_clean("the documented elevenLabsSettings shapes",
             els(speculativeTurn=True, turnEagerness="patient", turnModel="turn_v3", vad=True,
                 asrKeywords=["Acme", "boiler"],
                 interruptionIgnoreTerms=["one moment"], interruptionIgnoreTermLanguages=["en"],
                 backgroundSound={"preset": "office", "volume": 0.3, "crossfadeLoop": True}))

# 16) A wrong-shaped enum value must report, not crash — set membership on an unhashable value throws.
expect_error("turnEagerness as a list", els(turnEagerness=["patient"]), "bad-type")
expect_error("turnModel as an object", els(turnModel={"v": 3}), "bad-type")
expect_error("turnEagerness bad value still caught", els(turnEagerness="impatient"), "bad-enum")

# 16a) The added elevenLabsSettings sub-fields: two ignore-term lists and a nested backgroundSound object.
expect_error("interruptionIgnoreTerms as a bare string", els(interruptionIgnoreTerms="hi"), "bad-type")
expect_error("backgroundSound with an unknown preset", els(backgroundSound={"preset": "disco"}), "bad-enum")
# A backgroundSound with no preset AND an out-of-range volume must report BOTH, not stop at the first.
expect_error("backgroundSound missing its required preset", els(backgroundSound={"volume": 2}), "missing-required")
expect_error("backgroundSound volume out of range", els(backgroundSound={"volume": 2}), "out-of-range")
expect_error("backgroundSound crossfadeLoop as a string",
             els(backgroundSound={"preset": "office", "crossfadeLoop": "yes"}), "bad-type")
expect_error("backgroundSound preset wrong type", els(backgroundSound={"preset": 5}), "bad-type")
expect_error("backgroundSound volume wrong type",
             els(backgroundSound={"preset": "office", "volume": "loud"}), "bad-type")
# Unknown-key handling is recursive: /validate rejects an unknown NESTED key while the save drops it, so the
# validator flags it either way.
expect_error("backgroundSound with an unknown nested key",
             els(backgroundSound={"preset": "office", "fade": True}), "unknown-field")

# 16d) interruptionIgnoreTerms and its languages list are a pair: a terms list without languages warns
# (the half-configured set does nothing at runtime), and setting both is clean.
expect_warn("interruption terms without languages",
            els(interruptionIgnoreTerms=["one moment"]), "interruption-terms-no-languages")
expect_clean("interruption terms with languages",
             els(interruptionIgnoreTerms=["one moment"], interruptionIgnoreTermLanguages=["en"]))

# 16b) Same crash class on the transfer side: an unhashable destination must report, not TypeError.
expect_error("destination as a list", transfer_rule(destination=["agent"]), "bad-type")
expect_error("destination as an object", transfer_rule(destination={"type": "agent"}), "bad-type")
expect_error("destination as a number", transfer_rule(destination=2), "bad-type")

# 16c) ...and on every other enum read straight from config: unhashable values report, never crash.
expect_error("extractData property type as a list",
             lambda c: c.__setitem__("skills", {"extractData": {"enabled": True, "properties": [
                 {"name": "x", "type": ["STRING"], "description": "d"}]}}), "bad-enum")
expect_error("answerQuestions action as an object",
             lambda c: c.__setitem__("skills", {"answerQuestions": {"enabled": True,
                 "action": {"a": 1}}}), "bad-enum")
expect_error("scenario action as a list",
             lambda c: c["scenarios"].append({"enabled": True, "when": "the caller asks for a person",
                 "reply": "One moment.", "action": ["hangup"]}), "bad-enum")

# 17) call_flow is inbound-only: an outbound agent has no flow to return to.
_ob_cf = copy.deepcopy(BASE)
outbound(_ob_cf)
_ob_cf["failoverOutboundNumberId"] = 202
_ob_cf["skills"] = {"transferToHuman": {"enabled": True, "rules": [
    {"condition": "the contact asks for a person", "destination": "call_flow"}]}}
_ob_cf_rep = V.Report()
V.validate(_ob_cf, FIELDS, _ob_cf_rep)
if "call-flow-outbound" not in [i.code for i in _ob_cf_rep.issues if i.level == "WARN"]:
    failures.append("outbound + call_flow must warn (inbound-only destination)")
_in_cf = copy.deepcopy(BASE)
_in_cf["skills"] = {"transferToHuman": {"enabled": True, "rules": [
    {"condition": "the caller asks for a person", "destination": "call_flow"}]}}
_in_cf_rep = V.Report()
V.validate(_in_cf, FIELDS, _in_cf_rep)
if any(i.code == "call-flow-outbound" for i in _in_cf_rep.issues):
    failures.append("inbound + call_flow must not carry the outbound warning")

# 18) An incomplete target is outstanding work whatever the enabled toggle says — only a complete
# pair counts as wiring done.
_half_off = copy.deepcopy(BASE)
_half_off["skills"] = {"transferToHuman": {"enabled": False, "rules": [
    {"condition": "the caller asks for sales", "destination": "group", "groupId": 456}]}}
_half_off_rep = V.Report()
V.validate(_half_off, FIELDS, _half_off_rep)
if not any(r[3] for r in _half_off_rep.references):
    failures.append("a switched-off rule with half a target must be pending wiring")
_unset_off = copy.deepcopy(BASE)
_unset_off["skills"] = {"transferToHuman": {"enabled": False, "rules": [
    {"condition": "the caller asks for sales", "destination": ""}]}}
_unset_off_rep = V.Report()
V.validate(_unset_off, FIELDS, _unset_off_rep)
if not any(r[3] for r in _unset_off_rep.references):
    failures.append("a switched-off rule with an unset destination must be pending wiring")

# 18c) tone / verbosity identity presets (schema §11).
expect_clean("verbosity concise", lambda c: c.__setitem__("verbosity", "concise"))
expect_error("verbosity unknown value", lambda c: c.__setitem__("verbosity", "verbose"), "bad-enum")
expect_clean("verbosity empty string is unset", lambda c: c.__setitem__("verbosity", ""))
expect_error("verbosity wrong type (list)", lambda c: c.__setitem__("verbosity", ["concise"]), "bad-type")
expect_clean("tone allowlist values", lambda c: c.__setitem__("tone", ["friendly", "direct"]))
expect_error("tone free-text value", lambda c: c.__setitem__("tone", ["warm"]), "bad-enum")
expect_error("tone as a scalar string", lambda c: c.__setitem__("tone", "friendly"), "bad-type")

# A mixed tone list flags only the bad element, pinned to its index: bad-enum at tone[1], not tone[0].
_mixed_tone = copy.deepcopy(BASE)
_mixed_tone["tone"] = ["friendly", "warm"]
_mixed_rep = V.Report()
V.validate(_mixed_tone, FIELDS, _mixed_rep)
if not any(i.level == "ERROR" and i.code == "bad-enum" and i.where == "tone[1]" for i in _mixed_rep.issues):
    failures.append("mixed tone list must flag bad-enum at tone[1], got %s"
                    % [(i.code, i.where) for i in _mixed_rep.issues if i.level == "ERROR"])

# 18d) Three or more distinct labels is an advisory, not a blocker: the save takes them, but only one-
# and two-label combinations have been validated (schema §11).
expect_no_warn("two tone labels stay clean",
               lambda c: c.__setitem__("tone", ["professional", "calm"]), "tone-many-labels")
expect_warn("three tone labels draw the advisory",
            lambda c: c.__setitem__("tone", ["professional", "calm", "friendly"]), "tone-many-labels")
expect_no_code("three tone labels are not an error",
               lambda c: c.__setitem__("tone", ["professional", "calm", "friendly"]), "bad-enum")
expect_no_warn("a repeated label is deduped before counting",
               lambda c: c.__setitem__("tone", ["professional", "calm", "calm"]), "tone-many-labels")
if "tone-many-labels" in V.SAVE_BLOCKING_CODES:
    failures.append("tone-many-labels must stay non-blocking — the save accepts a wider blend")

# null / [] / "" all mean unset (the BE self-heals to its defaults), so they validate clean.
expect_clean("tone null is unset", lambda c: c.__setitem__("tone", None))
expect_clean("tone empty list is unset", lambda c: c.__setitem__("tone", []))
expect_clean("verbosity null is unset", lambda c: c.__setitem__("verbosity", None))

# 19) A misspelled skill name is not silently dropped — the platform hard-rejects unknown keys, so a
# typo'd skill ships an agent without the capability AND fails the save.
expect_error("typo'd skill name",
             lambda c: c.__setitem__("skills", {"transferToHumans": {"enabled": False, "rules": []}}),
             "unknown-skill")
expect_error("snake_case skill name",
             lambda c: c.__setitem__("skills", {"take_message": {"enabled": True, "prompt": "Take a name."}}),
             "unknown-skill")
expect_no_code("correctly spelled skill name",
               lambda c: c.__setitem__("skills", {"takeMessage": {"enabled": True, "prompt": "Take a name and number."}}),
               "unknown-skill")

# 19a) Unknown-key rejection is recursive, so a typo'd SUB-key inside a skill fails the save the same
# way a typo'd skill name does. The allowlist is derived from fields.json, not duplicated in the checker.
expect_error("unknown takeMessage sub-key",
             lambda c: c.__setitem__("skills", {"takeMessage": {"enabled": True, "prompt": "Take a name.",
                                                                "bogusSubKey": True}}),
             "unknown-field")
expect_error("unknown custom-skill sub-key",
             lambda c: c.__setitem__("skills", {"custom": [{"enabled": True, "name": "verify",
                                                            "prompt": "verify " * 60, "bogus": 1}]}),
             "unknown-field")
expect_no_code("documented skill sub-keys stay clean",
               lambda c: c.__setitem__("skills", {"takeMessage": {"enabled": True,
                                                                  "prompt": "Take a name and number."}}),
               "unknown-field")
expect_no_code("appointmentBooking's server-managed keys are documented, not unknown",
               lambda c: c.__setitem__("skills", {"appointmentBooking": {
                   "enabled": False, "integrationId": "", "calendarId": "", "eventName": "Fitting",
                   "durationMinutes": 30, "integrationType": "google_calendar"}}),
               "unknown-field")

# 20) A section sent with the wrong JSON type must report, not be skipped by an isinstance guard.
expect_error("skills as a list", lambda c: c.__setitem__("skills", []), "bad-type")
expect_error("transferToHuman as a list",
             lambda c: c.__setitem__("skills", {"transferToHuman": []}), "bad-type")
expect_error("takeMessage as a string",
             lambda c: c.__setitem__("skills", {"takeMessage": "take a message"}), "bad-type")
expect_error("extractData as a list",
             lambda c: c.__setitem__("skills", {"extractData": []}), "bad-type")
expect_error("answerQuestions as a string",
             lambda c: c.__setitem__("skills", {"answerQuestions": "admitUncertainty"}), "bad-type")
expect_error("appointmentBooking as a list",
             lambda c: c.__setitem__("skills", {"appointmentBooking": []}), "bad-type")
expect_error("custom as an object",
             lambda c: c.__setitem__("skills", {"custom": {"name": "verify"}}), "bad-type")
expect_error("scenarios as an object", lambda c: c.__setitem__("scenarios", {"enabled": True}), "bad-type")
expect_error("guardrails as an object", lambda c: c.__setitem__("guardrails", {"enabled": True}), "bad-type")
expect_error("elevenLabsSettings as a list", lambda c: c.__setitem__("elevenLabsSettings", []), "bad-type")

# 21) Scalar types the enum/range loops cannot reach: a JSON string where a number belongs passes the
# required-field check and skips every range check, which only runs on values that are already numbers.
expect_error("maxCallDuration as a string", lambda c: c.__setitem__("maxCallDuration", "20"), "bad-type")
expect_error("dialTime as a string", lambda c: c.__setitem__("dialTime", "20"), "bad-type")
expect_error("agentName as a number", lambda c: c.__setitem__("agentName", 123), "bad-type")
expect_error("secondaryLanguages holding a number",
             lambda c: c.update({"secondaryLanguages": [123], "providerOverride": "elevenlabs"}), "bad-type")
expect_error("secondaryLanguages as a bare string",
             lambda c: c.update({"secondaryLanguages": "de", "providerOverride": "elevenlabs"}), "bad-type")
expect_error("knowledgeBaseIds holding a number", set_kbs([123]), "bad-type")
expect_error("knowledgeBaseIds as a bare string", set_kbs("66aa11bb22cc33dd44ee55ff"), "bad-type")
expect_clean("real secondaryLanguages with the ElevenLabs pin",
             lambda c: c.update({"secondaryLanguages": ["de", "fr"], "providerOverride": "elevenlabs"}))
expect_no_code("real knowledgeBaseIds", set_kbs(["66aa11bb22cc33dd44ee55ff"]), "bad-type")

# 22) An unknown language code is the validator's list trailing the platform's, not proof of an invalid
# config: WARN, never ERROR (the authoritative set is validated on save). Same for a secondary code.
expect_warn("unknown primary language", lambda c: c.__setitem__("language", "af"), "unknown-language")
expect_no_code("unknown primary language is not an error",
               lambda c: c.__setitem__("language", "af"), "unknown-language")
# A SECONDARY code goes through the same acceptance helper as the primary one, so a plain two-letter
# code ElevenLabs takes (af, ca, th, …) is not second-guessed just because the documented subset omits it.
expect_no_warn("plain secondary language is accepted",
               lambda c: c.update({"secondaryLanguages": ["af"], "providerOverride": "elevenlabs"}),
               "bad-secondary-language")
# A non-plain secondary code keeps the hedged warning — the platform owns the authoritative set and
# decides which codes may join a given combination.
expect_warn("non-plain secondary language",
            lambda c: c.update({"secondaryLanguages": ["pt-BR"], "providerOverride": "elevenlabs"}),
            "bad-secondary-language")
expect_no_code("non-plain secondary language is not an error",
               lambda c: c.update({"secondaryLanguages": ["pt-BR"], "providerOverride": "elevenlabs"}),
               "bad-secondary-language")
# ...but the multilingual provider rules are independent and must keep erroring.
expect_error("multilingual without the ElevenLabs pin",
             lambda c: c.__setitem__("secondaryLanguages", ["de"]), "multilingual-needs-elevenlabs-pin")
expect_error("multilingual pinned to Deepgram",
             lambda c: c.update({"secondaryLanguages": ["de"], "providerOverride": "deepgram"}),
             "deepgram-multilingual")

# 22a) PROVIDER RESOLUTION (schema §4.3/§5): a plain two-letter code is ElevenLabs territory, so
# resolution must not key off absence from the validator's documented ElevenLabs subset. ca/et/lv/lt are
# plain codes Deepgram also lists — routing them to Deepgram invented a provider mismatch out of nothing
# (elevenLabsSettings "ignored", an ElevenLabs-only model "not offered", a language "mismatch").
for _plain in ("ca", "et", "lv", "lt", "th"):
    _got = V.resolve_provider({"language": _plain})
    if _got != "elevenlabs":
        failures.append("plain language %r must resolve to elevenlabs, got %r" % (_plain, _got))
for _exclusive in ("en-US", "en-GB", "pt-BR", "es-419", "zh-Hans", "multi"):
    _got = V.resolve_provider({"language": _exclusive})
    if _got != "deepgram":
        failures.append("Deepgram-exclusive language %r must resolve to deepgram, got %r"
                        % (_exclusive, _got))
if V.resolve_provider({"language": "ca", "providerOverride": "deepgram"}) != "deepgram":
    failures.append("providerOverride must still win over the language rule")

expect_clean("Catalan agent keeps its ElevenLabs settings",
             lambda c: c.update({"language": "ca",
                                 "elevenLabsSettings": {"turnEagerness": "normal", "vad": True}}))
expect_no_warn("Catalan agent does not get the settings-ignored warning",
               lambda c: c.update({"language": "ca",
                                   "elevenLabsSettings": {"vad": True}}), "elevenlabs-settings-ignored")
expect_no_warn("Latvian agent does not get a language mismatch",
               lambda c: c.__setitem__("language", "lv"), "language-provider-mismatch")
expect_no_code("Estonian agent may use an ElevenLabs-only model",
               lambda c: c.update({"language": "et", "llmOverride": "openai - gpt-5"}),
               "llm-provider-mismatch")
expect_clean("Catalan multilingual agent with ElevenLabs settings and the pin",
             lambda c: c.update({"language": "ca", "secondaryLanguages": ["es"],
                                 "providerOverride": "elevenlabs",
                                 "elevenLabsSettings": {"turnModel": "turn_v3"}}))
# A Deepgram-exclusive code still gets the Deepgram consequences.
expect_warn("en-US agent is Deepgram, so ElevenLabs settings are ignored",
            lambda c: c.update({"language": "en-US", "elevenLabsSettings": {"vad": True}}),
            "elevenlabs-settings-ignored")
expect_error("en-US agent cannot use an ElevenLabs-only model",
             lambda c: c.update({"language": "en-US", "llmOverride": "openai - gpt-5"}),
             "llm-provider-mismatch")

# 22b) Schema §5 rule 4 ("else Deepgram") must be reachable: a code that is neither plain nor a listed
# Deepgram variant used to fall through to ElevenLabs, which suppressed every Deepgram consequence.
for _malformed in ("zz-ZZ", "pt-br", "EN_us-Garbage!"):
    _got = V.resolve_provider({"language": _malformed})
    if _got != "deepgram":
        failures.append("non-plain unknown language %r must resolve to deepgram (schema §5 rule 4), "
                        "got %r" % (_malformed, _got))
# ...while an unknown PLAIN code stays ElevenLabs territory and only draws the hedged language warning.
if V.resolve_provider({"language": "xx"}) != "elevenlabs":
    failures.append("unknown plain language 'xx' must resolve to elevenlabs")
expect_warn("unknown plain language warns", lambda c: c.__setitem__("language", "xx"), "unknown-language")
expect_no_warn("unknown plain language keeps its ElevenLabs settings",
               lambda c: c.update({"language": "xx", "elevenLabsSettings": {"vad": True}}),
               "elevenlabs-settings-ignored")
expect_warn("malformed language makes elevenLabsSettings ignored",
            lambda c: c.update({"language": "zz-ZZ", "elevenLabsSettings": {"vad": True}}),
            "elevenlabs-settings-ignored")

# 23) Numeric thresholds: dialTime saves across 5-120 but dispatch refuses above 90, and maxCallDuration
# above 120 is refused by the save itself.
expect_warn("dialTime above the dispatch limit", lambda c: c.__setitem__("dialTime", 100),
            "dialtime-dispatch-limit")
expect_clean("dialTime at the dispatch limit", lambda c: c.__setitem__("dialTime", 90))
expect_clean("dialTime 0 is the provider default", lambda c: c.__setitem__("dialTime", 0))
expect_error("dialTime out of the saved range", lambda c: c.__setitem__("dialTime", 130), "dial-time")
expect_no_warn("dialTime out of range reports the range only, not the dispatch limit",
               lambda c: c.__setitem__("dialTime", 130), "dialtime-dispatch-limit")
expect_warn("maxCallDuration above the recommended 120", lambda c: c.__setitem__("maxCallDuration", 130),
            "maxcall-over-limit")
expect_no_warn("maxCallDuration at 120 is fine", lambda c: c.__setitem__("maxCallDuration", 120),
               "maxcall-over-limit")
# There is NO hard API cap, so maxcall-over-limit is a recommendation warning, NOT save-refusing — a value
# above 120 still exits 0, and a value inside the recommended band stays clean.
if "maxcall-over-limit" in V.SAVE_REFUSED_CODES or "maxcall-over-limit" in V.SAVE_BLOCKING_CODES:
    failures.append("maxcall-over-limit must NOT be save-refusing — there is no hard API cap")
expect_warn("maxCallDuration far above the recommendation", lambda c: c.__setitem__("maxCallDuration", 200),
            "maxcall-over-limit")
if "maxcall-over-limit" in error_codes(dict(BASE, maxCallDuration=200)):
    failures.append("maxcall-over-limit must stay a WARN, not become an ERROR")
expect_clean("maxCallDuration inside the inbound band", lambda c: c.__setitem__("maxCallDuration", 60))

# 23a) An int-typed field that declares no `range` skips the range loop entirely, so its integer-ness
# needs its own check — otherwise 30.5 minutes reaches the API unremarked.
expect_error("fractional maxCallDuration", lambda c: c.__setitem__("maxCallDuration", 30.5), "bad-type")
expect_error("fractional dialTime", lambda c: c.__setitem__("dialTime", 30.5), "bad-type")
_frac_over = copy.deepcopy(BASE)
_frac_over["maxCallDuration"] = 120.5
if "bad-type" not in error_codes(_frac_over) or "maxcall-over-limit" not in warn_codes(_frac_over):
    failures.append("maxCallDuration 120.5 must report both bad-type and maxcall-over-limit, got %s / %s"
                    % (error_codes(_frac_over), warn_codes(_frac_over)))

# 24) temperature warns only above the 0.4-0.7 conversational band.
expect_warn("temperature above the conversational band", lambda c: c.__setitem__("temperature", 0.8),
            "temperature-high")
expect_clean("temperature at the top of the conversational band",
             lambda c: c.__setitem__("temperature", 0.7))

# 25) An outbound agent that does not speak first opens with dead air.
def outbound_silent(c):
    outbound(c)
    c["failoverOutboundNumberId"] = 202
    c["startSpeakingFirst"] = False


expect_warn("outbound not speaking first", outbound_silent, "outbound-speak-first")
expect_clean("outbound speaking first", outbound_with_failover)
# Inbound keeps the hard rule — it is BE-enforced, so it stays an ERROR, not this warning.
expect_error("inbound not speaking first",
             lambda c: c.__setitem__("startSpeakingFirst", False), "inbound-speak-first")
expect_no_warn("inbound not speaking first is not the outbound warning",
               lambda c: c.__setitem__("startSpeakingFirst", False), "outbound-speak-first")

# 26) The transfer-condition length limit is one number in both the code and the message: 120.
expect_warn("over-long transfer condition",
            transfer_rule(condition="x" * 121, destination="group", groupId=456, groupExtension="2001"),
            "transfer-vague-condition")
expect_clean("transfer condition at the limit",
             transfer_rule(condition="x" * 120, destination="group", groupId=456, groupExtension="2001"))
_long_cond = copy.deepcopy(BASE)
transfer_rule(condition="x" * 121, destination="group", groupId=456,
              groupExtension="2001")(_long_cond)
_long_rep = V.Report()
V.validate(_long_cond, FIELDS, _long_rep)
if not any("limit 120" in i.msg for i in _long_rep.issues if i.code == "transfer-vague-condition"):
    failures.append("the transfer-condition warning must name the same 120-char limit the code applies")

# 27) `upgradeAvailable` is a response-only diagnostic (recomputed server-side): an INFO note, not a WARN,
# and never an unknown-field error. (There is no `upgradeSummary` field — it does not exist.)
_upgrade = copy.deepcopy(BASE)
_upgrade["upgradeAvailable"] = True
_upgrade_rep = V.Report()
V.validate(_upgrade, FIELDS, _upgrade_rep)
if not any(i.level == "INFO" and i.code == "response-only" and i.where == "upgradeAvailable"
           for i in _upgrade_rep.issues):
    failures.append("upgradeAvailable must report as a response-only INFO, got %s"
                    % [(i.level, i.code, i.where) for i in _upgrade_rep.issues])
if error_codes(_upgrade) or warn_codes(_upgrade):
    failures.append("upgradeAvailable must not error or warn, got %s / %s"
                    % (error_codes(_upgrade), warn_codes(_upgrade)))
if "upgradeSummary" in V.RESPONSE_ONLY_DIAGNOSTIC_KEYS:
    failures.append("upgradeSummary is a phantom field — it must not be in RESPONSE_ONLY_DIAGNOSTIC_KEYS")

# 27a) The server-emitted diagnostics get the same treatment: an echoed GET response is an INFO note, not
# an unknown-field ERROR (they are documented forbidden rows, not typos).
for _diag in sorted(V.RESPONSE_ONLY_DIAGNOSTIC_KEYS):
    _echo = copy.deepcopy(BASE)
    _echo[_diag] = ["something the server said"]
    _echo_rep = V.Report()
    V.validate(_echo, FIELDS, _echo_rep)
    if not any(i.level == "INFO" and i.code == "response-only" and i.where == _diag
               for i in _echo_rep.issues):
        failures.append("%s must report as a response-only INFO, got %s"
                        % (_diag, [(i.level, i.code, i.where) for i in _echo_rep.issues]))
    if error_codes(_echo) or warn_codes(_echo):
        failures.append("%s must not error or warn, got %s / %s"
                        % (_diag, error_codes(_echo), warn_codes(_echo)))

# 28) The human report survives a console that cannot encode its glyphs: on Windows (cp1252/cp437) an
# unencodable glyph makes print() raise and the whole report is lost.
class _NarrowConsole(io.TextIOBase):
    """A cp1252 console with no reconfigure() escape hatch — write() fails exactly like the real thing."""
    encoding = "cp1252"

    def __init__(self):
        self.chunks = []

    def write(self, s):
        s.encode(self.encoding)
        self.chunks.append(s)
        return len(s)


if V.report_glyphs(_NarrowConsole()) is not V.GLYPHS_ASCII:
    failures.append("a cp1252 console must get the ASCII glyph set")
if V.report_glyphs(io.StringIO()) is not V.GLYPHS:
    failures.append("a stream with no encoding must keep the Unicode glyphs")
_narrow = _NarrowConsole()
try:
    with contextlib.redirect_stdout(_narrow):
        V.print_human(_wired_rep, "test")
except UnicodeEncodeError:
    failures.append("the human report must not crash on a cp1252 console")
_narrow_out = "".join(_narrow.chunks)
if "Nothing else to wire" not in _narrow_out:
    failures.append("the ASCII report must still carry its content, got %r" % _narrow_out[:200])

# 29) The exit code is the automation contract: a blocking warning is a failure, ordinary behavioral
# warnings without --strict are not. Example filenames are resolved by prefix so a rename cannot silently
# turn this check into a "could not read the file" pass.
import subprocess
import tempfile

_here = os.path.dirname(os.path.abspath(__file__))
_examples = os.path.join(_here, "..", "examples")


def run_validator(path):
    return subprocess.run([sys.executable, os.path.join(_here, "validate_config.py"), path],
                          capture_output=True).returncode


def run_validator_on(cfg):
    """Exit code for an in-memory config — the contract automation reads."""
    fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    try:
        fh.write(json.dumps(cfg))
        fh.close()
        return run_validator(fh.name)
    finally:
        os.unlink(fh.name)


def example_path(prefix):
    # `prefix + "-"`, not a bare prefix: "E1" must not also match E10.
    matches = sorted(glob.glob(os.path.join(_examples, prefix + "-*.jsonc")))
    if not matches:
        failures.append("no example matching %s* — update the exit-code checks" % prefix)
        return None
    return matches[0]


_e2 = example_path("E2")
if _e2 and run_validator(_e2) == 0:
    failures.append("E2's save-blocking warning must exit non-zero")
_e1 = example_path("E1")
if _e1 and run_validator(_e1) != 0:
    failures.append("E1 must still exit zero (pending wiring is not a failure)")

# no-hangup keeps WARN severity in the report, but its code is a blocking one: an agent that cannot end
# a call is not shippable, so the exit code must say so.
if "no-hangup" not in V.SAVE_BLOCKING_CODES:
    failures.append("no-hangup must be a save-blocking code")
_nh = copy.deepcopy(BASE)
_nh["scenarios"][0]["enabled"] = False
if "no-hangup" in error_codes(_nh):
    failures.append("no-hangup must stay a WARN, not become an ERROR")
if run_validator_on(_nh) != 1:
    failures.append("a config with no enabled hangup scenario must exit 1")

# maxCallDuration above 120 is a recommendation warning, not a save refusal — there is no hard API cap — so
# it exits ZERO (an ordinary behavioral warning), same as a value inside the band.
_over = copy.deepcopy(BASE)
_over["maxCallDuration"] = 200
if run_validator_on(_over) != 0:
    failures.append("maxCallDuration above 120 must exit 0 — it is a recommendation, not a save refusal")
_under = copy.deepcopy(BASE)
_under["maxCallDuration"] = 60
if run_validator_on(_under) != 0:
    failures.append("maxCallDuration 60 must exit 0")
# A genuinely save-blocking config for the --json blocking checks below: outbound on Automatic with no
# failover (both-directions gate).
_blocked = copy.deepcopy(BASE)
outbound(_blocked)
if run_validator_on(_blocked) != 1:
    failures.append("outbound Automatic with no failover must exit 1 — the save is refused")


# 30) `--json` states the blocking verdict outright, so automation reading the report does not have to
# re-derive the blocking code set for itself.
def run_validator_json(cfg):
    fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    try:
        fh.write(json.dumps(cfg))
        fh.close()
        proc = subprocess.run(
            [sys.executable, os.path.join(_here, "validate_config.py"), fh.name, "--json"],
            capture_output=True, text=True)
        return json.loads(proc.stdout)
    finally:
        os.unlink(fh.name)


_clean_json = run_validator_json(BASE)
if _clean_json.get("saveBlocking") is not False:
    failures.append("a clean config must report saveBlocking false, got %r"
                    % _clean_json.get("saveBlocking"))
if _clean_json.get("nothingElseToWire") is not True:
    failures.append("the pre-existing --json keys must keep their meaning on a clean config")
_over_json = run_validator_json(_over)
if _over_json.get("saveBlocking") is not False:
    failures.append("a maxCallDuration above 120 must report saveBlocking false, got %r"
                    % _over_json.get("saveBlocking"))
_blocked_json = run_validator_json(_blocked)
if _blocked_json.get("saveBlocking") is not True:
    failures.append("outbound Automatic with no failover must report saveBlocking true, got %r"
                    % _blocked_json.get("saveBlocking"))
if _blocked_json.get("nothingElseToWire") is not False:
    failures.append("a save-blocking config must not read as nothing-else-to-wire")

# 31) The trailing-comma retry must be string-aware: a comma-space-bracket sequence INSIDE a string value
# must survive, while a real trailing comma is still stripped. The real trailing comma below forces the
# retry path; the earlier string values would be corrupted by a document-wide regex strip.
_raw_trailing = (
    '{\n'
    '  "agentName": "Acme, }",\n'
    '  "note": "list was [a, b, ]",\n'
    '  "direction": "inbound",\n'
    '}'
)
_parsed = V.parse_config(_raw_trailing)
if _parsed.get("agentName") != "Acme, }":
    failures.append("trailing-comma retry corrupted a string ending in ', }': got %r"
                    % _parsed.get("agentName"))
if _parsed.get("note") != "list was [a, b, ]":
    failures.append("trailing-comma retry corrupted a string containing ', ]': got %r"
                    % _parsed.get("note"))
if _parsed.get("direction") != "inbound":
    failures.append("trailing-comma retry dropped a value: got %r" % _parsed.get("direction"))
# A genuine trailing comma outside any string is still removed (behavior unchanged).
if V.parse_config('{"a": 1, "b": [2, 3,],}') != {"a": 1, "b": [2, 3]}:
    failures.append("trailing-comma retry no longer strips real trailing commas")

if failures:
    print("FAIL — %d check(s):" % len(failures))
    for f in failures:
        print("  ✗ %s" % f)
    sys.exit(1)
print("OK — all positive, negative, and regression checks passed.")
sys.exit(0)
