"""Hostile 4.5/5.2 nine-channel wind-state/source matching tests, no physical admission."""
import copy,math,unittest
from pony_wind_state_interop import compare,SCHEMA
from pony_source_trajectory import classify
from test_pony_source_trajectory import fixture
NAMES=["wind_%03d"%i for i in range(1,10)]
def sample():
    s=fixture();sha=classify(s)["source_capsule_sha256"]
    a={"schema":SCHEMA,"source_kind":"original_synthetic","source_blend_sha256":s["source_blend_sha256"],
       "source_capsule_sha256":sha,"rig":"PonyRig30","frame_count":48,"source_surface":"geometric_coat_mane_tail",
       "wind_names":NAMES[:],"frames":[],"source_mutated_on_disk":False,"scientific_hold":"KEEP","release_admission":False}
    b={"schema":"equine.pony52.attached_original_groom_48f.v1","source_blend_sha256":s["source_blend_sha256"],
       "source_capsule_sha256":sha,"mode":"animation","modifier_mode":"Animation",
       "source_wind_morph_mode":"animated","source_surface":"geometric_coat_mane_tail",
       "source_surface_has_armature_skin":True,"curves_surface_binding_confirmed":True,
       "source_wind_morphs_detected":9,"source_wind_key_names":NAMES[:],
       "source_wind_effective_weights_per_frame":[],"frame_count":48,"guide_count":6,
       "status":"48F_ORIGINAL_SKIN_GROOM_NATIVE_GEOMETRY_OBSERVED","errors":[],
       "science_hold":"KEEP","release_admission":False,"full_body_collision_accepted":False,"frames":[]}
    for i in range(48):
        f=i+1;w=max(0.,math.sin(math.pi*i/47))
        weights=[w if k==3 else 0. for k in range(9)]
        src=[];native=[]
        for g in s["guides"]:
            root=g["samples"][i]["root_m"];shift=.04*w
            tip=[root[0]+shift,root[1],root[2]-.2]
            src.append({"card_id":g["card_id"],"region":g["region"],"root_m":root[:],"tip_m":tip[:]})
            native.append({"card_id":g["card_id"],"region":g["region"],"actual_root_m":root[:],"actual_tip_m":tip[:],
                "tip_minus_root_m":[shift,0.,-.2],"segment_surface_ray_hits":0})
        a["frames"].append({"frame":f,"wind_weights":weights,"guides":src})
        b["frames"].append({"frame":f,"guides":native})
        b["source_wind_effective_weights_per_frame"].append(weights[:])
    return s,a,b
class WindTests(unittest.TestCase):
    def test_positive_is_only_engineering(self):
        r=compare(*sample())
        self.assertEqual(r["verdict"],"SOURCE_WIND_ANIMATION_MATCHES_RIGID_52_ENGINEERING_ONLY")
        self.assertGreater(r["max_wind_effect_45_vs_skin_only_m_by_region"]["mane"],.03)
        self.assertEqual(r["scientific_hold"],"KEEP")
        self.assertFalse(r["release_or_CPE_admission"])
        self.assertEqual(r,compare(*sample()))
    def test_mismatch_science_hold(self):
        q=list(sample())
        for frame in q[2]["frames"]:
            for g in frame["guides"]:
                g["actual_tip_m"][0]+=.03;g["tip_minus_root_m"][0]+=.03
        self.assertEqual(compare(*q)["verdict"],"SOURCE_WIND_ANIMATION_CROSS_VERSION_DISCREPANCY_SCIENCE_HOLD")
    def test_wind_not_excited_is_inconclusive(self):
        q=list(sample())
        for f in q[1]["frames"]:f["wind_weights"]=[0.]*9
        for f in q[2]["source_wind_effective_weights_per_frame"]:f[:]=[0.]*9
        self.assertEqual(compare(*q)["verdict"],"INCONCLUSIVE_NO_ACTIVATED_WIND")
    def test_hostile_source_and_science_forgery(self):
        edits=[
            lambda x:x[0].update(source_kind="protected_person"),
            lambda x:x[1].update(source_capsule_sha256="f"*64),
            lambda x:x[1].update(source_mutated_on_disk=True),
            lambda x:x[1].update(release_admission=True),
            lambda x:x[1]["frames"].pop(),
            lambda x:x[1]["frames"][5].update(frame=4),
            lambda x:x[1]["frames"][6]["wind_weights"].__setitem__(0,float("nan")),
            lambda x:x[2]["source_wind_effective_weights_per_frame"][10].__setitem__(2,.5),
            lambda x:x[2]["frames"][5]["guides"].pop(),
            lambda x:x[2]["frames"][5]["guides"][0].update(card_id=999),
            lambda x:x[2]["frames"][0]["guides"][0].update(actual_root_m=[0,0,float("inf")]),
            lambda x:x[2]["frames"][0]["guides"][0].update(tip_minus_root_m=[1,0,0]),
            lambda x:x[2].update(science_hold="PASS"),
            lambda x:x[2].update(source_wind_morph_mode="disabled"),
            lambda x:x[2]["frames"][10]["guides"][0].update(segment_surface_ray_hits=-1)
        ]
        for i,edit in enumerate(edits):
            q=copy.deepcopy(sample());edit(q)
            with self.subTest(i=i),self.assertRaises((ValueError,TypeError,KeyError)):compare(*q)
if __name__=="__main__":unittest.main()
