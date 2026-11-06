import copy
import math
import unittest
from pony_skin_frame_quality import assess
from test_pony_source_trajectory import fixture
from test_pony52_actual_surface_native import measured
from pony_source_trajectory import classify as source_gate

def setup():
    c=fixture()
    gate=source_gate(c)
    a=measured(c,"animation")
    cards=[]
    for guide in c["guides"]:
        frames=[]
        for index,item in enumerate(guide["samples"]):
            root=item["root_m"][:];tip=item["tip_m"][:]
            frames.append({"frame":index+1,"source_root_m":root,"source_tip_m":tip,
              "bone_transport_predicted_root_m":root[:],"bone_transport_predicted_tip_m":tip[:],
              "bone_transport_delta_quat_wxyz":[1.,0.,0.,0.],
              "source_bone_transport_root_error_m":0.,"source_bone_transport_tip_error_m":0.})
        cards.append({"card_id":guide["card_id"],"region":guide["region"],
                      "owner_bone":guide["owner_bone"],"frames":frames})
    f={"schema":"equine.pony.source_skin_bone_frame_48f.v1",
       "source_blend_sha256":c["source_blend_sha256"],
       "source_capsule_sha256":gate["source_capsule_sha256"],
       "source_kind":"original_synthetic","rig":"PonyRig30","frame_count":48,"cards":cards,
       "bone_transport_proof":"rest-to-pose source rig matrix, world-space",
       "wind_morphs_disabled":True,"scientific_hold":"KEEP",
       "hair_material_accepted":False,"release_or_CPE_admission":False}
    a["rest_capture_order"]="armature_then_capture"
    return c,f,a

class BoneFrameTests(unittest.TestCase):
    def test_known_source_bone_vs_wrong_rigid_frame_not_release(self):
        c,f,a=setup()
        r=assess(c,f,a)
        self.assertEqual(r["hypothesis"],"BONE_TRANSPORT_MATCHES_SOURCE_RIGID_52_SURFACE_FRAME_DRIFTS")
        self.assertGreater(r["regions"]["mane"]["native_rigid"]["max_m"],.03)
        self.assertLess(r["regions"]["mane"]["bone_tip"]["max_m"],.00001)
        self.assertFalse(r["rest_frame_attachment_and_tangent_calibrated"])
        self.assertFalse(r["release_or_CPE_admission"])
        self.assertEqual(r,assess(c,f,a))
    def test_bone_reconstruction_error_must_be_visible(self):
        c,f,a=setup()
        for record in f["cards"]:
            for frame in record["frames"][1:]:
                frame["bone_transport_predicted_tip_m"][0]+=.02
                frame["source_bone_transport_tip_error_m"]=.02
        r=assess(c,f,a)
        self.assertEqual(r["hypothesis"],"SOURCE_BONE_TRANSPORT_ITSELF_NOT_VERIFIED")
    def test_forged_observer_source_and_controls_fail_closed(self):
        inputs=setup()
        mutations=[
          lambda x:x[1]["cards"].pop(),
          lambda x:x[1]["cards"][0].update(owner_bone="fictional_bone"),
          lambda x:x[1]["cards"][0]["frames"].pop(),
          lambda x:x[1]["cards"][0]["frames"][6].update(frame=6),
          lambda x:x[1]["cards"][0]["frames"][6].update(source_tip_m=[1.,1.,1.]),
          lambda x:x[1]["cards"][0]["frames"][6].update(source_bone_transport_tip_error_m=100.),
          lambda x:x[1]["cards"][0]["frames"][6].update(bone_transport_delta_quat_wxyz=[0.,0.,0.,0.]),
          lambda x:x[1]["cards"][0]["frames"][6].update(bone_transport_predicted_root_m=[float("nan"),0.,0.]),
          lambda x:x[1].update(wind_morphs_disabled=False),
          lambda x:x[1].update(hair_material_accepted=True),
          lambda x:x[2].update(mode="physics"),
          lambda x:x[2]["frames"][6]["guides"][0].update(tip_minus_root_m=[math.inf,0.,0.]),
          lambda x:x[2].update(source_blend_sha256="f"*64),
        ]
        for n,modify in enumerate(mutations):
            args=list(copy.deepcopy(inputs));modify(args)
            with self.subTest(mutation=n):
                with self.assertRaises((ValueError,KeyError,TypeError)):assess(*args)
if __name__=="__main__":unittest.main()
