"""Independently falsify fake glTF animation existence and single-timestamp channels."""
import copy
import math
import struct
import unittest
from w4d_liveness import liveness,decode_glb

def fixture():
    binary=bytearray()
    views=[];accessors=[]
    def pack(rows,kind):
        offset=len(binary)
        width={"SCALAR":1,"VEC4":4}[kind]
        for row in rows:
            binary.extend(struct.pack("<"+"f"*width,*row))
        views.append({"buffer":0,"byteOffset":offset,"byteLength":len(rows)*width*4})
        accessors.append({"bufferView":len(views)-1,"componentType":5126,"type":kind,"count":len(rows)})
        return len(accessors)-1
    times=[(i/12,) for i in range(24)]
    ids=[]
    for actor in range(2):
        ti=pack(times,"SCALAR")
        rotations=[(math.sin(i/20+actor/10),0,0,math.cos(i/20+actor/10)) for i in range(24)]
        qi=pack(rotations,"VEC4")
        ids.append((ti,qi))
    nodes=[{"name":f"actor{ai}_{i}" } for ai in range(2) for i in range(6)]
    nodes[1]["name"]="LeftLower"
    nodes[7]["name"]="LeftLower.001"
    doc={"asset":{"version":"2.0"},"nodes":nodes,
         "skins":[{"joints":list(range(0,6))},{"joints":list(range(6,12))}],
         "bufferViews":views,"accessors":accessors,
         "animations":[{"samplers":[{"input":ids[i][0],"output":ids[i][1],"interpolation":"LINEAR"}],
                        "channels":[{"sampler":0,"target":{"node":[1,7][i],"path":"rotation"}}]}
                       for i in range(2)]}
    receipt={"schema":"scp.walk_w4d_native_24frame_smoke.v1",
             "rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
             "frame_count":24,"fps_num":12,"glb_sha256":"f"*64}
    return doc,bytes(binary),receipt

class LivenessTests(unittest.TestCase):
    def test_two_native_glb_skin_actors_24_real_samples(self):
        d,b,r=fixture()
        out=liveness(d,b,r)
        self.assertEqual(out["moving_skin_actors"],[0,1])
        self.assertEqual(out["status"],"PASS_SYNTHETIC_GLB_24FRAME_LOWER_BONE_LIVENESS_ONLY")
        self.assertEqual(out["human_anatomy"],"UNKNOWN_UNAPPROVED")
    def test_false_animation_objects_with_one_timestamp_abstain(self):
        d,b,r=fixture()
        for a in d["accessors"]:a["count"]=1
        with self.assertRaisesRegex(ValueError,"NO_REAL_24FRAME"):
            liveness(d,b,r)
    def test_wrong_bone_target_must_not_count(self):
        d,b,r=fixture();d["animations"][0]["channels"][0]["target"]["node"]=0
        with self.assertRaisesRegex(ValueError,"NO_REAL_24FRAME"):
            liveness(d,b,r)
    def test_fake_timestamp_count_does_not_override_actual_buffer(self):
        d,b,r=fixture();d["accessors"][0]["count"]=25
        with self.assertRaisesRegex(ValueError,"BUFFER_VIEW_BOUNDS"):
            liveness(d,b,r)
    def test_duplicate_clock_rejected(self):
        d,b,r=fixture()
        data=bytearray(b);struct.pack_into("<f",data,4,0.0)
        with self.assertRaisesRegex(ValueError,"ANIMATED_CLOCK"):
            liveness(d,bytes(data),r)
    def test_rights_are_not_promoted(self):
        d,b,r=fixture();r["rights"]="RIGHTS_UNKNOWN"
        with self.assertRaisesRegex(ValueError,"SOURCE_RIGHTS"):
            liveness(d,b,r)
    def test_no_second_actor_motion_rejected(self):
        d,b,r=fixture();d["animations"][1]["channels"][0]["target"]["node"]=1
        with self.assertRaisesRegex(ValueError,"NO_REAL_24FRAME"):
            liveness(d,b,r)
    def test_invalid_glb_no_fake_passing(self):
        with self.assertRaisesRegex(ValueError,"GLB_BYTES_OR_MAGIC"):
            decode_glb(b"not a glb")
if __name__=="__main__":unittest.main()
