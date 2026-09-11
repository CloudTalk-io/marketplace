#!/usr/bin/env python3
"""check_docs_sync.py — CI guard that schema.md, fields.json and validate_config.py still agree.

Three sources describe the same field set and would drift apart silently: the human table in
`schema.md` §2, the machine registry in `fields.json`, and the enums hardcoded in `validate_config.py`
(kept there so the validator stays self-contained). A field added to one but not the others turns into
either a false `unknown-field` ERROR on a valid config or a silent pass on an invalid one.

Checks:
  1. schema.md §2's field set and `authoring` column == fields.json `topLevel` paths and tiers.
     `skills` is the one allowed schema-only row: it is the container key for the skills section and
     has no `topLevel` entry (the validator patches it in via EXTRA_TOPLEVEL_KEYS).
  2. fields.json's `tone` enum == validate_config.TONE_PRESETS, and the `elevenLabsSettings`
     subFields paths == ELEVENLABS_SETTING_SHAPES keys / BACKGROUND_SOUND_FIELDS.
  3. The enums schema.md spells out in prose or tables == the ones the validator mirrors in code:
     §4.2's per-provider LLM matrix == ELEVENLABS_MODELS / DEEPGRAM_MODELS; §4.3's Deepgram language
     list == DEEPGRAM_LANGS, plus the plain-two-letter-code rule provider resolution now keys off;
     §4.4's premade voice IDs == KNOWN_VOICE_IDS; §11's tone labels == TONE_PRESETS and its verbosity
     values == VERBOSITIES; §7.1's scenario actions == SCENARIO_ACTIONS (and fields.json's
     `scenarioActions` rows).

Not checked (so the README must not claim it): §4.2's legacy-alias list (prose gives examples, not the
whole map), the skills sub-schema shapes, and every threshold that lives only in the validator.

Stdlib only. Run: python3 scripts/check_docs_sync.py   (exit 0 = in sync, 1 = a mismatch)
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
SCHEMA_PATH = os.path.join(SKILL_DIR, "schema.md")
FIELDS_PATH = os.path.join(SKILL_DIR, "fields.json")

sys.path.insert(0, HERE)
import validate_config as V  # noqa: E402

# `skills` is documented in the §2 table but carries no fields.json topLevel row.
SCHEMA_ONLY_FIELDS = {"skills"}
SECTION_2_RE = re.compile(r"^##\s+2\.")
NEXT_SECTION_RE = re.compile(r"^##\s")
TIER_NOISE_RE = re.compile(r"[`*()¹²³\s]")
ANY_HEADING_RE = re.compile(r"^#{2,4}\s")
SUPPORTED_MARK = "✅"


def section_2_lines(text):
    """The lines under the §2 heading, up to the next `## ` heading."""
    out, inside = [], False
    for line in text.splitlines():
        if SECTION_2_RE.match(line):
            inside = True
            continue
        if inside and NEXT_SECTION_RE.match(line):
            break
        if inside:
            out.append(line)
    return out


def parse_toplevel_table(text):
    """{field: authoring tier} from §2's pipe table. Returns {} when the table cannot be found."""
    rows = {}
    started = False
    for line in section_2_lines(text):
        stripped = line.strip()
        if not stripped.startswith("|"):
            if started:
                break                       # the table ended; later pipe text is not it
            continue
        started = True
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 2:
            continue
        field = cells[0].strip("` ")
        if not field or field.lower() == "field" or set(cells[0]) <= set("-: "):
            continue                        # header row / separator row
        rows[field] = TIER_NOISE_RE.sub("", cells[1]).lower()
    return rows


def section_lines(text, heading_re):
    """The lines under the first heading matching `heading_re`, up to the next heading."""
    out, inside = [], False
    for line in text.splitlines():
        if not inside:
            if heading_re.match(line):
                inside = True
            continue
        if ANY_HEADING_RE.match(line):
            break
        out.append(line)
    return out


def diff_lines(label, schema_set, fields_set):
    problems = []
    for missing in sorted(schema_set - fields_set):
        problems.append("%s: `%s` is in schema.md §2 but not in fields.json topLevel" % (label, missing))
    for extra in sorted(fields_set - schema_set):
        problems.append("%s: `%s` is in fields.json topLevel but not in schema.md §2" % (label, extra))
    return problems


def check_field_set(schema_rows, fields):
    problems = []
    if not schema_rows:
        return ["schema.md: could not parse the §2 top-level table (heading or pipe rows changed)"]
    toplevel = {f["path"]: f for f in fields.get("topLevel", [])}
    schema_fields = set(schema_rows) - SCHEMA_ONLY_FIELDS
    problems += diff_lines("field set", schema_fields, set(toplevel))
    for path in sorted(schema_fields & set(toplevel)):
        want = schema_rows[path]
        got = str(toplevel[path].get("authoring", "")).strip().lower()
        # `generate¹` and `(per-skill)` normalize to the bare tier; a real disagreement is a typo or a
        # deliberate reclassification that only landed in one file.
        if want != got:
            problems.append("authoring tier: `%s` is %r in schema.md §2 but %r in fields.json"
                            % (path, want, got))
    for path in sorted(SCHEMA_ONLY_FIELDS - set(schema_rows)):
        problems.append("field set: `%s` row disappeared from schema.md §2 — the validator still "
                        "patches it in via EXTRA_TOPLEVEL_KEYS" % path)
    return problems


def entry(fields, path):
    for f in fields.get("topLevel", []):
        if f.get("path") == path:
            return f
    return None


def check_enums(fields):
    problems = []
    tone = entry(fields, "tone")
    if tone is None:
        problems.append("fields.json: no topLevel entry for `tone`")
    else:
        declared = set(tone.get("enum") or [])
        if declared != V.TONE_PRESETS:
            problems.append("tone enum: fields.json has %s, validate_config.TONE_PRESETS has %s"
                            % (sorted(declared), sorted(V.TONE_PRESETS)))

    els = entry(fields, "elevenLabsSettings")
    if els is None:
        problems.append("fields.json: no topLevel entry for `elevenLabsSettings`")
        return problems
    paths = [s.get("path", "") for s in els.get("subFields") or []]
    if not paths:
        problems.append("fields.json: elevenLabsSettings has no subFields")
        return problems
    declared_top = {p.split(".", 1)[0] for p in paths}
    if declared_top != set(V.ELEVENLABS_SETTING_SHAPES):
        problems.append("elevenLabsSettings subFields: fields.json has %s, "
                        "validate_config.ELEVENLABS_SETTING_SHAPES has %s"
                        % (sorted(declared_top), sorted(V.ELEVENLABS_SETTING_SHAPES)))
    declared_bg = {p.split(".", 1)[1] for p in paths if p.startswith("backgroundSound.")}
    if declared_bg != set(V.BACKGROUND_SOUND_FIELDS):
        problems.append("backgroundSound subFields: fields.json has %s, "
                        "validate_config.BACKGROUND_SOUND_FIELDS has %s"
                        % (sorted(declared_bg), sorted(V.BACKGROUND_SOUND_FIELDS)))
    return problems


def compare(label, doc_set, code_set, doc_where, code_where):
    if doc_set == code_set:
        return []
    problems = []
    for missing in sorted(doc_set - code_set):
        problems.append("%s: `%s` is in %s but not in %s" % (label, missing, doc_where, code_where))
    for extra in sorted(code_set - doc_set):
        problems.append("%s: `%s` is in %s but not in %s" % (label, extra, code_where, doc_where))
    return problems


def check_llm_matrix(schema_text):
    """§4.2's per-provider matrix: one row per canonical ID, a ✅ in the provider column that offers it."""
    el, dg, seen_rows = set(), set(), 0
    for line in section_lines(schema_text, re.compile(r"^###\s+4\.2")):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 3 or set(cells[0]) <= set("-: "):
            continue
        model = cells[0].strip("` ")
        if not model or "llmOverride" in model:
            continue                        # header row
        seen_rows += 1
        if SUPPORTED_MARK in cells[1]:
            el.add(model)
        if SUPPORTED_MARK in cells[2]:
            dg.add(model)
    if not seen_rows:
        return ["schema.md: could not parse the §4.2 LLM matrix (heading or pipe rows changed)"]
    return (compare("LLM matrix (ElevenLabs)", el, V.ELEVENLABS_MODELS,
                    "schema.md §4.2", "validate_config.ELEVENLABS_MODELS")
            + compare("LLM matrix (Deepgram)", dg, V.DEEPGRAM_MODELS,
                      "schema.md §4.2", "validate_config.DEEPGRAM_MODELS"))


def check_languages(schema_text):
    """§4.3: the Deepgram list is enumerated, so it is compared code-for-code. ElevenLabs' real set is
    ~66 codes and is NOT enumerated there — the doc's rule is "every plain two-letter code", which is
    what provider resolution keys off, so that rule is what gets checked instead of a list."""
    body = "\n".join(section_lines(schema_text, re.compile(r"^###\s+4\.3")))
    problems = []
    match = re.search(r"\*\*Deepgram\*\*.*?:\s*`([^`]+)`", body, re.S)
    if not match:
        problems.append("schema.md: could not parse the §4.3 Deepgram language list")
    else:
        documented = {c.strip() for c in match.group(1).split(",") if c.strip()}
        problems += compare("Deepgram languages", documented, V.DEEPGRAM_LANGS,
                            "schema.md §4.3", "validate_config.DEEPGRAM_LANGS")
    if "plain two-letter" not in body:
        problems.append("schema.md §4.3 no longer states the plain-two-letter-code rule that "
                        "validate_config.resolve_provider keys off — restate it or change the code")
    stray = sorted(c for c in V.ELEVENLABS_LANGS if not V.PLAIN_LANG_CODE_RE.match(c))
    if stray:
        problems.append("ElevenLabs languages: %s in validate_config.ELEVENLABS_LANGS are not plain "
                        "two-letter codes — that list is a documented subset of the plain codes, and "
                        "membership in it must never be decisive (schema.md §4.3)" % stray)
    plain_exclusive = sorted(c for c in V.DEEPGRAM_EXCLUSIVE_LANGS if V.PLAIN_LANG_CODE_RE.match(c))
    if plain_exclusive:
        problems.append("Deepgram-exclusive languages: %s are plain two-letter codes, which schema.md "
                        "§4.3/§5 puts on ElevenLabs" % plain_exclusive)
    outside = sorted(V.DEEPGRAM_EXCLUSIVE_LANGS - V.DEEPGRAM_LANGS)
    if outside:
        problems.append("Deepgram-exclusive languages: %s are not in DEEPGRAM_LANGS at all" % outside)
    return problems


def check_voices(schema_text):
    ids = set()
    for line in section_lines(schema_text, re.compile(r"^###\s+4\.4")):
        match = re.match(r"^([A-Za-z0-9]{20})\s+\(", line.strip())
        if match:
            ids.add(match.group(1))
    if not ids:
        return ["schema.md: could not parse the §4.4 voice ID block"]
    return compare("voice IDs", ids, V.KNOWN_VOICE_IDS,
                   "schema.md §4.4", "validate_config.KNOWN_VOICE_IDS")


def check_identity_presets(schema_text):
    """§11 spells out both identity enums in prose: tone as a backticked label line, verbosity as one
    bullet per value."""
    problems = []
    labels = set()
    for line in section_lines(schema_text, re.compile(r"^###\s+`tone`")):
        stripped = line.strip()
        if re.fullmatch(r"(?:`[a-z]+`)(?:,\s*`[a-z]+`)+", stripped):
            labels = set(re.findall(r"`([a-z]+)`", stripped))
            break
    if not labels:
        problems.append("schema.md: could not parse the §11 tone label line")
    else:
        problems += compare("tone labels", labels, V.TONE_PRESETS,
                            "schema.md §11", "validate_config.TONE_PRESETS")
    values = set()
    for line in section_lines(schema_text, re.compile(r"^###\s+`verbosity`")):
        match = re.match(r"^-\s+`([a-z]+)`\s+—", line.strip())
        if match:
            values.add(match.group(1))
    if not values:
        problems.append("schema.md: could not parse the §11 verbosity value bullets")
    else:
        problems += compare("verbosity values", values, V.VERBOSITIES,
                            "schema.md §11", "validate_config.VERBOSITIES")
    return problems


def check_scenario_actions(schema_text, fields):
    body = "\n".join(section_lines(schema_text, re.compile(r"^###\s+7\.1")))
    documented = set(re.findall(r'action == "(\w+)"', body))
    problems = []
    if not documented:
        problems.append("schema.md: could not parse the §7.1 scenario actions")
    else:
        problems += compare("scenario actions", documented, V.SCENARIO_ACTIONS,
                            "schema.md §7.1", "validate_config.SCENARIO_ACTIONS")
    registry = set()
    for row in fields.get("scenarioActions", []):
        match = re.match(r'^scenarios\[\]\.action == "(\w+)"$', str(row.get("path", "")))
        if match:
            registry.add(match.group(1))
    if not registry:
        problems.append("fields.json: no `scenarios[].action == \"…\"` rows in scenarioActions")
    else:
        problems += compare("scenario actions", registry, V.SCENARIO_ACTIONS,
                            "fields.json scenarioActions", "validate_config.SCENARIO_ACTIONS")
    return problems


def main():
    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as fh:
            schema_text = fh.read()
        with open(FIELDS_PATH, "r", encoding="utf-8") as fh:
            fields = json.load(fh)
    except (OSError, ValueError) as exc:
        print("Could not read the corpus: %s" % exc, file=sys.stderr)
        return 1

    problems = check_field_set(parse_toplevel_table(schema_text), fields)
    problems += check_enums(fields)
    problems += check_llm_matrix(schema_text)
    problems += check_languages(schema_text)
    problems += check_voices(schema_text)
    problems += check_identity_presets(schema_text)
    problems += check_scenario_actions(schema_text, fields)

    if problems:
        print("OUT OF SYNC — %d mismatch(es):" % len(problems))
        for p in problems:
            print("  - %s" % p)
        print("Fix the file that is behind; fields.json is the source of truth for the field set and "
              "each field's authoring class.")
        return 1
    print("OK — schema.md, fields.json and validate_config.py agree (field set + tiers, LLM matrix, "
          "languages, voices, tone/verbosity, scenario actions, elevenLabsSettings sub-fields).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
