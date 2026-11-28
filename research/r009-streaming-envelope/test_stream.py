import copy
import io
import json
import math
import unittest
from stream_envelope import audit_stream
from paired_envelope import audit, schedule, MARKERS, SCHEMA

WINDOWS=[[50,53],[62,64]]
def packets(vertices=4):
    header=dict(schema=SCHEMA,source_class="ORIGINAL_SYNTHETIC",scene_sha256="a"*64,
        fps=60,subdiv=32,physical_contact_accepted=False,protected_likeness_used=False)
    a={**header,"rows":[]};b={**header,"scene_sha256":"b"*64,"rows":[]}
    for tick in schedule(WINDOWS):
        row={"tick":tick,"actors":{actor:{"markers":{m:[tick/100000,0,1] for m in MARKERS},
            "feet":{side:{str(i):[i*.001,tick/100000,0] for i in range(vertices)} for side in ("L","R")}}
            for actor in ("a","b")}}
        a["rows"].append(row)
        q=copy.deepcopy(row)
        for m in q["actors"]["a"]["markers"].values():m[0]+=.03*math.sin(tick/200)
        for v in q["actors"]["a"]["feet"]["R"].values():v[1]+=.01*math.cos(tick/150)
        b["rows"].append(q)
    return a,b
def encode(p):
    return ("\n".join(json.dumps(x,separators=(",",":")) for x in
        [{k:v for k,v in p.items() if k!="rows"},*p["rows"]])+"\n").encode()
def check(a,b):
    return audit_stream(io.BytesIO(encode(a)),io.BytesIO(encode(b)),WINDOWS)

class Stream(unittest.TestCase):
    def test_exact_batch_parity_nonuniform_clock_and_ties(self):
        a,b=packets();self.assertEqual(check(a,b),audit(a,b,WINDOWS))
    def test_no_lost_tail(self):
        a,b=packets();b["rows"].pop()
        with self.assertRaisesRegex(ValueError,"DENOMINATOR"):check(a,b)
    def test_extra_sample(self):
        a,b=packets();b["rows"].append(b["rows"][-1])
        with self.assertRaisesRegex(ValueError,"EXTRA_SAMPLES"):check(a,b)
    def test_duplicate_and_nonfinite_json(self):
        a,b=packets();raw=encode(a).replace(b'"fps":60',b'"fps":60,"fps":60',1)
        with self.assertRaisesRegex(ValueError,"DUPLICATE"):audit_stream(io.BytesIO(raw),io.BytesIO(encode(b)),WINDOWS)
        b["rows"][0]["actors"]["a"]["markers"]["root"][0]=math.inf
        with self.assertRaisesRegex(ValueError,"NONFINITE"):check(a,b)
    def test_clock_and_identity(self):
        a,b=packets();b["rows"][10]["tick"]=b["rows"][9]["tick"]
        with self.assertRaisesRegex(ValueError,"CLOCK"):check(a,b)
        a,b=packets();verts=b["rows"][5]["actors"]["a"]["feet"]["L"];verts["99"]=verts.pop("0")
        with self.assertRaisesRegex(ValueError,"IDS"):check(a,b)
    def test_joint_layout_change_both_packets(self):
        a,b=packets()
        for p in (a,b):
            v=p["rows"][5]["actors"]["a"]["feet"]["L"];v["99"]=v.pop("0")
        with self.assertRaisesRegex(ValueError,"ID_DRIFT"):check(a,b)
    def test_line_budget_and_protected_source(self):
        a,b=packets()
        with self.assertRaisesRegex(ValueError,"LINE_BUDGET"):audit_stream(io.BytesIO(encode(a)),io.BytesIO(encode(b)),WINDOWS,1024)
        b["protected_likeness_used"]=True
        with self.assertRaisesRegex(ValueError,"ADMISSION"):check(a,b)
if __name__=="__main__":unittest.main()
