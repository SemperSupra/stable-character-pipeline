# N03D-E — three independent temporal stance segmenters, synthetic oracle only

Prior physical RED: R090 real source recorded 100STYLE Aster shoe up to 95.578 mm below floor and Juniper skating 2.962075 m/s; N03C real 5-bone foot tail IK target improved but physical shoe sole still RED. Contact inference cannot substitute for actual evaluated shoe mesh world positions. N03D authority: public #662, #650, private R009 #23.

Three candidate algorithms on matching finite time-stamped shoe-proximity and measured horizontal motion: (1) per-frame height+velocity threshold; (2) stateful enter/exit hysteresis and minimum-three-sample dwell; (3) two-state Viterbi cost with transition penalty. Adversarial stdlib oracle includes planted, slip, hovering, single-sample false contact, missing telemetry, nonfinite, bad clocks, penetration >10mm. Contact *candidate* segments don't establish physical foot plant. Real source mapping into per-foot trace MUST be separately verified from actual rigid/deformed CC0 shoe. All source-only tests use no paid, GPU, private or external assets. No source recordings, protected real identities or binary models committed or uploaded. PASS_NARROW means only independent synthetic algorithm contracts, never human gait.

Design decision: Do NOT select a model based on fabricated ground truth alone. R095D native actual 24Hz metadata trace will be measured independently, then candidate algorithms/held-out trace oracles qualify before promotion into N03D/F native five-bone support solver. No condition is allowed to promote zero-stance/no-observed samples as PASS.

Draft/unmerged. No release or MVP gate waiver.
