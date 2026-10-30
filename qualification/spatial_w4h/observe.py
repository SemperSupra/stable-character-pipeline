"""Independent stdlib Python reference for a fixed original annotation fixture."""
import hashlib
import json
import sys
from fractions import Fraction
from pathlib import Path
p=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert p["schema"]=="scp.w4h_annotated_sync_receipt.v1"
assert p["status"]=="SOURCE_ONLY_TYPED_ANNOTATION_PASS"
assert p["cue_count"]==9
assert p["source_sha256"]==hashlib.sha256(b"original-synthetic-w4h-voice-source").hexdigest()
assert len(p["packet_sha256"])==64
frame=lambda s:int(Fraction(s*30000,48000*1001))
samples={"word0":24000,"ph0":24000,"ph1":30000,"vi0":24000,"vi1":30000,"expr0":22000,"gest0":28000,"cam0":0,"foot0":24000}
assert p["start_frames"]=={k:frame(v) for k,v in samples.items()}
assert p["mid_pose"]==Fraction(27000-24000,30000-24000)
print("W4H_INDEPENDENT_SOURCE_CLOCK_PASS cues=9 sample_clock=48000 fps=30000/1001")
