# Stable Character Pipeline

A composable, versioned approach to creating, editing, validating, and maintaining **stable fictional character attributes** across generated media.

**Status: early research and private implementation.** No production model, public runtime, distributable dataset, published license, or character-identity quality guarantee is available from this repository yet.

## Product boundaries

- **Stable Character Pipeline** owns character-instance IDs, approved references and rights, immutable CharacterPack revisions, appearance/morphology invariants, edit specifications, generation integration, and independent validation.
- **Concept Policy Engine (CPE)** independently owns reusable character-related semantic concepts, definitions, multilingual lexicalizations, mappings, and concept promotion. CPE enriches character descriptions **optionally**, never as a runtime prerequisite. Character-pipeline consumers can submit research proposals for independent CPE adjudication; proposals do not mutate its ontology.
- **Object-centric media analysis (W2)** and **temporal analysis (W3)** are substitutable providers for candidate ranking, region grounding, and bounded tracking. A similarity score or track ID alone is not proof of stable identity.
- **Model Artifact Foundry** and deployment platforms are optional integration targets, not prerequisites for the core contracts.

## Planned audiences

- **Humans**, including assistive technology users: legible character information, visual comparisons, explicit uncertainty and approval controls.
- **Automation**: deterministic, versioned artifact and operation interfaces with explicit errors and idempotency.
- **Agents**: discoverable capabilities, bounded operations, provenance, validation receipts, and independently enforceable review gates.

## Release policy

The public repository is a **reviewed publication surface**, not an automatic mirror of private experiments. Publishing any code, character dataset, reference art, model weights, or trained adapter requires authorization, provenance and licensing review, security/privacy controls and relevant qualification evidence.

See [public release gate #1](https://github.com/SemperSupra/stable-character-pipeline/issues/1) for the current checklist. No automatic deployment or paid CI is configured.

## Roadmap

1. Establish stable CharacterPack/EditSpec contracts, lineage, offline validation and review UX.
2. Compare interchangeable image/region/track providers on bounded, rights-cleared test media.
3. Qualify optional CPE accepted-concept enrichment and research proposal exchange.
4. Prove character consistency with independent oracles across controlled generation/edit operations.
5. Release reusable code and synthetic fixtures only when the applicable gates have passed.
