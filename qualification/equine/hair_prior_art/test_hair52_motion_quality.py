import copy
import hashlib
import json
import math
import unittest
from hair52_motion_quality import evaluate

SHA="0"*64
def receipt(mode):
    a={"schema":"equine.blender52.dynamic.original_synthetic.v1","blender":"5.2.3 LTS",
       "source_sha256":SHA,"control_mode":mode,"frame_count":48,"frames_requested":48,
       "production_blender_4_5_15_untouched":True,"source_and_release_hold":"KEEP",
       "visual_collision_quality":"UNKNOWN","errors":[],
       "mode_control":{"after":"Physics (Experimental)" if mode=="physics" else "Animation"},
       "verdict":"EXPERIMENTAL_48F_MOTION_OBSERVED_NOT_SCIENTIFIC_ACCEPTANCE" if mode=="physics" else "CONTROL_RIGID_FOLLOW_CONFIRMED",
       "samples":[]}
    for i in range(48):
        f=i+1
        x=.2*math.sin(math.pi*i/47)
        a["samples"].append({"frame":f,"scalp_world_x_m":x,
          "root_world_m":[[x+o,0.,.5] for o in (-.045,0.,.045)],
          "tip_world_m":[[x+o-(.12*math.sin(math.pi*i/47) if mode=="physics" else 0),0.,.8] for o in (-.045,0.,.045)],
          "tip_minus_root_m":[[-.12*math.sin(math.pi*i/47) if mode=="physics" else 0,0.,.3] for _ in range(3)]})
    return a
class PairTests(unittest.TestCase):
    def test_positive_and_holds(self):
        a,b=receipt("physics"),receipt("animation")
        r=evaluate(a,b)
        self.assertEqual(r["verdict"],"PAIRED_NATIVE_SECONDARY_MOTION_ENGINEERING_OBSERVED")
        self.assertEqual(r["measured_samples"],48)
        self.assertFalse(r["physical_material_calibrated"])
        self.assertFalse(r["merge_release_CPE"])
        self.assertEqual(r,evaluate(a,b))
    def test_forged_source_and_negative_control(self):
        a,b=receipt("physics"),receipt("animation")
        b["source_sha256"]="1"*64
        with self.assertRaises(ValueError):evaluate(a,b)
        b=receipt("animation")
        b["samples"][20]["tip_world_m"][1][0]+=0.1
        with self.assertRaises(ValueError):evaluate(a,b)
    def test_forged_timeline_nonfinite_and_missing(self):
        a,b=receipt("physics"),receipt("animation")
        for alteration in (lambda x:x["samples"].pop(),
                           lambda x:x["samples"][20].update(frame=19),
                           lambda x:x["samples"][10]["tip_world_m"][0].__setitem__(2,float("nan")),
                           lambda x:x["samples"][20].update(scalp_world_x_m=float("inf"))):
            clone=copy.deepcopy(a)
            alteration(clone)
            with self.assertRaises(ValueError):
                evaluate(clone,b)
    def test_no_motion_is_not_simulation(self):
        a,b=receipt("physics"),receipt("animation")
        for row in a["samples"]:
            row["tip_minus_root_m"]=[[0,0,.3] for _ in range(3)]
            row["tip_world_m"]=[[x[0],x[1],x[2]+.3] for x in row["root_world_m"]]
        with self.assertRaises(ValueError):evaluate(a,b)
    def test_severe_strain_rejected(self):
        a,b=receipt("physics"),receipt("animation")
        for row in a["samples"][1:]:
            row["tip_minus_root_m"]=[[0,0,.65] for _ in range(3)]
            row["tip_world_m"]=[[x[0],x[1],x[2]+.65] for x in row["root_world_m"]]
        with self.assertRaises(ValueError):evaluate(a,b)
if __name__=="__main__":unittest.main()
