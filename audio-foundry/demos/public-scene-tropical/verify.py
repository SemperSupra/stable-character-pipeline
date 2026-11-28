"""Independent PCM and custody witness for original-only tropical demo."""
import argparse
import array
import hashlib
import json
import math
import pathlib
import subprocess
import sys
import tempfile
import unittest
import wave

NAMES = ("wind", "synthetic_chirps", "synthetic_pulses", "insect_texture", "leaf_rustle", "water_texture")
RATE = 48000
FRAMES = RATE * 12

def require(condition, message):
    if not condition:
        raise ValueError(message)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def pcm_metrics(path, frames=FRAMES):
    with wave.open(str(path), "rb") as wav:
        require((wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getnframes())
                == (2, 2, RATE, frames), f"invalid PCM format/duration: {path}")
        data = array.array("h", wav.readframes(frames))
    if sys.byteorder != "little":
        data.byteswap()
    require(len(data) == 2 * frames, f"truncated PCM: {path}")
    rms = math.sqrt(sum(x*x for x in data) / len(data)) / 32768
    peak = max(abs(x) for x in data) / 32768
    require(rms > 10 ** (-60/20), f"silent/low-level PCM: {path}")
    require(peak < 10 ** (-0.2/20), f"clipped/near-full-scale PCM: {path}")
    return {"rms": rms, "mean_dbfs": 20*math.log10(rms), "peak_dbfs": 20*math.log10(peak)}

def verify(root):
    manifest = json.loads((root/"scene.json").read_text())
    render = json.loads((root/"render_receipt.json").read_text())
    require(manifest["schema"] == "scene_audio.v1", "wrong manifest schema")
    require(manifest["classification"] == "PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL", "nonpublic source")
    require(render["schema"] == "scene_audio.receipt.v1" and render["scene_id"] == manifest["id"]
            and render["classification"] == manifest["classification"], "render receipt identity mismatch")
    require(len(manifest["tracks"]) == len(render["assets"]) == len(NAMES), "wrong track count")
    require({t["id"] for t in manifest["tracks"]} == set(NAMES), "wrong track identity")
    require({a["track_id"]: a["sha256"] for a in render["assets"]}
            == {t["id"]: t["sha256"] for t in manifest["tracks"]}, "renderer source mismatch")
    receipts = []
    for track in manifest["tracks"]:
        name = track["id"]
        require(track["asset"] == "stems/"+name+".wav", "unexpected stem path")
        path = root/track["asset"]
        require(sha(path) == track["sha256"], "stem digest mismatch")
        receipts.append(dict(path=track["asset"], sha256=sha(path), codec="pcm_s16le",
                             sample_rate=RATE, channels=2, duration_seconds=12, **pcm_metrics(path)))
    mix = root/"tropical_scene.wav"
    require(sha(mix) == render["output_sha256"] and mix.stat().st_size == render["output_bytes"],
            "render output digest/size mismatch")
    metrics = pcm_metrics(mix)
    receipts.append(dict(path=mix.name, sha256=sha(mix), codec="pcm_s16le",
                         sample_rate=RATE, channels=2, duration_seconds=12, **metrics))
    preview = root/"tropical_scene.m4a"
    meta = json.loads(subprocess.check_output(["ffprobe","-v","error","-select_streams","a:0",
        "-show_entries","stream=codec_name,sample_rate,channels:format=duration","-of","json",str(preview)]))
    require(len(meta["streams"]) == 1, "missing preview audio stream")
    stream = meta["streams"][0]
    duration = float(meta["format"]["duration"])
    require(stream["codec_name"] == "aac" and int(stream["sample_rate"]) == RATE
            and stream["channels"] == 2 and math.isfinite(duration) and abs(duration-12) <= .03,
            "invalid preview codec/rate/channels/duration")
    receipts.append(dict(path=preview.name, sha256=sha(preview), codec="aac", sample_rate=RATE,
                         channels=2, duration_seconds=duration))
    return dict(status="technical_signal_check_passed", classification=manifest["classification"],
                per_stem_pcm_acceptance="PASS", perceptual_acceptance="NOT_TESTED",
                real_device_acceptance="NOT_TESTED", event_causality="METADATA_ONLY",
                manifest_file_sha256=sha(root/"scene.json"), render_receipt_sha256=sha(root/"render_receipt.json"),
                assets=receipts)

class Negatives(unittest.TestCase):
    def make(self, path, value):
        with wave.open(str(path), "wb") as wav:
            wav.setparams((2,2,RATE,0,"NONE","not compressed"))
            wav.writeframes(int(value).to_bytes(2,"little",signed=True)*200)
    def test_signal_controls(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d)/"one.wav"
            for value in (0,32767,-32768):
                self.make(path,value)
                with self.assertRaises(ValueError):
                    pcm_metrics(path,100)
            self.make(path,1000)
            self.assertGreater(pcm_metrics(path,100)["rms"],0)
            with self.assertRaises(ValueError):
                pcm_metrics(path,101)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("root",type=pathlib.Path)
    p.add_argument("--gain-witness",type=pathlib.Path,required=True)
    a=p.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Negatives)
    require(unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful(),"negative controls failed")
    receipt=verify(a.root)
    baseline=pcm_metrics(a.root/"tropical_scene.wav")["rms"]
    changed=pcm_metrics(a.gain_witness)["rms"]
    ratio=changed/baseline
    require(abs(ratio-10**(-6/20)) < .02, f"manifest gain change not reflected in PCM: {ratio}")
    receipt["gain_mutation"]={"delta_db":-6,"rms_ratio":ratio,"expected_ratio":10**(-6/20),
                              "mutated_mix_sha256":sha(a.gain_witness),"acceptance":"PASS"}
    (a.root/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print("tropical_scene_receipt_PASS stems=6 independent_pcm_gain_mutation=PASS")

if __name__=="__main__":
    main()
