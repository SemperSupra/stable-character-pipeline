#!/usr/bin/env python3
"""Independent analytic CSG oracle for original public-safe geometry fixtures."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def signed_box(xyz, half):
    q = [abs(v)-h for v,h in zip(xyz,half)]
    return math.sqrt(sum(max(v,0.0)**2 for v in q))+min(max(q),0.0)


def reference(xyz):
    sphere = math.sqrt(sum(v*v for v in xyz))-1.0
    box = signed_box(xyz,[1.4,0.25,0.25])
    return min(sphere,box)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(fixture_path, results):
    fixture = json.loads(fixture_path.read_text())
    points = fixture["points"]
    output = {"schema":"procedural-sdf-bakeoff-receipt/v1",
              "fixture_sha256":sha256(fixture_path),"donors":{},
              "status":"PASS"}
    failures = []
    for donor,path in results:
        data = json.loads(path.read_text())
        errors = []
        if data.get("donor") != donor:
            errors.append("donor_identity_mismatch")
        if data.get("invalid_rejected") is not True:
            errors.append("zero_radius_not_rejected")
        cases = data.get("cases",[])
        if len(cases) != len(points):
            errors.append("count_mismatch")
        max_error = 0.0
        tol = fixture["tolerances"][donor]
        for expected,got in zip(points,cases):
            if got.get("id") != expected["id"] or got.get("xyz") != expected["xyz"]:
                errors.append("point_mismatch")
                continue
            d = got.get("distance")
            if not isinstance(d,(int,float)) or not math.isfinite(d):
                errors.append("nonfinite_distance")
                continue
            diff = abs(d-reference(expected["xyz"]))
            max_error = max(max_error,diff)
            if diff > tol:
                errors.append("numeric_error:"+expected["id"])
        output["donors"][donor]={"sha256":sha256(path),"cases":len(cases),
                                 "tolerance":tol,"max_abs_error":max_error,
                                 "status":"PASS" if not errors else "FAIL",
                                 "errors":sorted(set(errors))}
        if errors: failures.append(donor)
    if len(results) != 2 or set(x[0] for x in results) != {"gsdf","sdfx"}:
        failures.append("missing_donor")
    if failures:
        output["status"]="FAIL"
        output["failed"]=sorted(set(failures))
    return output


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parent)
    args=parser.parse_args()
    root=args.root
    files=[("sdfx",root/"results/sdfx.json"),("gsdf",root/"results/gsdf.json")]
    receipt=verify(root/"fixture.json",files)
    (root/"results").mkdir(exist_ok=True)
    (root/"results/oracle-receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,sort_keys=True))
    raise SystemExit(0 if receipt["status"]=="PASS" else 1)


if __name__=="__main__":
    main()
