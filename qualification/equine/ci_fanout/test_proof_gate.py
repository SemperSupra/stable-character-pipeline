import datetime as dt
import unittest
from proof_gate import (BASE_SHA, BRANCH, WORK, delta_is_irrelevant,
                        provider_proof, qualify)
HEAD = "b" * 40
OLD = "a" * 40
NOW = dt.datetime(2026, 11, 6, 14, 0, tzinfo=dt.timezone.utc)

def proof(workcell):
    run_id=10003
    r={"id":run_id,"event":"pull_request","status":"completed","conclusion":"success",
       "head_branch":BRANCH,"head_sha":OLD,"created_at":"2026-11-06T12:00:00Z",
       "pull_requests":[{"number":331,"head":{"sha":OLD},"base":{"sha":BASE_SHA}}]}
    jobs=[{"status":"completed","conclusion":"success"} for x in WORK[workcell][1]]
    arts=[{"name":name+str(run_id),"size_in_bytes":1234,"expired":False,"digest":"sha256:"+"f"*64}
          for name in WORK[workcell][1]]
    return r,jobs,arts

class Gate(unittest.TestCase):
    def test_disjoint_change_safe_not_unknown(self):
        self.assertTrue(delta_is_irrelevant("equine-ik-reachability", ["qualification/equine/av_observer/domain_guard_test.go"]))
        self.assertTrue(delta_is_irrelevant("equine-ik-axis-matrix", ["qualification/equine/finite_z/test_patch_limits.py"]))
        self.assertFalse(delta_is_irrelevant("equine-ik-axis-matrix", ["qualification/equine/ik_ab/rom30_native.py"]))
        self.assertFalse(delta_is_irrelevant("equine-ik-reachability", ["qualification/equine/ci_fanout/proof_gate.py"]))
        self.assertFalse(delta_is_irrelevant("equine-av-native-hoof-proxy", ["qualification/equine/av_observer/domain_guard.go"]))
        self.assertFalse(delta_is_irrelevant("equine-ik-reachability", ["README.md"]))
        self.assertFalse(delta_is_irrelevant("equine-ik-reachability", [".github/workflows/equine-ik-reachability.yml"]))
        self.assertFalse(delta_is_irrelevant("equine-ik-reachability", ["../forged"] ))
        self.assertFalse(delta_is_irrelevant("unknown", []))
    def test_native_proof_positive(self):
        for w in WORK:
            with self.subTest(w=w):
                r,j,a=proof(w)
                self.assertTrue(provider_proof(r,j,a,workcell=w,head=HEAD,base=BASE_SHA,now=NOW))
    def test_provider_negative_controls(self):
        w="equine-front-z-finite-matrix"
        r,j,a=proof(w)
        negatives=[lambda r,j,a:r.update(conclusion="failure"),
                   lambda r,j,a:r.update(event="push"),
                   lambda r,j,a:r.update(created_at="2026-10-01T00:00:00Z"),
                   lambda r,j,a:r["pull_requests"][0]["base"].update(sha="0"*40),
                   lambda r,j,a:r["pull_requests"][0].update(number=101),
                   lambda r,j,a:j[0].update(conclusion="skipped"),
                   lambda r,j,a:a[0].update(expired=True),
                   lambda r,j,a:a[0].update(digest="missing"),
                   lambda r,j,a:a[0].update(size_in_bytes=0),
                   lambda r,j,a:a.pop(),
                   lambda r,j,a:r.update(head_sha="f"*40)]
        import copy
        for i,mutate in enumerate(negatives):
            rr,jj,aa=copy.deepcopy((r,j,a))
            mutate(rr,jj,aa)
            self.assertFalse(provider_proof(rr,jj,aa,workcell=w,head=HEAD,base=BASE_SHA,now=NOW),i)
    def test_selection_positive_and_negative(self):
        w="equine-front-z-finite-matrix"
        r,j,a=proof(w)
        def api(path,token):
            if path.startswith("/actions/workflows/"):return {"workflow_runs":[r]}
            if path.endswith("/jobs?per_page=100"):return {"total_count":len(j),"jobs":j}
            if path.endswith("/artifacts?per_page=100"):return {"total_count":len(a),"artifacts":a}
            raise AssertionError(path)
        good=lambda *args:["qualification/equine/av_observer/domain_guard.go"]
        got=qualify(w,HEAD,BASE_SHA,"read-only",api=api,diff=good,now=NOW)
        self.assertFalse(got["run_native"])
        self.assertTrue(got["technical_evidence_only"])
        self.assertFalse(got["merge_or_release_authorized"])
        for changes in (["qualification/equine/finite_z/patch_limits.py"],["qualification/equine/ci_fanout/proof_gate.py"],["unknown.md"]):
            self.assertTrue(qualify(w,HEAD,BASE_SHA,"read-only",api=api,diff=lambda *args:changes,now=NOW)["run_native"])
        self.assertTrue(qualify(w,HEAD,"0"*40,"read-only",api=api,diff=good,now=NOW)["run_native"])
        self.assertTrue(qualify(w,HEAD,BASE_SHA,"",api=api,diff=good,now=NOW)["run_native"])
        self.assertTrue(qualify(w,HEAD,BASE_SHA,"read-only",api=lambda *a:1/0,diff=good,now=NOW)["run_native"])

if __name__ == "__main__":
    unittest.main()
