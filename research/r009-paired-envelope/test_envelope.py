import copy
import math
import unittest
from paired_envelope import audit, schedule, SCHEMA, MARKERS, SUB, load, unique

WINDOWS=[[50,70]]

def packet():
    return dict(schema=SCHEMA,source_class="ORIGINAL_SYNTHETIC",scene_sha256="a"*64,
        fps=60,subdiv=32,physical_contact_accepted=False,protected_likeness_used=False,
        rows=[dict(tick=t,actors={a:dict(markers={m:[0.,0.,1.] for m in MARKERS},
                 feet={s:{str(v):[0.,0.,0.] for v in range(4)} for s in ("L","R")})
                 for a in ("a","b")}) for t in schedule(WINDOWS)])

class Envelope(unittest.TestCase):
    def test_held_good_and_complete(self):
        a=packet();r=audit(a,a,WINDOWS)
        self.assertEqual(r["samples"],980)
        self.assertEqual(r["edges"],979)
        self.assertEqual(r["last_tick"],359*32)
        self.assertEqual(r["status"],"HOLD_DIAGNOSTIC_ONLY")
        self.assertFalse(r["physical_contact_accepted"])
    def test_body_and_other_foot_not_hidden_by_fixed_left(self):
        a=packet();b=copy.deepcopy(a)
        for row in b["rows"]:
            frame=row["tick"]/32
            shift=max(0.,1-abs(frame-60)/10)*.03
            body=row["actors"]["a"]
            body["markers"]["root"][0]=shift
            for v in body["feet"]["R"].values():v[0]=shift
        r=audit(a,b,WINDOWS)["actors"]["a"]
        self.assertAlmostEqual(r["feet"]["L"]["max_induced_displacement_m"]["value"],0)
        self.assertAlmostEqual(r["feet"]["R"]["max_induced_displacement_m"]["value"],.03)
        self.assertAlmostEqual(r["markers"]["root"]["max_induced_speed_mps"]["value"],.18)
        self.assertGreater(r["markers"]["root"]["max_induced_acceleration_mps2"]["value"],0)
        self.assertEqual(r["feet"]["R"]["outside_window_max_displacement_m"],0)
    def test_dropped_tail_or_duplicate_tick(self):
        a=packet();b=copy.deepcopy(a);b["rows"].pop()
        with self.assertRaisesRegex(ValueError,"DENOMINATOR"):audit(a,b,WINDOWS)
        b=copy.deepcopy(a);b["rows"][2]["tick"]=b["rows"][1]["tick"]
        with self.assertRaisesRegex(ValueError,"CLOCK"):audit(a,b,WINDOWS)
    def test_missing_offkey_sample(self):
        a=packet();b=copy.deepcopy(a);b["rows"].pop(51)
        with self.assertRaisesRegex(ValueError,"DENOMINATOR"):audit(a,b,WINDOWS)
    def test_bad_point_or_ids(self):
        a=packet();b=copy.deepcopy(a)
        b["rows"][0]["actors"]["a"]["markers"]["root"][0]=math.nan
        with self.assertRaisesRegex(ValueError,"XYZ"):audit(a,b,WINDOWS)
        b=copy.deepcopy(a)
        vertices=b["rows"][3]["actors"]["a"]["feet"]["R"];vertices["9"]=vertices.pop("0")
        with self.assertRaisesRegex(ValueError,"ID_DRIFT"):audit(a,b,WINDOWS)
    def test_missing_actor_or_foot_or_false_admission(self):
        a=packet();b=copy.deepcopy(a);b["rows"][1]["actors"].pop("b")
        with self.assertRaisesRegex(ValueError,"ACTOR_IDS"):audit(a,b,WINDOWS)
        b=copy.deepcopy(a);b["rows"][2]["actors"]["b"]["feet"].pop("L")
        with self.assertRaisesRegex(ValueError,"BILATERAL"):audit(a,b,WINDOWS)
        b=copy.deepcopy(a);b["protected_likeness_used"]=True
        with self.assertRaisesRegex(ValueError,"ADMISSION"):audit(a,b,WINDOWS)
    def test_bad_windows_and_duplicate_json(self):
        for w in ([[50,50]],[[50,70],[69,90]],[[0,360]],[[True,5]]):
            with self.assertRaises(ValueError):schedule(w)
        with self.assertRaisesRegex(ValueError,"DUPLICATE"):unique([("a",1),("a",2)])
if __name__=="__main__":unittest.main()
