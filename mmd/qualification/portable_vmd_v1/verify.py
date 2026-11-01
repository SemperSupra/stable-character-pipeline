#!/usr/bin/env python3
"""Independent stdlib VMD v2 byte reader; NO runtime MMD playback/PMX admission."""
import hashlib,json,math,pathlib,struct,sys
p=pathlib.Path(sys.argv[1]);receipt=json.loads(pathlib.Path(sys.argv[2]).read_text())
raw=p.read_bytes();magic=b"Vocaloid Motion Data 0002"
assert raw[:len(magic)]==magic and raw[len(magic):30]==bytes(30-len(magic))
assert raw[30:50].rstrip(b"\x00")==b"SCP_SYNTHETIC"
n=struct.unpack_from("<I",raw,50)[0]
assert n==93 and len(raw)==74+n*111,(len(raw),n)
groups={}
for i in range(n):
    at=54+i*111
    name=raw[at:at+15].partition(b"\0")[0].decode("ascii")
    frame=struct.unpack_from("<I",raw,at+15)[0]
    pos=struct.unpack_from("<3f",raw,at+19)
    quat=struct.unpack_from("<4f",raw,at+31)
    assert all(math.isfinite(x) for x in pos+quat)
    assert abs(sum(x*x for x in quat)-1)<1e-5
    assert quat==(0.,0.,0.,1.)
    assert abs(pos[0]-frame/30)<1e-6
    assert pos[1]==0
    expected_z={"Center":0.,"L_Ankle":-.35,"R_Ankle":.35}
    assert name in expected_z and abs(pos[2]-expected_z[name])<1e-6
    assert raw[at+47:at+51]==bytes([20,20,107,107])
    groups.setdefault(name,[]).append(frame)
assert set(groups)=={"Center","L_Ankle","R_Ankle"}
assert all(v==list(range(31)) for v in groups.values())
assert raw[54+n*111:]==bytes(20)
assert hashlib.sha256(raw).hexdigest()==receipt["vmd_sha256"]
assert receipt["status"]=="PASS_SOURCE_ONLY_VMD_BINARY_STRUCTURAL_ROUNDTRIP"
assert receipt["real_mocap"]=="NOT_ADMITTED" and receipt["PMX_bone_binding"]=="NOT_RUN"
assert receipt["native_MMD_playback"]=="NOT_RUN" and receipt["R009"]=="HELD_NOT_ACCEPTED"
print(json.dumps({"schema":"scp.vmd.independent.structural-review.v1","reader":"python_struct_stdlib","records":n,"frames_per_bone":31,"status":"PASS_ORIGINAL_SYNTHETIC_VMD_STRUCTURAL_ONLY","native_MMD_playback":"NOT_RUN","actual_character_motion":"UNKNOWN"},sort_keys=True))
