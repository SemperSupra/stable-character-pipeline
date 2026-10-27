# Independent EBU libear object panning reference

Spatial Audio DLE: https://github.com/SemperSupra/stable-character-pipeline/issues/18

This separate test does **not** replace the first-party libspatialaudio five-layout audio workcell, invent a new panner, render private character assets, or merge/release/deploy any existing experimental branches. It checks an independently maintained **EBU libear Apache-2.0** source implementation for ADM/ITU object-gain calculations.

- Exact source revision: `ebu/libear@2db69f8fcea0bc5db8a78e14a9c2ae6ed4283c15` (retrieved transiently on $0 public CPU GHA and pinned).
- First-party sample uses the documented `ear::GainCalculatorObjects`, `getLayout("0+5+0")` and `getLayout("0+7+0")`, tests azimuth +70° and -70° against **5.1 and 7.1** declared native channel-order labels, finite direct/diffuse gains, total energy, LFE exclusion for full-band object, and left/right mirror symmetry (tolerance <=0.005).
- No source/weights/audio downloaded from private resources. Eigen, Boost and xsimd are installed from Ubuntu repositories only in the disposable runner. The upstream commit is protected by an exact SHA check.
- The Linux build runs headlessly through CMake/Ninja, prints numeric gain observations and returns an explicit pass/failure receipt. No artifact upload occurs.
- Qualifying this oracle does **not** establish that libspatialaudio and libear produce equivalent gains; their processing, diffuse handling and interpolation differ. Our next experiment must put *the same precisely timed source and layout* through both engines and compare amplitude/channel mapping objectively.
- The native VideoLAN stereo renderer remains quarantined on NaN; the proven 5.1→stereo FFmpeg downmix is documented in public PR #21. A successful EBU oracle does not repair native stereo.
- Stereo, binaural HRTF, 2.1 bass management, acoustic simulation and Dolby/THX branded deliveries have separate admission boundaries.

All human, operator and agent audiences ultimately share `spatial_audio.v1`; this experiment provides one numerical reference primitive and is **not** a complete authoring UI, CLI render backend, or consumer headphone/perceptual qualification.
