"""ROM W4B: source-backed research candidate intake, no physiological ROM promotion.

A research citation proves the identity of a published method, not that a numeric
joint limit is correct or generalizes across species, body and load contexts.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

MAX=1_000_000
REQUIRED={"schema","candidate_id","domain","taxon","joint","parent_bone","child_bone",
          "axis_frame","unit","measurement","context","active_passive",
          "cohort","evidence_id","evidence_url","source_rights",
          "reviewer","review_state","numeric_limits","source_hash"}
SCHEMA="scp.rom.anatomical_candidate.v1"

def canonical(record):
    return json.dumps(record,sort_keys=True,separators=(",",":"),allow_nan=False).encode()

def evaluate(atlas,candidate,source_bytes):
    issues=[]
    if candidate.get("schema")!=SCHEMA or set(candidate)!=REQUIRED:
        raise ValueError("CANDIDATE_SCHEMA_FIELDS")
    if not source_bytes or hashlib.sha256(source_bytes).hexdigest()!=candidate["source_hash"]:
        raise ValueError("SOURCE_ORIGINAL_BYTES_SHA")
    if candidate["domain"] not in ("human","animal","machine","synthetic_fixture"):
        raise ValueError("DOMAIN_UNRECOGNIZED")
    names=("candidate_id","taxon","joint","parent_bone","child_bone","axis_frame","unit",
           "measurement","context","active_passive","cohort","evidence_id","evidence_url",
           "source_rights","reviewer","review_state")
    if any(not isinstance(candidate[x],str) or not candidate[x].strip() for x in names):
        raise ValueError("INCOMPLETE_PROVENANCE")
    if candidate["unit"] not in ("rad","m") or candidate["axis_frame"]=="unidentified" or        candidate["parent_bone"]==candidate["child_bone"]:
        raise ValueError("COORDINATE_FRAME_OR_BONE_IDENTITY")
    records={r["id"]:r for r in atlas["records"]}
    if candidate["evidence_id"] not in records or candidate["evidence_url"]!=records[candidate["evidence_id"]]["source"]:
        raise ValueError("ATLAS_SOURCE_NOT_MATCHED")
    linked=records[candidate["evidence_id"]]
    if linked["domain"]!=candidate["domain"]:
        raise ValueError("TAXON_EVIDENCE_DOMAIN_MISMATCH")
    if linked.get("taxon") and linked["taxon"]!=candidate["taxon"]:
        raise ValueError("WRONG_SPECIES_EVIDENCE")
    if candidate["active_passive"] not in ("active","passive","model_only","not_measured"):
        raise ValueError("ROM_MEASUREMENT_MODE")
    if candidate["source_rights"] not in ("PUBLIC_RESEARCH_REFERENCE_ONLY","ORIGINAL_SELF_AUTHORED_SYNTHETIC"):
        raise ValueError("SOURCE_LICENSE_NOT_ADMITTED")
    if candidate["review_state"] not in ("pending_independent_review","rejected","synthetic_test_only"):
        raise ValueError("REVIEW_STATE_NOT_ADMITTED")
    limits=candidate["numeric_limits"]
    if limits is not None:
        if not isinstance(limits,list) or len(limits)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in limits) or limits[0]>=limits[1]:
            raise ValueError("NUMERIC_LIMITS_INVALID")
        if candidate["domain"]!="synthetic_fixture":
            issues.append("BIOLOGICAL_OR_ROBOT_NORMATIVE_LIMITS_NOT_INDEPENDENTLY_ADMITTED")
    if candidate["domain"]=="animal" and not candidate["taxon"] in ("Canis lupus familiaris","Equus caballus","Aves"):
        issues.append("TAXON_CONTEXT_UNKNOWN")
    if candidate["active_passive"]=="not_measured":
        issues.append("NO_ACTUAL_ROM_MEASUREMENT")
    if candidate["review_state"]=="rejected":
        return {"schema":"scp.rom.anatomical_intake_receipt.v1","status":"FAIL_REVIEW_REJECTED","candidate_sha256":hashlib.sha256(canonical(candidate)).hexdigest(),"issues":["INDEPENDENT_REVIEW_REJECTED"]}
    issues.append("NEEDS_INDEPENDENT_NUMERIC_METHOD_RIGHTS_AND_FRAME_REVIEW")
    return {"schema":"scp.rom.anatomical_intake_receipt.v1",
            "status":"UNKNOWN_CANDIDATE_NOT_PRODUCTION_ADMITTED",
            "candidate_sha256":hashlib.sha256(canonical(candidate)).hexdigest(),
            "evidence_id":linked["id"],"source_hash":candidate["source_hash"],
            "issues":issues,"human_animal_rom_acceptance":"NOT_ACCEPTED",
            "can_promote":False}

def run(atlas,record,source,out):
    for p in (atlas,record,source):
        if Path(p).stat().st_size>MAX:
            raise ValueError("INPUT_BOUNDED_SIZE")
    a=json.loads(Path(atlas).read_text());c=json.loads(Path(record).read_text())
    if a.get("schema")!="scp.rom.provenance_atlas.v1":
        raise ValueError("ATLAS_SCHEMA_MISMATCH")
    r=evaluate(a,c,Path(source).read_bytes())
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
    print(json.dumps(r,sort_keys=True))
if __name__=="__main__":
    p=argparse.ArgumentParser()
    for k in ("atlas","record","source","out"):p.add_argument("--"+k,required=True)
    a=p.parse_args();run(a.atlas,a.record,a.source,a.out)
