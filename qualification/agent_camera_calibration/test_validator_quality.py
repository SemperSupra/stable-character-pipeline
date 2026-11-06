"""Read-only adversarial and coordinate-metamorphic camera-oracle qualification.

Native synthetic declared two-camera correspondences only; not a real photo
or extrinsics authenticity claim. The independent expected outcomes are
defined here, not computed from the candidate validator's result.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import time
import unittest

from calibration import AdmissionError, assess
from test_calibration import fixture


def digest(value):
    raw=json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def cases():
    result=[]
    def put(name,expected,change=None,budget=1.):
        rows=fixture()
        if change is not None:
            rows=change(rows) or rows
        result.append((name,expected,rows,budget))
    put("baseline-admitted-synthetic","ACCEPT")
    put("permutation-of-observation-order","ACCEPT",lambda rows: list(reversed(rows)))
    def move_principal(rows):
        for r in rows:
            r["uv"][0]+=20.
            r["uv"][1]+=10.
        return rows
    put("translated-pixel-origin","ACCEPT",move_principal)
    def change_resolution(rows):
        for r in rows:
            r["uv"]=[2*v for v in r["uv"]]
            r["size"]=[2*v for v in r["size"]]
        return rows
    put("double-image-resolution","ACCEPT",change_resolution)
    def heldout_drift(rows):
        for r in rows:
            if r["view"]=="front" and r["role"]=="heldout":
                r["uv"][0]+=5.
        return rows
    put("heldout-reprojection-regression","REJECT",heldout_drift)
    put("capture-family-leakage","REJECT",lambda rows:rows[6].update(family=rows[0]["family"]))
    put("heldout-image-duplicate","REJECT",lambda rows:rows[6].update(image_sha256=rows[0]["image_sha256"]))
    put("extrinsics-digest-swap","REJECT",lambda rows:rows[0].update(extrinsics_sha256="3"*64))
    put("nonnumeric-depth","REJECT",lambda rows:rows[0]["xyz"].__setitem__(2,"NaN"))
    put("negative-depth","REJECT",lambda rows:rows[0]["xyz"].__setitem__(2,-1.))
    put("single-view-only","REJECT",lambda rows:[r for r in rows if r["view"]=="front"])
    put("out-of-image-pixel","REJECT",lambda rows:rows[0]["uv"].__setitem__(0,999999))
    put("unbounded-error-budget","REJECT",budget=999.)
    put("duplicate-source-point","REJECT",lambda rows:rows[1].update(point_id=rows[0]["point_id"]))
    put("bad-source-hash","REJECT",lambda rows:rows[0].update(source_sha256="invalid"))
    put("missing-train-features","REJECT",lambda rows:[r for r in rows if r["point_id"] not in ("front:0","front:1","front:2")])
    return result


def classify(rows,budget,oracle=assess):
    try:
        decision=oracle(rows,max_heldout_error_px=budget)
    except AdmissionError:
        return "REJECT"
    except Exception:
        return "ERROR"
    if not isinstance(decision,dict) or decision.get("external_photo_fit")!="NOT_RUN" or decision.get("independent_extrinsics")!="NOT_PROVEN" or decision.get("character_anatomy")!="UNKNOWN" or decision.get("release_or_CPE_admission") is not False:
        return "ERROR"
    if decision.get("geometry")=="PASS_DECLARED_SYNTHETIC_ONLY":
        return "ACCEPT"
    if decision.get("geometry")=="FAIL_HELDOUT_REPROJECTION":
        return "REJECT"
    return "ERROR"


def measure(oracle=assess):
    data=cases()
    labels=("ACCEPT","ABSTAIN","REJECT","ERROR")
    confusion={e:{a:0 for a in labels} for e in labels}
    entries=[]
    elapsed=[]
    for label,want,rows,budget in data:
        start=time.perf_counter_ns()
        got=classify(rows,budget,oracle)
        duration=time.perf_counter_ns()-start
        confusion[want][got]+=1
        entries.append({"id":label,"expected":want,"actual":got,"source_sha256":digest(rows),
                        "error_budget":budget,"elapsed_ns":duration})
        elapsed.append(duration)
    wrong=sum(int(r["expected"]!=r["actual"]) for r in entries)
    positives=sum(r["expected"]=="ACCEPT" for r in entries)
    reject_count=sum(r["expected"]=="REJECT" for r in entries)
    sorted_elapsed=sorted(elapsed)
    return {"schema":"scp.validator.performance.v1","validator":"scp.synthetic_camera_declared_intrinsics",
            "validator_sha256":hashlib.sha256(Path(__file__).with_name("calibration.py").read_bytes()).hexdigest(),
            "corpus":"scp.camera_intrinsics_declared_metavalidator.v1",
            "corpus_sha256":digest([{"id":n,"expected":w,"source_sha256":digest(r),"budget":b} for n,w,r,b in data]),
            "source_class":"DECLARED_SYNTHETIC_CAMERA_COORDINATES",
            "case_count":len(data),"confusion":confusion,
            "rejection_detection":{"detected":confusion["REJECT"]["REJECT"],"total":reject_count},
            "expected_accepted":positives,
            "false_acceptance_count":sum(r["expected"]!="ACCEPT" and r["actual"]=="ACCEPT" for r in entries),
            "false_rejection_count":sum(r["expected"]=="ACCEPT" and r["actual"]!="ACCEPT" for r in entries),
            "hard_error_count":sum(r["actual"]=="ERROR" for r in entries),
            "contract_mismatch_count":wrong,
            "runtime":{"python":platform.python_version(),"latency_p50_ns":sorted_elapsed[(len(data)-1)//2],
                      "latency_p95_ns":sorted_elapsed[(len(data)*95+99)//100-1]},
            "cases":entries,
            "external_photo_fit":"NOT_RUN","extrinsics_authenticity":"UNKNOWN",
            "decision":"PASS_DECLARED_SYNTHETIC_ORACLE_CONTROLS_ONLY" if wrong==0 else "FAIL_ORACLE_CONTROLS",
            "merge_release_CPE_approval":False}


class CameraValidatorQuality(unittest.TestCase):
    def test_quality_measured_and_archived(self):
        r=measure()
        self.assertEqual(r["case_count"],16)
        self.assertEqual(r["expected_accepted"],4)
        self.assertEqual(r["rejection_detection"],{"detected":12,"total":12})
        self.assertEqual(r["contract_mismatch_count"],0)
        self.assertEqual(r["false_acceptance_count"],0)
        self.assertEqual(r["false_rejection_count"],0)
        self.assertEqual(r["decision"],"PASS_DECLARED_SYNTHETIC_ORACLE_CONTROLS_ONLY")
        out=os.environ.get("SCP_CAMERA_VALIDATOR_PERF_OUT")
        if out:
            Path(out).write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")

    def test_metamorphic_camera_intrinsics(self):
        base=assess(fixture())
        shifted=next(rows for name,_,rows,_ in cases() if name=="translated-pixel-origin")
        doubled=next(rows for name,_,rows,_ in cases() if name=="double-image-resolution")
        a=assess(shifted)
        b=assess(doubled)
        for initial,move,scale in zip(base["views"],a["views"],b["views"]):
            self.assertEqual(initial["view"],move["view"])
            self.assertAlmostEqual(move["cx_px"],initial["cx_px"]+20,places=4)
            self.assertAlmostEqual(move["cy_px"],initial["cy_px"]+10,places=4)
            self.assertAlmostEqual(scale["fx_px"],initial["fx_px"]*2,places=4)
            self.assertAlmostEqual(scale["fy_px"],initial["fy_px"]*2,places=4)
            self.assertAlmostEqual(scale["cx_px"],initial["cx_px"]*2,places=4)
            self.assertAlmostEqual(scale["cy_px"],initial["cy_px"]*2,places=4)

    def test_broken_oracle_detected(self):
        accepted={"geometry":"PASS_DECLARED_SYNTHETIC_ONLY",
                  "external_photo_fit":"NOT_RUN","independent_extrinsics":"NOT_PROVEN",
                  "character_anatomy":"UNKNOWN","release_or_CPE_admission":False}
        always_accept=measure(oracle=lambda rows,max_heldout_error_px:copy.deepcopy(accepted))
        self.assertEqual(always_accept["false_acceptance_count"],12)
        self.assertEqual(always_accept["contract_mismatch_count"],12)
        rejected={**accepted,"geometry":"FAIL_HELDOUT_REPROJECTION"}
        always_reject=measure(oracle=lambda rows,max_heldout_error_px:copy.deepcopy(rejected))
        self.assertEqual(always_reject["false_rejection_count"],4)
        self.assertEqual(always_reject["contract_mismatch_count"],4)

    def test_case_names_unique_and_original_fixture_stays_unchanged(self):
        src=fixture()
        before=copy.deepcopy(src)
        data=cases()
        self.assertEqual(src,before)
        self.assertEqual(len(data),len({name for name,_,_,_ in data}))


if __name__=="__main__":
    unittest.main()
