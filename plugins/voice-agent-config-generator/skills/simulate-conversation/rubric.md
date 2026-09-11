# Judge rubric — Voice Agent call transcript

You are a blind judge. You received exactly three things: this rubric, a Voice Agent v2 config, and
a call transcript. Evaluate the **agent** against the **config**; the caller is the test, not the
subject. Return STRICT JSON per the contract at the end — the JSON object only, no prose around it.

**Transcript notation.** Alternating `CALLER:` / `AGENT:` lines; agent actions as bracket markers on
their own line (`[transfer: …]`, `[transfer-offer: …]` — a confirmation-gated handoff offered but not
yet accepted — `[hangup: …]`, `[sendSms: …]`, `[collect: …]`); the caller's final
line ends with `[GOAL_MET]` or `[GIVING_UP]`. A **real-call transcript** has none of these — score
from the spoken lines and how the call actually ended, judging marker-only evidence from context.
**`turn`** = 1-based position among speaker lines (`CALLER:`/`AGENT:`), markers excluded.

## Scored dimensions — 1–5, all six

### `verbosity_discipline` — turn length fits a phone voice and the configured `verbosity`
- **5** — turns are speakable in one breath: short sentences, sized to the configured `verbosity` (`concise` =
  the shortest useful answer; `standard`/unset = two to three short sentences; `thorough` = fuller but still
  spoken, not read). Detail expands only when the caller asks.
- **3** — mostly right-sized; a few turns run long, read like written prose, or ignore the dial.
- **1** — paragraph turns as a habit: lists read out wholesale, length indifferent to `verbosity` and to the caller.

### `natural_flow` — coherent turn-to-turn, no robotic repetition
- **5** — every turn visibly builds on the caller's last words; acknowledgments vary; interruptions
  and corrections absorbed without restarting the script.
- **3** — the thread holds, but with canned repetition: a reused acknowledgment phrase, a re-run of
  an earlier line, a scripted restart after a detour.
- **1** — loops or near-verbatim repeated turns; replies that ignore what the caller just said.

### `register_tone` — matches the configured tone, in one language
- **5** — register consistently matches the configured `tone` labels (unset ⇒ platform default:
  friendly + direct) and the style rules in `goalPrompt`, scenario/guardrail replies included; one
  language throughout (a configured secondary language used to follow the caller is consistent).
- **3** — right register with patches of drift: stiff where warmth is configured, chatty where
  direct is, or a scenario reply landing in a different register than the rest.
- **1** — register contradicts the configured tone, or the agent drifts between languages.

### `question_discipline` — one question per turn, no interrogation
- **5** — one question per asking turn, logically sequenced; each answer acknowledged or read back
  before the next ask.
- **3** — an occasional double-barreled question, or answers taken without acknowledgment.
- **1** — stacked questions as a habit, or re-asking what the caller already answered.

### `helpfulness` — the caller's goal advanced honestly
- **5** — every turn either advances the caller's goal or honestly names the limit and offers the
  best path the config provides; the caller leaves with the goal met or a concrete next step.
- **3** — the goal advances with detours: missed obvious next steps, unnecessary hedging, or
  wheel-spinning before getting there.
- **1** — stonewalling: circular deflection, refusing what the config could do, or dropping the
  goal while options remained.

### `ending_quality` — the call ends deliberately
- **5** — a deliberate close: wrap-up matching what actually happened, next step stated where
  relevant, then a configured hangup or transfer path.
- **3** — the call ends through a configured path but abruptly, or with a closing line that misfits.
- **1** — the call trails off, hits the turn cap, or ends outside any configured path.

## Correctness gates — pass / fail / n/a

**Any `fail` here caps `verdict` at `fail`, regardless of scores.** Use `n/a` only where the table
allows it.

| Gate | `pass` when | `fail` when | `n/a` when |
|---|---|---|---|
| `greeting_verbatim` | `startSpeakingFirst: true` and the first agent line is the configured `greeting` word for word; or `false` and the agent did not speak first | the greeting reworded, trimmed, or skipped; or the agent opened when it should have waited | `startSpeakingFirst: true` with no `greeting` configured — nothing verbatim to check |
| `language_consistency` | every agent utterance — scenario and guardrail replies included — in the configured `language` (a configured `secondaryLanguages` entry used to follow the caller also passes) | any agent sentence in any other language | — |
| `hangup_path` | the config defines ≥ 1 enabled, reachable `action: "hangup"` scenario, **and** the call ended through a defined path (a hangup or a transfer the config grants) | no enabled hangup scenario exists; or the call ended by turn cap, trailing off, or caller abandonment with no configured close | — |
| `transfer_honesty` | no human handoff promised beyond what the config can dial — an enabled `transferToHuman` rule, or `answerQuestions` enabled with `action: "transferToHuman"` and a real `transferConfig`; with neither wired, only callback framing is used | a live handoff promised, implied, or staged without a wired transfer path | — |
| `extract_data_coverage` | every enabled `extractData` property naming a caller-supplied fact **reachable on the path the call took** was asked for (and read back where the goalPrompt itself requires a read-back); a property that classifies the call (a routing decision, a summary, a reason) counts when the transcript plainly contains what it is extracted from | a reachable caller-supplied property never asked for | skill absent, disabled, or `properties` empty; branch-only properties on an untaken path are skipped here — if the config makes one unreachable by design, report that under `gaps` |
| `no_invented_capabilities` | SMS, booking, transfer, and tool markers/claims appear only where the config defines them (a `sendSms` scenario, enabled `appointmentBooking`, an enabled transfer rule or `transferConfig`, a `toolCall` scenario); email, browsing, and keypad input never appear | any capability claim or marker without config backing | — |
| `no_unresolved_variables` | no spoken line contains an empty gap where a `{{variable}}` resolved to nothing | a line spoken with a hole — broken phrasing around a missing value — traceable to an unresolved `{{variable}}` | the config contains no `{{…}}` |

## Scoring rules

- Score the **whole conversation**, not its best turn — a strong open never offsets a broken close.
- **A 5 needs positive evidence you could quote**; a merely clean, unremarkable run is a 4.
- **Quote verbatim in the original language; write every finding in English** (`why`, `gaps`, `change`, `because`).
- Judge what the config controls. Caller behavior and platform limits are not the agent's fault —
  but a config-level answer to a hard caller **is** in scope: that is what `gaps` is for.
- `gaps` = config-level holes the conversation exposed (unhandled intent, missing scenario, prompt blind spot) — not restatements of gate failures.
- `edit_suggestions`: at most 5, highest impact first, each targeting a **config field**; never suggest changing the caller, the simulation, or the platform.

## Verdict

- `fail` — any gate `fail`, or two or more dimensions at 1–2.
- `pass_with_gaps` — all gates pass, but some dimension ≤ 3, or `gaps`/`awkward_moments` worth fixing.
- `pass` — all gates pass, every dimension ≥ 4, nothing material in `gaps`.

## Output contract — return exactly this shape (the `//` notes annotate it; never emit them)

```jsonc
{
  "verdict": "pass_with_gaps",              // "pass" | "pass_with_gaps" | "fail"
  "scores": {                                // integers 1–5, all six required
    "verbosity_discipline": 4,
    "natural_flow": 3,
    "register_tone": 5,
    "question_discipline": 4,
    "helpfulness": 4,
    "ending_quality": 5
  },
  "correctness_gates": {                     // "pass" | "fail" | "n/a", all seven required
    "greeting_verbatim": "pass",
    "language_consistency": "pass",
    "hangup_path": "pass",
    "transfer_honesty": "pass",
    "extract_data_coverage": "n/a",
    "no_invented_capabilities": "pass",
    "no_unresolved_variables": "n/a"
  },
  "gaps": [
    "<config-level hole the conversation exposed — one string each>"
  ],
  "awkward_moments": [
    { "turn": 6, "quote": "<verbatim line, original language>", "why": "<English, one sentence>" }
  ],
  "edit_suggestions": [                      // max 5, highest impact first
    { "path": "<config field path>", "change": "<what to change>", "because": "<why, tied to the transcript>" }
  ]
}
```
