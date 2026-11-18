# Numerical bakeoff N01 / N02 — public free-tier trial

**Scope.** Original synthetic scalar fixtures only. No private Naomi/Alison references, actual Aster/Juniper assets, rights-limited media, identities, credentials, paid cloud, Kaggle account access, GPU or sovereign hosts.

**N01.** Compare the existing style of semi-implicit Euler spring integration with limiter against adaptive substeps, classical RK4 and analytic damped-system reference for underdamped, critically damped and a permitted stiff/overdamped case. Require a deliberately failing legacy numerical case and bounded challenger errors. A passing result does not constitute real 3D tissue/cloth qualification.

**N02.** Independently reproduce a historical semantic-acceptance predicate where waist OR volume change satisfied an intended waist modification. A candidate must reject a volume-only edit and admit a genuine waist edit while preserving height. This does not modify private R032 source.

**Exactly reproducible commands:**

```sh
python3 -m unittest discover -s research/numerical-bakeoff-r1 -p test_bakeoff.py -v
python3 research/numerical-bakeoff-r1/bakeoff.py --lane n01
python3 research/numerical-bakeoff-r1/bakeoff.py --lane n02
```

Two independent standard Ubuntu public GitHub Actions jobs execute in parallel with 5-minute caps, read-only token, no secrets, no external Python dependencies, and three-day public synthetic JSON receipts. A PASS_NARROW establishes only the synthetic numerical behavior specified here. Owner acceptance, real character source and private MVP gates remain HOLD.

**DLE.** Public source-safe research evidence; private Product #2, R009 #23, R032 audit #166/P0 #167, and R033 #168 retain authority. Future separate workcells: N03 gait/contact reuse public R084 #645 and motion #29; N04 triangle+ARAP registration; N05 MPFB/MHR/Anny inverse morphology; N06 LBS/DQS/XPBD; N07 render accelerator compare; N08 revision-aware receipt/state invariants. No duplicate implementation of existing qualified workcells.
