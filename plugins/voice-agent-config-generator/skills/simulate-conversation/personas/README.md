Caller persona cards for `simulate-conversation`: intent and style only — never scripted lines; the conversation itself runs in the agent's configured `language`.
The runner fills each `goal_template`'s `<GOAL>` from the config's use case (`wrong-fit-caller`: an adjacent need this config does not serve) and passes exactly one card per simulator run.
