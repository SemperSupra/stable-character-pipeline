"""Independent decoded-PCM source-safe Csound transport test.

Inspects a REAL Csound-generated waveform; does not trust the original
Go note author, csd score text or receipt as a sufficient onset oracle.
"""
from pathlib import Path
import json
import sys
import struct
import wave

def verify(root):
    root = Path(root)
    receipt = json.loads((root / "receipt.json").read_text())
    assert receipt["source_project_sha256"]
    assert receipt["sample_count"] == 896000
    assert len(receipt["note_onsets"]) == 20
    file = root / "csound-target.wav"
    with wave.open(str(file), "rb") as f:
        assert (f.getnchannels(), f.getsampwidth(), f.getframerate()) == (1, 2, 48000)
        n = f.getnframes()
        assert abs(n - receipt["sample_count"]) <= 4, (n, receipt["sample_count"])
        pcm = struct.unpack(f"<{n}h", f.readframes(n))
    attacks = [i for i, v in enumerate(pcm) if v > 18000 and
               (i == 0 or pcm[i - 1] <= 18000)]
    expected = [v["sample"] for v in receipt["note_onsets"]]
    assert len(attacks) == len(expected) == 20, (len(attacks), len(expected), attacks[:25])
    errors = [abs(a - e) for a, e in zip(attacks, expected)]
    assert max(errors) <= 2, list(zip(attacks, expected, errors))
    assert any(a >= 384000 for a in attacks)
    mutated = expected[:]
    mutated[13] += 40
    assert max(abs(a - e) for a, e in zip(attacks, mutated)) > 2
    result = {
        "schema": "scp.original-synthetic-csound-transport-review.v0",
        "source_project_sha256": receipt["source_project_sha256"],
        "actual_pcm_samples": n,
        "tested_note_events": len(attacks),
        "maximum_absolute_onset_error_samples": max(errors),
        "status": "PASS_ORIGINAL_SYNTHETIC_EXTERNAL_CSOUND_DIAGNOSTIC_NOT_HISTORICAL_OR_R009",
        "performance_rights": "ORIGINAL_SYNTHETIC_ONLY",
        "true_human_motion": "NOT_RUN",
    }
    print(json.dumps(result, sort_keys=True))
    return result

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: csound_tempo_target_oracle.py EVIDENCE_DIR")
    verify(sys.argv[1])
