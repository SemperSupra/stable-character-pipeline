# Scientific and code donors — review candidate methodology, not automatic admission

This source inventory supports [DLE #582](https://github.com/SemperSupra/stable-character-pipeline/issues/582). Each donor must be pinned to an exact source revision, license-checked by code and asset, tested independently, and documented as reference/oracle or isolated adapter before copying anything. No third-party source, recordings or assets are bundled here.

| Candidate | Relevant methodology | Qualification limits |
| --- | --- | --- |
| [Faust physmodels.lib](https://faustlibraries.grame.fr/libs/physmodels/) and [source](https://github.com/grame-cncm/faustlibraries/blob/master/physmodels.lib) | fractional-delay waveguides, `fluteEmbouchure`, `clarinetMouthPiece`, blower, reed, wind `wBell`, source-filter vocal effects | Check original library/version license and effect; a generic flute or reed function is not an anatomically complete player |
| [STK](https://github.com/thestk/stk) | physical modeling wind source and real-time DSP primitives, instrument objects | Compare code and license against separately authored Go; instrument resonance must be separate from vocal source |
| [VocalTractLab](https://vocaltractlab.de/) | glottal source, articulatory tract, vocal performance trajectories | GPL/source and anatomical validation separately reviewed |
| [Pink Trombone](https://github.com/IMAGINARY/pink-trombone) | mouth/tongue controls, nasal branch, turbulent noise and glottal source | Educational simulation and source rights; cannot infer exact anatomy or panic/gasp biology |
| [Nasal vs oral respiratory measurement](https://pubmed.ncbi.nlm.nih.gov/21956580/) | breath phase and route spectrum measurements | Small study, different sensors/subjects; no fixed template for every person |
| [Dynamic glottis respiratory fluid/acoustics model](https://pmc.ncbi.nlm.nih.gov/articles/PMC5962264/) | time-varying glottis, CFD and breathing sounds | Heavier scientific reference; not immediate low-cost live synthesis |
| [Oral whistling MRI](https://pmc.ncbi.nlm.nih.gov/articles/PMC6048461/) and [jet-vortex measurements](https://doi.org/10.1121/10.0041252) | tongue/pursed lips, cavities, jet instability, whistled pitch | Distinct from singing in high `whistle register` |
| [Human beatboxing articulatory study](https://pubmed.ncbi.nlm.nih.gov/33514144/) | labial/tongue closures, pulmonary vs non-pulmonary egressive/ingressive mechanisms | Some real beatbox transient mechanisms don't depend on lung flow |
| [High soprano phonation mechanism](https://pmc.ncbi.nlm.nih.gov/articles/PMC11161605/) | physical vocal-fold phonation can underlie a high 'whistle register' | Do not model this automatically as external aerodynamic lip whistle |
| [VocalSound](https://sls.csail.mit.edu/downloads/vocalsound/) | 21,024 labeled cough/laugh/sigh/etc examples | CC BY-SA 4.0, consent/person metadata and derived use governance |
| [Deeply Nonverbal OpenSLR99](https://openslr.org/99/) | panting, crying, laughing, screaming, lip-popping and other classes | CC BY-NC-ND 4.0: do not use to train derivative audio generation; separate rights review, no public PII |

**Free-tier original bakeoff only:** start with deterministic synthetic auditory examples and mathematical conservation oracles. Source/critic acceptance from public CPU cannot establish physiological realism or user listening preferences. Real anatomy and identity material remain in private/sovereign custody.
