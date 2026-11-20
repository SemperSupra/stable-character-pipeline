"""Source-first exact upstream Diffeomorphic makehuman.json asymmetry experiment.
Original research-only code. Not an MPFB rig calibration or license code fork.
"""
import hashlib,json,math
MAPPING_COMMIT="a4f2a394901d043457a9426f0d9e2ade9cda702c"
def qualified(raw):
 if len(raw)>65536:raise ValueError("MAPPING_FILE_OVERSIZE")
 info=json.loads(raw)
 if info.get("name")!="MakeHuman" or not isinstance(info.get("bones"),dict):raise ValueError("SOURCE_MAPPING_UNSUPPORTED")
 bones=info["bones"]
 expected={"upperleg01.L":"thigh.L","upperleg02.L":"thigh_twist.L",
           "upperleg01.R":"thigh.R","lowerleg01.L":"shin.L","lowerleg01.R":"shin.R",
           "foot.L":"foot.L","foot.R":"foot.R"}
 if any(bones.get(k)!=v for k,v in expected.items()):raise ValueError("UPSTREAM_MAPPING_DRIFT")
 if "upperleg02.R" in bones:raise ValueError("NO_MISSING_RIGHT_TWIST")
 if any(bones.get("lowerleg02."+s) is not None for s in ("L","R")):raise ValueError("UNKNOWN_SHIN_TWIST")
 return {"schema":"scp.n03d-n.vendor-map-audit.v1","vendor_source_commit":MAPPING_COMMIT,
  "raw_sha256":hashlib.sha256(raw).hexdigest(),
  "missing_source_target_right_thigh_twist":True,
  "symmetric_candidate":{"upperleg02.R":"thigh_twist.R"},
  "unmapped_shin_subdivisions":["lowerleg02.L","lowerleg02.R"],
  "variant_is_actual_native_qualified":False,"physical_contact_accepted":False,
  "release_authorized":False}
