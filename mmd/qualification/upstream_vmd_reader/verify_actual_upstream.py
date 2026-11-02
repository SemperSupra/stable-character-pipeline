#!/usr/bin/env python3
"""Use UNMODIFIED pinned upstream MMD Tools File.load on authored VMD bytes.
Format-reader interoperability only. Does not run Blender or MMD animation.
"""
import argparse,hashlib,importlib.util,json,math,pathlib,sys
EXPECTED="3b20c6822337dab0078d32a2d65f7ead2d11716db5e5500b619d3218b4439b94"
SOURCE_COMMIT="f1d8a98db5e185cfa73c9b8a8a67fa42d9eb4b14"
SOURCE_ANNOTATED_TAG_OBJECT="fc6411d0fb0dd690cae8cf8eb1fae14311e756cc"
LABELS=("Center","L_Ankle","R_Ankle")
CANON=(20,20,107,107)

def check(data_path,upstream):
 source=pathlib.Path(data_path)
 raw=source.read_bytes()
 sha=hashlib.sha256(raw).hexdigest()
 if sha!=EXPECTED:raise ValueError("UPSTREAM_READER_UNADMITTED_SOURCE_SHA")
 reader=pathlib.Path(upstream)/"mmd_tools"/"core"/"vmd"/"__init__.py"
 if not reader.is_file():raise ValueError("PINNED_UPSTREAM_READER_SOURCE_MISSING")
 spec=importlib.util.spec_from_file_location("mmd_upstream_vmd_unmodified",reader)
 mod=importlib.util.module_from_spec(spec)
 sys.modules[spec.name]=mod
 spec.loader.exec_module(mod)
 original=mod.File()
 original.load(filepath=str(source.resolve()))
 if original.header.model_name!="SCP_SYNTHETIC":
  raise AssertionError("UPSTREAM_MMD_MODEL_HEADER_MISMATCH")
 if set(original.boneAnimation)!=set(LABELS):
  raise AssertionError("UPSTREAM_MMD_BONE_TRACK_SET_MISMATCH")
 lengths={}
 endpoints={}
 for name in LABELS:
  keys=original.boneAnimation[name]
  if len(keys)!=31 or [k.frame_number for k in keys]!=list(range(31)):
   raise AssertionError("UPSTREAM_MMD_30FPS_FRAME_SEQUENCE_MISMATCH")
  for key in keys:
   if not all(math.isfinite(float(x)) for x in key.location+key.rotation):
    raise AssertionError("UPSTREAM_MMD_NONFINITE_INPUT")
   if abs(sum(float(x)**2 for x in key.rotation)-1)>1e-5:
    raise AssertionError("UPSTREAM_MMD_NOT_UNIT_ROTATION")
   if len(key.interp)!=64:raise AssertionError("UPSTREAM_MMD_NOT_64_INTERPOLATION_BYTES")
   for bank in range(4):
    actual=tuple(key.interp[16*bank+i] for i in (0,4,8,12))
    if actual!=CANON:raise AssertionError("UPSTREAM_MMD_BEZIER_BANK_NOT_LINEAR")
   if abs(float(key.location[0])-float(key.frame_number)/30)>1e-6:
    raise AssertionError("UPSTREAM_MMD_UNEXPECTED_KEY_X")
  lengths[name]=len(keys)
  endpoints[name]=[list(keys[0].location),list(keys[-1].location)]
 for x in ("shapeKeyAnimation","cameraAnimation","lightAnimation","selfShadowAnimation","propertyAnimation"):
  if len(getattr(original,x))!=0:
   raise AssertionError("UNQUALIFIED_NON_BONE_SECTION_"+x)
 return {"schema":"scp.mmd.vmd_upstream_fileload.v1",
  "status":"PASS_UNMODIFIED_PINNED_UPSTREAM_VMD_FORMAT_READER_ONLY",
  "source_vmd_sha256":sha,"upstream_commit":SOURCE_COMMIT,"upstream_tag_object":SOURCE_ANNOTATED_TAG_OBJECT,
  "upstream_entrypoint":"mmd_tools.core.vmd.File.load","bone_keyframes":lengths,
  "keyframe_count":sum(lengths.values()),"bezier_channels_per_key":4,
  "start_end_source_positions":endpoints,
  "human_capture":"NOT_ADMITTED","native_blender_bpy":"NOT_RUN",
  "native_mmd_animation":"NOT_RUN","pmx_bone_mapping":"NOT_RUN",
  "contact_rom_anatomy":"UNKNOWN","private_r009":"HELD_NOT_ACCEPTED"}

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--vmd");p.add_argument("--upstream");p.add_argument("--out")
 p.add_argument("--capabilities",action="store_true")
 a=p.parse_args()
 if a.capabilities:
  print(json.dumps({"schema":"scp.mmd.vmd_upstream_fileload.v1",
   "actions":["capabilities","check_original_synthetic_vmd"],
   "writer_actions":[],"private_r009":"HELD_NOT_ACCEPTED"},sort_keys=True))
  return 0
 if not (a.vmd and a.upstream and a.out):p.error("--vmd --upstream --out required")
 result=check(a.vmd,a.upstream)
 with pathlib.Path(a.out).open("x",encoding="utf-8") as f:
  json.dump(result,f,sort_keys=True,indent=2)
  f.write("\n")
 print(json.dumps(result,sort_keys=True))
 return 0
if __name__=="__main__":raise SystemExit(main())
