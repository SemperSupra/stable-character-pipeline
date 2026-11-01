#!/usr/bin/env python3
"""Original public source/media native negative controls; two views are NOT gait."""
import json,tempfile,sys
from pathlib import Path
from verify import assess
def denied(name,s,a,b):
 try:assess(s,a,b)
 except (ValueError,TypeError,KeyError,OSError):return name
 raise AssertionError("wrong ACCEPT for "+name)
s,a,b=map(Path,sys.argv[1:4])
r=assess(s,a,b)
assert r["qualification"]=="PASS_ORIGINAL_PUBLIC_SYNTHETIC_SOURCE_CAMERA_BYTES_ONLY"
assert r["issuer"]=="UNKNOWN_NOT_AUTHENTICATED" and r["R009"].startswith("HELD_")
controls=[denied("swapped_distinct_front_oblique",s,b,a),denied("duplicate_camera_alias",s,a,a)]
with tempfile.TemporaryDirectory() as folder:
 t=Path(folder);source=json.loads(s.read_bytes());source["actors"][0]["frames"][11]["root_x"]+=.002
 original=t/"wrong.json";original.write_text(json.dumps(source))
 controls.append(denied("tiny_source_motion_substitution",original,a,b))
 original.write_bytes(s.read_bytes()+b" ")
 controls.append(denied("source_byte_semantic_same_substitution",original,a,b))
 wrong=t/"altered.mp4";wrong.write_bytes(a.read_bytes()+b"\0")
 controls.append(denied("mutated_H264_bytes",s,wrong,b))
print(json.dumps({"status":"PASS_FIVE_ORIGINAL_BYTE_ROLE_NEGATIVES_ONLY","negative_controls":controls,"issuer":"UNKNOWN","R009":"HELD"},sort_keys=True))
