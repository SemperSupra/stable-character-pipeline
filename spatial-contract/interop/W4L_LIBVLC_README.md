# W4l-B4 — Native VideoLAN libVLC original PCM callback qualification

Owner prereg: [Spatial #39 comment 6530696576](https://github.com/SemperSupra/stable-character-pipeline/issues/39#issuecomment-6530696576). This draft is stacked on source-original B3 [#157](https://github.com/SemperSupra/stable-character-pipeline/pull/157) at `83d193bf749c11caa74c33e6c668cff6068ba0a4`. No source transfer from R009 or private character data.

**Source:** exactly 16,384 mono S16LE samples at 48,000 Hz, impulses `(0,12000),(4096,15000),(8192,10000)`, otherwise zero. B3 verified frozen SHA256 `155cd0c71c1743bfb2ff90fe36288b354f766f89da4ebcd8adc9febe456b9d39`.

**Native job:** Ubuntu 24.04 standard public $0 runner; apt-installed libVLC 3.x version observed (not misrepresented as a pinned upstream Git commit), real `libvlc_audio_set_callbacks` and S16N/48k/mono. Writes original raw+WAV, **unmodified entire callback** raw, native state/first-failure receipt, and actual libVLC version. No pre-skip, post-trim, resampling forgiveness or inferred physical delay. Bounded 12s and no credentials.

**Independent job:** separate clean worker reconstructs source bytes independently, checks WAV envelope, complete callback sample count and exact PCM, version and true native termination, with two positive and twelve hostile fixture controls. Distinguish a successful producer from a scientific FAIL: actual output mismatch is preserved as FAIL with the original native bytes for diagnosis, not masked by green CI.

**Semantics:** libVLC audio decode/output callback is *not* an OpenAL HRTF or SAF TVConv equivalent; do not compare filter responses or assume a universal delay. No actual R009 character, Foley event, human audio, real physical perception, or product acceptance.

**Custody:** source/tests, immutable SHAs, compact receipts in public Git/DLE; original GHA ZIP artifacts short-lived for native evidence. Retained large native media only via admitted owner-private Google Drive, independently full-byte SHA rehydrated, with cross-reference in private Product #2. No private Git material/locators in public.

**State:** Source candidate only until exact PR HEAD, native GHA and independent job are read back. Preserve first failure, initial failures and all private source, rights, runner, merge/release, deploy, CPE promotion holds.