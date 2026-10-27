# Practice call in chat

A test any app can run, ChatGPT included: the user plays the caller, you play the AI Voice Agent strictly
from its setup, then you score the call. It is a **practice call, not an independent test**: the same
assistant plays the agent and scores it, nothing is dialed, and the real voice, timing, knowledge base
search and tools are not involved. Say that label once when you start, and again on the score.

Used by: the builder after a save (through its one next step), the checkup's tests, and the replay, to try
a fix on a caller card before saving it.

## 1 · Set it up

- **The setup under test.** Connected: read the agent fresh with `cloudtalk_get_voice_agent`. Offline: the
  setup the user pasted. A proposed change that isn't saved yet can be practised too: say so plainly
  (*"This plays the version with the shorter greeting. It isn't saved yet."*).
- **Knowledge.** When knowledge bases are linked and CloudTalk is connected, read
  `cloudtalk_list_knowledge_bases` once and keep each linked one's name, description and, for a custom one,
  its text. That is all the agent may answer from beyond its setup. A web page or file knowledge base's
  content can't be read here: asked about it, the agent says it will check, and the score says knowledge
  answers weren't tested.
- **Call details.** A `{{variable}}` nobody gives a value for is spoken as a gap, exactly as on a real call
  (`variables.md`). When the instructions use call details (a name, an appointment time), ask once whether
  the user wants to give sample values.
- **Tell the user, in two lines,** who they are calling, what you will play, and how to stop: *"Say 'end
  call' any time."* With a caller card (section 4), offer it as their brief: who calls and what they want.

Cost: one read for the setup and at most one for knowledge. The call itself makes no requests.

## 2 · Play the agent, strictly from the setup

- **Opening.** When the agent speaks first, say its greeting word for word. An inbound agent with no
  greeting says *"Hello, how can I help you today?"*. An outbound agent with no greeting, or one set to
  wait, stays silent until the user speaks.
- **Language.** Speak the agent's language. Switch only to one of its other languages, and only to follow
  the caller.
- **Flow.** One question per turn. Follow its task steps and their decision rules, nothing else.
- **Only what the setup grants.** A handoff only through a switched-on transfer rule (or questions it
  can't answer set to transfer, with a real target); otherwise offer a callback. No text message without
  a text-message scenario, no booking without a switched-on, connected booking skill, no lookup without a
  tool scenario, never email or keypad menus. A switched-off part grants nothing. The `guardrails` list
  never fires on real calls, so only the rules written in the instructions count.
- **Facts.** Only from the instructions, custom skills, scenarios and the knowledge from section 1.
  Anything else is handled the way the setup says to handle what it doesn't know.
- **Actions** go on their own line in plain brackets, never as a claim in speech: *[The agent ends the
  call]*, *[The agent transfers you to Sales]*, *[A text goes to your number]*, *[The agent looks up your
  order; the answer is imagined here]*.
- **Stay in role.** No hints, coaching or explanations mid-call. Stop at a hang-up or a transfer, when the
  user says "end call", or after about 15 of their turns.

## 3 · Score it, right after the call

Same checks as the simulator's judge (`../../claude-skills/voice-agent-simulator/rubric.md` where it
exists), adapted to plain words. Quote at most 15 words; no ids, field names or tool names.

**Must-pass checks.** Any miss means *Not yet*.

1. **Opening:** the greeting was said word for word, or the agent waited when it should.
2. **Language:** every line in the agent's language, or one of its other languages to follow the caller.
3. **Ending:** it can end calls, and this one ended through its setup (a hang-up or a transfer it has).
4. **Handoffs:** it never promised a person it couldn't reach.
5. **Details:** it asked for each detail it is meant to note after the call, on the path this call took.
6. **Capabilities:** it never claimed a text, booking, transfer, lookup, email or keypad it doesn't have.
7. **Gaps:** no line had a hole where a missing call detail should be.

**How it did, 1 to 5 each:** length of answers, flow, tone, one question at a time, helpfulness, ending. A 5
needs a moment you can quote; clean but unremarkable is a 4.

**Result.** *Not yet* when a must-pass check failed or two scores are 1 or 2. *Passed, with gaps* when a
score is 3 or less or a change is worth making. *Passed* otherwise.

```text
**Practice call (not an independent test):** <the caller's goal in a few words> with <agent name>: <Passed | Passed, with gaps | Not yet>
**Missed:** <one plain line per failed must-pass check, with the moment it happened>
**How it did:** length of answers <n>/5 · flow <n>/5 · tone <n>/5 · one question at a time <n>/5 · helpfulness <n>/5 · ending <n>/5
**What to change:**
1. <the setup part, as the dashboard names it>: <the change>, because <what happened>
**Not tested:** real voice and timing, knowledge base contents, real tool answers, which number reaches the agent.
```

Leave out a line that is empty. End with one next step: when there is something to change, *"Want me to
make these changes and practise again?"* (the builder saves them); when it passed, a real test call of
at least 30 seconds.

## 4 · Caller cards: practice calls that come from real calls

The replay turns each proven cause into a caller card, so the same failure can be practised before a fix
is saved, and re-run on later replays:

```text
**Caller card: <plain name, e.g. "Asks for Sunday opening hours">**
- Who calls: <the kind of caller: style and patience>
- What they want: <the goal, in their words>
- What went wrong on real calls: <what the agent did, with the dates of the two calls that prove it>
- What a pass looks like: <the outcome you can see, e.g. "gives Sunday hours from its instructions, no guess">
```

To run a card:

- **In Claude, with the `voice-agent-simulator` skill:** use the card as the persona (who calls sets the
  style, what they want fills the goal). After its blind judge, check *what a pass looks like* against the
  transcript yourself and add one line: *Caller card: passed* or *not yet*.
- **In any app:** a practice call where the user plays the card's caller.

Either way it is practice, **not a real-engine test**: say so. Offer to keep the cards in this chat or in a
document the user names, and on the next replay re-run them first on the current setup.
