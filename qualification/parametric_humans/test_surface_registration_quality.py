"""Qualification of the synthetic surface-fit validator itself, not of anatomy or images.

The fixture classes are authored independently of fit_once's returned verdict,
so an always-accept or always-reject validator cannot silently pass.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import time
import unittest

from surface_registration_v1 import SCHEMA, FitRejected, fit_once
from test_surface_registration_v1 import fixture


def digest(value):
    raw=json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def cases():
    rows=[]
    def add(name,want,change=None,offset=.04):
        data=fixture(offset)
        if change: change(data)
        rows.append((name,want,data))
    add("admitted-normal-positive","ACCEPT")
    add("admitted-normal-negative","ACCEPT",offset=-.03)
    add("clipped-large-target-abstain","ABSTAIN",offset=.4)
    add("low-confidence-abstain","ABSTAIN",lambda d:d["correspondences"][0].update(confidence=.1))
    add("held-vertex-abstain","ABSTAIN",lambda d:d["correspondences"][0].update(status="HOLD"))
    add("unknown-schema","REJECT",lambda d:d.update(schema="unknown"))
    add("disallowed-step","REJECT",lambda d:d["options"].update(max_normal_step_m=.9))
    add("zero-normal","REJECT",lambda d:d["normals"].__setitem__(0,[0.,0.,0.]))
    add("invalid-triangle","REJECT",lambda d:d["triangles"].__setitem__(0,[0,0,1]))
    add("clothing-is-not-body","REJECT",lambda d:d["correspondences"][0].update(surface="CLOTHING"))
    add("boolean-tangent-is-not-distance","REJECT",lambda d:d["options"].update(max_tangent_step_m=False))
    add("text-metric-step-is-not-admitted","REJECT",lambda d:d["options"].update(max_tangent_step_m="0.02"))
    add("nonnumeric-coordinate","REJECT",lambda d:d["vertices"][0].__setitem__(0,"nan"))
    return rows


def classify(document,validator=fit_once):
    try:
        output=validator(document)
    except FitRejected:
        return "REJECT"
    except Exception:
        return "ERROR"
    if not isinstance(output,dict) or output.get("qualification")!="SYNTHETIC_GEOMETRIC_CONTRACT_ONLY" or output.get("motion_accepted") is not False or output.get("identity_accepted") is not False:
        return "ERROR"
    stats=output.get("stats",{})
    if any(stats.get(k,0)>0 for k in ("held","unknown","clamped")):
        return "ABSTAIN"
    return "ACCEPT"


def score(validator=fit_once):
    items=cases()
    matrix={label:{outcome:0 for outcome in ("ACCEPT","ABSTAIN","REJECT","ERROR")} for label in ("ACCEPT","ABSTAIN","REJECT","ERROR")}
    results=[]
    durations=[]
    for name,expected,document in items:
        start=time.perf_counter_ns()
        observed=classify(document,validator)
        elapsed=time.perf_counter_ns()-start
        durations.append(elapsed)
        matrix[expected][observed]+=1
        results.append({"id":name,"expected":expected,"actual":observed,"input_sha256":digest(document),"elapsed_ns":elapsed})
    mistakes=sum(x["expected"]!=x["actual"] for x in results)
    false_accept=sum(x["expected"]!="ACCEPT" and x["actual"]=="ACCEPT" for x in results)
    fail_reject=sum(x["expected"]=="ACCEPT" and x["actual"]!="ACCEPT" for x in results)
    ordered=sorted(durations)
    return {
        "schema":"scp.validator.performance.v1",
        "validator":"scp.original_human.synthetic_surface_registration",
        "validator_sha256":hashlib.sha256(Path(__file__).with_name("surface_registration_v1.py").read_bytes()).hexdigest(),
        "corpus":"scp.synthetic_surface_fit.hostile.v2",
        "corpus_sha256":digest([{"id":n,"expected":w,"source":digest(d)} for n,w,d in items]),
        "source_class":"QUAD_SYNTHETIC_NO_REAL_PHOTOGRAPH",
        "case_count":len(items),"confusion":matrix,
        "rejection_detection":{"detected":matrix["REJECT"]["REJECT"],"total":sum(x["expected"]=="REJECT" for x in results)},
        "false_acceptance_count":false_accept,"false_rejection_count":fail_reject,
        "hard_error_count":sum(x["actual"]=="ERROR" for x in results),
        "contract_mismatch_count":mistakes,
        "runtime":{"python":platform.python_version(),"latency_p50_ns":ordered[len(ordered)//2],
                   "latency_p95_ns":ordered[(len(ordered)*95+99)//100-1]},
        "cases":results,
        "external_photo_fit":"NOT_RUN","anatomical_motion_quality":"UNKNOWN",
        "verdict":"PASS_SYNTHETIC_VALIDATOR_CONTROLS_ONLY" if not mistakes else "FAIL_VALIDATOR_CONTROLS",
        "merge_release_CPE_approval":False
    }


class SurfaceValidatorPerformance(unittest.TestCase):
    def test_quality_and_emit_receipt(self):
        report=score()
        self.assertEqual(report["case_count"],13)
        self.assertEqual(report["rejection_detection"],{"detected":8,"total":8})
        self.assertEqual(report["confusion"]["ABSTAIN"]["ABSTAIN"],3)
        self.assertEqual(report["false_acceptance_count"],0)
        self.assertEqual(report["false_rejection_count"],0)
        self.assertEqual(report["contract_mismatch_count"],0)
        self.assertEqual(report["verdict"],"PASS_SYNTHETIC_VALIDATOR_CONTROLS_ONLY")
        path=os.getenv("SCP_VALIDATOR_PERF_OUT")
        if path:
            Path(path).write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")

    def test_meta_oracle_that_accepts_everything_is_detected(self):
        def accept_all(document):
            return {"qualification":"SYNTHETIC_GEOMETRIC_CONTRACT_ONLY",
                    "motion_accepted":False,"identity_accepted":False,"stats":{}}
        report=score(validator=accept_all)
        self.assertEqual(report["false_acceptance_count"],11)
        self.assertEqual(report["contract_mismatch_count"],11)

    def test_meta_oracle_that_rejects_everything_is_detected(self):
        def reject_all(document):
            raise FitRejected("broken")
        report=score(validator=reject_all)
        self.assertEqual(report["false_rejection_count"],2)
        self.assertEqual(report["contract_mismatch_count"],5)

    def test_corpus_does_not_mutate_its_fixtures(self):
        source=fixture()
        before=copy.deepcopy(source)
        self.assertEqual(source,before)
        self.assertEqual(len(set(c[0] for c in cases())),13)


if __name__=="__main__":
    unittest.main()
