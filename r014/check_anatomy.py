"""Fail-closed anatomical completeness admission contract, not a geometry creator."""
import argparse, json
from pathlib import Path

def assess(schema, candidate):
    errors=[]
    if schema.get("schema")!="r014.anatomical-coverage.v1":
        errors.append("schema-mismatch")
    if candidate.get("age_class")!="adult":
        errors.append("adult-only requirement unverified")
    found=candidate.get("features",{})
    for feature in schema.get("common_external",[]):
        if found.get(feature)!="PRESENT_VERIFIED":
            errors.append("common-geometry-unverified:"+feature)
    for var in candidate.get("active_reproductive_variants",[]):
        if var not in schema.get("external_reproductive_variants",{}):
            errors.append("unknown-anatomical-variant:"+var)
            continue
        for feature in schema["external_reproductive_variants"][var]:
            if found.get(feature)!="PRESENT_VERIFIED":
                errors.append("variant-geometry-unverified:"+var+"/"+feature)
    if not candidate.get("active_reproductive_variants"):
        errors.append("no-external-anatomy-variant-declared")
    for k in schema.get("required_model_evidence",[]):
        if candidate.get("evidence",{}).get(k)!="VERIFIED":
            errors.append("evidence-unverified:"+k)
    # This is a coverage admission gate only; no footage quality claim is possible.
    return {"status":"HOLD_UNVERIFIED" if errors else "PASS_MANIFEST_ONLY",
            "candidate":candidate.get("id","unnamed"),"errors":sorted(errors),
            "limits":["Feature tags cannot establish medical/anatomical quality",
                      "No mesh, film, or tissue simulation evaluated"]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--schema",type=Path,required=True)
    p.add_argument("--candidate",type=Path)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    schema=json.loads(a.schema.read_text())
    candidates=[json.loads(a.candidate.read_text())] if a.candidate else [
       {"id":c["id"],"age_class":c["age_class"],"active_reproductive_variants":["female","male"],
        "features":{},"evidence":{}} for c in schema["fixture_candidates"]]
    receipts=[assess(schema,c) for c in candidates]
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(receipts,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipts,indent=2,sort_keys=True))
    # Do not fail the research CI merely because an unqualified asset is correctly held.
    return 0
if __name__=="__main__":
    raise SystemExit(main())
