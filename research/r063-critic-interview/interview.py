#!/usr/bin/env python3
"""Disposable MODEL interview probes; NOT a production critic or acceptance authority.

R063: source-original fixtures only. No network calls except Hugging Face model
download initiated by from_pretrained. No prompts or assets from private R009.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback

VISION_MODEL = "HuggingFaceTB/SmolVLM2-256M-Video-Instruct"
VISION_REV = "4d176c0088bd75e5e9291c3c3569f3d8ebbf836b"
AUDIO_MODEL = "openai/whisper-tiny"
AUDIO_REV = "169d4a4341b33bc18d8881c4b69c2e104e1cc0af"

def sha(data):
    return hashlib.sha256(data).hexdigest()

def checked(cmd, **kwargs):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=90, **kwargs)

def fixtures(path):
    from PIL import Image, ImageDraw
    path.mkdir(parents=True, exist_ok=True)
    files = {}
    for color in ("red", "blue"):
        img = Image.new("RGB", (224, 224), (240, 240, 240))
        ImageDraw.Draw(img).rectangle((65, 65, 159, 159), fill=color)
        target = path / ("image_" + color + ".png")
        img.save(target)
        files[color] = target
    for direction, positions in (("right", (12, 148)), ("left", (148, 12))):
        seq = path / ("sequence_" + direction)
        seq.mkdir(exist_ok=True)
        for i, xpos in enumerate(positions, 1):
            im = Image.new("RGB", (224, 224), "white")
            ImageDraw.Draw(im).rectangle((xpos, 90, xpos + 60, 150), fill="red")
            im.save(seq / ("frame_%03d.png" % i))
        mp4 = path / (direction + ".mp4")
        checked(["ffmpeg", "-v", "error", "-y", "-framerate", "1", "-i",
                 str(seq / "frame_%03d.png"), "-frames:v", "2",
                 "-pix_fmt", "yuv420p", "-c:v", "libx264", str(mp4)])
        # Read actual compressed video back, not the image producer's PNGs.
        decoded = path / ("decoded_" + direction)
        decoded.mkdir(exist_ok=True)
        checked(["ffmpeg", "-v", "error", "-y", "-i", str(mp4),
                 str(decoded / "frame_%03d.png")])
        frames = sorted(decoded.glob("*.png"))
        if len(frames) != 2:
            raise ValueError("video must produce precisely two decoded frames")
        files["video_" + direction] = (mp4, frames)
    return files

def load_vision():
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor
    torch.set_num_threads(2)
    processor = AutoProcessor.from_pretrained(VISION_MODEL, revision=VISION_REV)
    model = AutoModelForImageTextToText.from_pretrained(
        VISION_MODEL, revision=VISION_REV, torch_dtype=torch.float32,
        attn_implementation="eager").eval()
    return processor, model

def vision_reply(processor, model, images, prompt):
    from PIL import Image
    content = [{"type": "image", "image": Image.open(p).convert("RGB")} for p in images]
    content.append({"type": "text", "text": prompt})
    msgs = [{"role": "user", "content": content}]
    inputs = processor.apply_chat_template(
        msgs, add_generation_prompt=True, tokenize=True,
        return_dict=True, return_tensors="pt")
    outputs = model.generate(**inputs, do_sample=False, max_new_tokens=32)
    return processor.decode(
        outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True
    ).strip()

def single_label(text, choices):
    hits = [c for c in choices if re.search(r"\b" + re.escape(c) + r"\b", text.lower())]
    return hits[0] if len(hits) == 1 else "UNKNOWN"

def visual_lane(path, video):
    f = fixtures(path)
    proc, model = load_vision()
    records = []
    if video:
        for label in ("right", "left"):
            mp4, frames = f["video_" + label]
            prompt = ("Compare the first and second frames in that order. "
                      "Does the red square move LEFT, RIGHT or NOT MOVE? "
                      "Answer with only the direction.")
            response = vision_reply(proc, model, frames, prompt)
            predicted = single_label(response, ("left", "right"))
            records.append({"fixture": label, "sha256": sha(mp4.read_bytes()),
                            "predicted": predicted, "raw": response,
                            "passed": predicted == label})
    else:
        for label in ("red", "blue"):
            img = f[label]
            response = vision_reply(proc, model, [img],
                                    "What is the color of the center square? Answer one word.")
            predicted = single_label(response, ("red", "blue"))
            records.append({"fixture": label, "sha256": sha(img.read_bytes()),
                            "predicted": predicted, "raw": response,
                            "passed": predicted == label})
    return records

def audio_lane(path):
    import numpy as np
    import torch
    import wave
    from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
    path.mkdir(parents=True, exist_ok=True)
    source = path / "tts.wav"
    voice = path / "voice16.wav"
    checked(["espeak-ng", "-v", "en", "-s", "125", "-w", str(source),
             "Move the square left."])
    checked(["ffmpeg", "-v", "error", "-y", "-i", str(source),
             "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(voice)])
    silent = path / "silence16.wav"
    with wave.open(str(silent), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\0" * 32000)
    torch.set_num_threads(2)
    proc = AutoProcessor.from_pretrained(AUDIO_MODEL, revision=AUDIO_REV)
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        AUDIO_MODEL, revision=AUDIO_REV, torch_dtype=torch.float32,
        attn_implementation="eager").eval()
    records = []
    for label, p in (("left", voice), ("silence", silent)):
        with wave.open(str(p), "rb") as w:
            if w.getframerate() != 16000 or w.getnchannels() != 1:
                raise ValueError("unqualified audio sample rate/channels")
            samples = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
        audio = samples.astype("float32") / 32768.0
        inp = proc(audio, sampling_rate=16000, return_tensors="pt")
        out = model.generate(inp.input_features, max_new_tokens=64,
                             do_sample=False)
        response = proc.batch_decode(out, skip_special_tokens=True)[0].strip()
        normalized = re.sub(r"[^a-z0-9 ]", "", response.lower()).strip()
        passed = ("left" in normalized.split() if label == "left"
                  else normalized == "")
        records.append({"fixture": label, "sha256": sha(p.read_bytes()),
                        "raw": response, "passed": passed})
    return records

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane", choices=["image", "video", "audio"], required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    p = Path(args.out)
    p.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    model_id = AUDIO_MODEL if args.lane == "audio" else VISION_MODEL
    model_rev = AUDIO_REV if args.lane == "audio" else VISION_REV
    receipt = {
        "schema": "scp.r063.model-critic-interview.v1",
        "lane": args.lane, "status": "UNKNOWN", "model": model_id,
        "model_revision": model_rev, "declared_weights_license": "apache-2.0",
        "source_sha": os.getenv("GITHUB_SHA", "NOT_GHA"),
        "source_class": "ORIGINAL_SYNTHETIC_ONLY",
        "venue": "PUBLIC_GHA_CPU", "private_inputs": False,
        "executed": False, "model_critic_accepted": False,
        "product_accepted": False, "evidence": [], "first_failure": None,
    }
    try:
        result = (audio_lane(p) if args.lane == "audio"
                  else visual_lane(p, args.lane == "video"))
        receipt["executed"] = True
        receipt["evidence"] = result
        receipt["status"] = ("PASS_NARROW_SYNTHETIC_ONLY"
                             if all(x["passed"] for x in result) else "FAIL_CONTROLS")
        if receipt["status"] != "PASS_NARROW_SYNTHETIC_ONLY":
            receipt["first_failure"] = next(x["fixture"] for x in result if not x["passed"])
    except Exception as exc:
        receipt["status"] = "ERROR_RUNTIME_OR_DEPENDENCY"
        receipt["first_failure"] = type(exc).__name__ + ": " + str(exc)[:500]
        traceback.print_exc()
    receipt["elapsed_seconds"] = round(time.monotonic() - start, 2)
    canonical = json.dumps(receipt, sort_keys=True, ensure_ascii=False).encode()
    receipt["receipt_sha256_without_self_hash"] = sha(canonical)
    (p / "receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    print("R063_CRITIC_INTERVIEW", json.dumps(receipt, sort_keys=True))
    return 0 if receipt["status"] == "PASS_NARROW_SYNTHETIC_ONLY" else 12

if __name__ == "__main__":
    sys.exit(main())
