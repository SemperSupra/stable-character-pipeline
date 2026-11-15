# R033 source-known synthetic 2D visual-critic negative controls

Three first-party authored image fixtures: normal two-arm stylized humanoid (`YES`), omitted right arm (`NO`), and occluded right arm/shoulder (`UNKNOWN`). All were generated on a public standard free CPU runner and never contain real human identity, actual character output, private repository bytes, owner feedback, secrets or paid API keys.

Model `HuggingFaceTB/SmolVLM-256M-Instruct` at exact pinned `d039ab0d4b9311b617e8ffec1d06c8464364aeb3`. Same version/prompt for every fixture, no target answer in actual request; generation flags deterministic. Source-known fixture truth is independent of VLM response, but not a separate geometry-engine oracle, and three drawings are not heldout anatomy/photoreal acceptance.

Record each exact screenshot hash, response, latency, count correct/incorrect, and `UNKNOWN` abstention. No asserted critic PASS from code execution or any single answer. A model fails a fixture if it guesses a hidden limb rather than abstains. Don't hide failures or change rubric after looking at results.

DLE: Stable Character R033 #168, Oneirifact critic R60 #88. Frozen G4/G5, native source/permission, character canon and human preference unchanged.
