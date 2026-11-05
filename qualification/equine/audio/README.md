# Equine audio event experiment — synthetic only

DLE: https://github.com/SemperSupra/stable-character-pipeline/issues/293

This independent Go stdlib workcell ingests a strict equine.contact.v1 JSON payload with source state SYNTHETIC_PLANNED, transforms time into exact 48 kHz PCM16 WAV samples and produces a checksum/semantics receipt. Terrain-specific acoustic primitives exist for sand, soil, grass and stone. The test fixture is four impacts in one 24-fps synthetic walk cycle and is NOT a measured real pony gait.

These are synthesized hoof Foley, NOT licensed animal recordings, whinnies, nickers, vocal anatomy or accepted biological audio. Real recorded animal samples remain a distinct individually-rights-qualified source workcell. Hard-reject nonintegral sample clocks, forged physical-contact state, invalid actor/foot/surface, duplicate or out-of-order events, unknown species vocal event, excessive input.

Three-audience: human WAV audition and contact sheet; automation Go CLI, JSON receipts and checksum; agent typed fail-closed time/asset interface. Reproducible and disposable GitHub public runner, no local dev box modification, no private material, no authorized main merge/release/deploy/CPE.
