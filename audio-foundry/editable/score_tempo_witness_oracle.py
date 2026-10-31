"""Independent stdlib oracle for original-only synthetic tempo/MIDI/XML/WAV.
Source-generated clicks are NOT proof of performance fidelity or physical dance.
"""
import hashlib
import json
import struct
import sys
import wave
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path


def verify(path: Path) -> None:
    receipt = json.loads((path / "receipt.json").read_text())
    plan = json.loads((path / "time-map.json").read_text())
    source_path = path / "source.json"
    project = json.loads(source_path.read_text())
    assert receipt["source_project_sha256"] == hashlib.sha256(source_path.read_bytes()).hexdigest()
    assert receipt["source_project_sha256"] == plan["source_audio_project_sha256"]
    assert receipt["source_clock_plan_id"] == plan["content_id"]
    assert receipt["status"] == "ORIGINAL_SYNTHETIC_WAV_GENERATED_EXTERNAL_ONSET_REVIEW_REQUIRED"
    assert receipt["pcm_format"] == "MONO_PCM16_LE_ONSET_DIAGNOSTIC_NOT_MUSIC_PRODUCTION"
    for name, key in [
        ("original-synthetic-onsets.wav", "wav_sha256"),
        ("original-synthetic-tempo.mid", "midi_sha256"),
        ("original-synthetic-tempo.musicxml", "musicxml_sha256"),
    ]:
        assert hashlib.sha256((path / name).read_bytes()).hexdigest() == receipt[key]

    xml = ET.parse(path / "original-synthetic-tempo.musicxml").getroot()
    measures = xml.findall(".//part/measure")
    assert len(measures) == 8
    assert sum(len(measure.findall("./note/pitch")) for measure in measures) == len(project["notes"]) == 20
    tempos_xml = [
        (int(measure.attrib["number"]), float(direction.findtext(".//per-minute")))
        for measure in measures
        for direction in measure.findall("./direction")
        if direction.findtext(".//per-minute")
    ]
    assert tempos_xml == [(1, 120.0), (5, 90.0)]

    midi = (path / "original-synthetic-tempo.mid").read_bytes()
    assert midi[:4] == b"MThd" and int.from_bytes(midi[12:14], "big") == 480
    assert midi[14:18] == b"MTrk" and int.from_bytes(midi[18:22], "big") == len(midi) - 22

    def vlq(index):
        value = 0
        while True:
            byte = midi[index]
            index += 1
            value = (value << 7) | (byte & 127)
            if not byte & 128:
                return value, index

    position, tick, events = 22, 0, []
    while position < len(midi):
        delta, position = vlq(position)
        tick += delta
        status = midi[position]
        position += 1
        if status == 0xFF:
            kind = midi[position]
            position += 1
            size, position = vlq(position)
            data = midi[position:position + size]
            position += size
            if kind == 0x51:
                assert size == 3
                events.append((tick, "tempo", int.from_bytes(data, "big")))
            elif kind == 0x2F:
                assert size == 0
            else:
                raise AssertionError(f"Unsupported MIDI meta {kind}")
        elif status in (0x90, 0x80):
            pitch, velocity = midi[position:position + 2]
            position += 2
            if status == 0x90:
                assert velocity > 0
                events.append((tick, "onset", pitch))
        else:
            raise AssertionError(f"Unsupported MIDI status {status}")

    tempos = [(tick, value) for tick, kind, value in events if kind == "tempo"]
    assert tempos == [(0, 500000), (7680, 666666)]
    midi_onsets = [(tick, pitch) for tick, kind, pitch in events if kind == "onset"]
    assert len(midi_onsets) == 20
    assert [tick for tick, _ in midi_onsets] == [note["start_tick"] for note in project["notes"]]

    def independent_midi_sample(onset_tick):
        micros = Fraction(0)
        for i, (start, micros_per_quarter) in enumerate(tempos):
            stop = min(onset_tick, tempos[i + 1][0]) if i + 1 < len(tempos) else onset_tick
            if stop > start:
                micros += Fraction((stop - start) * micros_per_quarter, 480)
        return int(micros * 48000 / 1000000 + Fraction(1, 2))

    with wave.open(str(path / "original-synthetic-onsets.wav"), "rb") as audio:
        assert (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) == (1, 2, 48000)
        assert audio.getnframes() == receipt["sample_count"] == 896000
        num_samples = audio.getnframes()
        pcm = struct.unpack(f"<{num_samples}h", audio.readframes(num_samples))

    actual = [index for index, amplitude in enumerate(pcm)
              if amplitude >= 11000 and (index == 0 or pcm[index - 1] < 11000)]
    expected = [note["sample"] for note in receipt["note_onsets"]]
    assert len(actual) == len(expected) == 20
    assert actual == expected
    assert max(abs(observed - independent_midi_sample(tick))
               for observed, (tick, _) in zip(actual, midi_onsets)) <= 2
    assert actual[12] == 384000 and actual[13] == 448000
    assert plan["score_minus_audio_end_samples"] == "128000"
    tampered = list(expected)
    tampered[13] += 40
    assert actual != tampered
    print("PASS 20 synthetic PCM/MIDI/XML note onsets across actual 120-to-90 BPM witness")
    print("HOLD: original diagnostic renderer only; human dance motion/score provenance NOT qualified")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: oracle.py EVIDENCE_DIR")
    verify(Path(sys.argv[1]))
