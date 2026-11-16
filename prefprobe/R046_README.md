# R046 synthetic preference robustness — opposite scopes and minimum evidence

Authority: private Stable Character R016 #145 for genuine human preferences and R037 #176 for photorealism DOE. Stacked on public synthetic-only preference PR #550 SHA f86dcd2cba63579fc1d19475097d07559a63fd71.

Source-safe algorithmic workcell only. There is **no real owner preference**, model weights, PII, copyrighted reference art, privileged asset or external API. One invented pairwise preference event previously returned a ranking; this research slice adds a predeclared five-independent-vote per-scope gate. One or four choices, 100 duplicate events, abstention-only events, unknown source / character / shot, and conflicting evidence must all abstain. A fixed number five is an engineering safety floor rather than calibrated statistical confidence; future owner-aware experiments must validate confidence with actually authored feedback.

The deterministic synthetic experiment now tests two disjoint lighting contexts with opposing invented labels, blind side reversals, and 10%-ish deterministic poisoned labels; holdout pairs are never ingested as training. Cross-context/source/character leakage and global replay event IDs fail closed. Current ranking still only returns SYNTHETIC_RANK_ONLY and never canonicalizes a CharacterPack or sets user preferences.

Run in disposable public Go runner:

    cd prefprobe
    go vet ./...
    go test -race -count=1 -v ./...
    go run . -synthetic

Workflow: .github/workflows/r046-pref-stress.yml. All evidence is source-original safe for free public standard GitHub Actions, no new scheduler. The current R016 #145 authority and R032 #167 source/intent P0 remain independent blockers for genuine human intention work. Use the original gallery #163 and independent R033 critics #168; avoid duplicating either. Keep draft until independent source-head tests and negative evidence are reviewed.

**Interpretation:** Passing proves the chosen synthetic fixture methods preserve scoped abstention and can distinguish fabricated opposed preferences at this sample size. It is NOT proof of human aesthetic generalization, useful personalization, calibrated preference probabilities, photographic realism, or actual owner acceptance.
