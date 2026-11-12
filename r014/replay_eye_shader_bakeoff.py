"""Reevaluate original native Blender logs without re-downloading CC0 assets.

Only explicit node API compatibility is qualified. Source archived artifacts
belong to public GHA run 43207664661, corrected adult phenotype presets.
"""
import argparse,hashlib,json,sys
from pathlib import Path
from r014.mpfb_shader_audit import audit

SOURCE_RUN=43207664661
MODES=("MAKESKIN","PROCEDURAL_EYES")

def inspect(root):
    result={}
    for mode in MODES:
        folder=root/mode
        log=folder/"eye_shader.log"
        source=folder/"generation.json"
        archived=folder/"acquisition.json"
        if not log.is_file() or not source.is_file() or not archived.is_file():
            raise ValueError("original shader trace/metadata unavailable for "+mode)
        scene=json.loads(source.read_text())
        acquisition=json.loads(archived.read_text())
        assert scene["eye_material_mode"]==mode,"mode label mismatch"
        assert acquisition["status"]=="PASS_PINNED_ARCHIVE_VERIFIED"
        assert acquisition["sha256"]=="b542127a8e25547c7c29c19f2d1d2adb9a664c80396ecd694095dbc8028a0107"
        assert {(c["sex"],c["source_gender_macro"]) for c in scene["characters"]}=={("female",0.),("male",1.)}
        raw=log.read_bytes()
        qa=audit(raw.decode("utf-8",errors="replace"),mode)
        qa["source_log_sha256"]=hashlib.sha256(raw).hexdigest()
        qa["native_scene"]="R014_MPFB_CC0_surface_study.blend" in [x.name for x in folder.iterdir()]
        qa["observed_model_characters"]=len(scene["characters"])
        assert qa["native_scene"],"archived Blender model absent from source artifact"
        result[mode]=qa
    assert result["MAKESKIN"]["status"]=="PASS_SHADER_LOG_COMPAT_ONLY","MAKESKIN still emits runtime node faults"
    assert result["PROCEDURAL_EYES"]["status"]=="HOLD_SHADER_LOG_COMPAT","procedural shader failure not reproduced"
    assert result["PROCEDURAL_EYES"]["node_error_count"]==20,"original error count mismatch; replay different logs"
    return {"status":"PASS_EVIDENCE_REPLAY_SHADERS_ONLY",
            "source_github_run":SOURCE_RUN,
            "accepted_compatibility_mode":"MAKESKIN",
            "rejected_compatibility_mode":"PROCEDURAL_EYES",
            "mode_receipts":result,
            "limits":["Zero node errors is not photoreal optical/material quality",
                      "Original 281MB CC0 archive source pinned and rights checked elsewhere",
                      "Only archived Blender 4.5.16 log compatibility checked",
                      "No sex organ geometry, complete human skin or video realism qualified"]}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--artifact-dir",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    out=inspect(a.artifact_dir)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print("R014_EYE_SHADER_BAKEOFF",json.dumps({k:v for k,v in out.items() if k!="mode_receipts"},sort_keys=True))
