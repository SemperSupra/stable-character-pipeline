"""Independent hostile tests for original caudal bone/torso proximity."""
import copy
import math
import unittest
from test_pony_body_follicle_quality import sample
from pony_tail_bone_quality import check

def source():
    original,body=sample()
    guides=[g for g in original["guides"] if g["region"]=="tail"]
    rows=[]
    for g in guides:
        cards=[]
        for i in range(48):
            root=g["samples"][i]["root_m"]
            offsets={"tail_1":.03,"tail_2":.01 if g["owner_bone"]=="tail_2" else .012,
                     "tail_3":.012 if g["owner_bone"]=="tail_3" else .032}
            candidates=[{"bone":bone,"root_distance_to_bone_centerline_m":dist,
                        "bone_segment_fraction":.5,
                        "nearest_bone_centerline_point_m":[root[0]+dist,root[1],root[2]],
                        "bone_head_world_m":[root[0]+dist,root[1]-.05,root[2]],
                        "bone_tail_world_m":[root[0]+dist,root[1]+.05,root[2]]}
                        for bone,dist in sorted(offsets.items())]
            candidates.sort(key=lambda x:x["bone"])
            nearest=min(candidates,key=lambda x:(x["root_distance_to_bone_centerline_m"],x["bone"]))
            owner=next(c for c in candidates if c["bone"]==g["owner_bone"])
            cards.append({"frame":i+1,"source_root_m":root[:],
                          "closest_tail_bone":copy.deepcopy(nearest),
                          "source_owner_tail_bone":copy.deepcopy(owner),
                          "candidate_bone_distances":candidates})
        rows.append({"card_id":g["card_id"],"region":"tail","owner_bone":g["owner_bone"],
                     "frames":cards})
    from pony_source_trajectory import classify
    evidence={"schema":"equine.pony.original_caudal_bone_centerline_48f.v1",
              "source_blend_sha256":original["source_blend_sha256"],
              "source_capsule_sha256":classify(original)["source_capsule_sha256"],
              "source_kind":"original_synthetic","rig":"PonyRig30",
              "frames":48,"bone_names":["tail_1","tail_2","tail_3"],
              "tail_cards":rows,
              "bone_centerline_is_surface":False,
              "new_tail_shaft_generated":False,
              "source_roots_snapped_to_bones":False,
              "anatomical_acceptance":False,"scientific_hold":"KEEP",
              "release_or_CPE_admission":False}
    return original,body,evidence

class CaudalTests(unittest.TestCase):
    def test_caudal_bone_is_not_a_skin_surface(self):
        src,body,caudal=source()
        result=check(src,body,caudal)
        self.assertEqual(result["schema"],"equine.pony.source_caudal_bone_vs_rump_48f.v1")
        self.assertEqual(len(result["caudal_bone_centerline_distances"]),2)
        self.assertTrue(result["caudal_bone_centerline_distances"][0]["nearer_to_cauda_bone_than_tested_rump_at_rest"])
        self.assertTrue(result["bone_centerline_not_skinned_surface"])
        self.assertEqual(result["science_hold"],"KEEP")
        self.assertEqual(result,check(src,body,caudal))
    def test_hostile_tampered_source_bone_or_proximity(self):
        setup=source()
        modifications=[
            lambda a:a[2]["tail_cards"].pop(),
            lambda a:a[2]["tail_cards"][0].update(owner_bone="tail_3"),
            lambda a:a[2]["tail_cards"][0]["frames"].pop(),
            lambda a:a[2]["tail_cards"][0]["frames"][4].update(frame=4),
            lambda a:a[2]["tail_cards"][0]["frames"][4].update(source_root_m=[99,99,99]),
            lambda a:a[2]["tail_cards"][0]["frames"][4]["closest_tail_bone"].update(bone="fake"),
            lambda a:a[2]["tail_cards"][0]["frames"][4]["closest_tail_bone"].update(root_distance_to_bone_centerline_m=float("nan")),
            lambda a:a[2]["tail_cards"][0]["frames"][4]["closest_tail_bone"].update(nearest_bone_centerline_point_m=[0.,0.,0.]),
            lambda a:a[2]["tail_cards"][0]["frames"][4]["closest_tail_bone"].update(bone_segment_fraction=-.2),
            lambda a:a[2]["tail_cards"][0]["frames"][4]["candidate_bone_distances"].pop(),
            lambda a:a[2]["tail_cards"][0]["frames"][4]["candidate_bone_distances"][1].update(bone_head_world_m=[0.,0.,0.]),
            lambda a:a[2]["tail_cards"][0]["frames"][4]["candidate_bone_distances"][1].update(bone_tail_world_m=[float("inf"),0.,0.]),
            lambda a:a[2]["tail_cards"][0]["frames"][4]["candidate_bone_distances"][1].update(bone_segment_fraction=.3),
            lambda a:a[2]["tail_cards"][0]["frames"][4]["candidate_bone_distances"][1].update(nearest_bone_centerline_point_m=[0.,0.,0.]),
            lambda a:a[2]["tail_cards"][0]["frames"][4]["source_owner_tail_bone"].update(bone_head_world_m=[0.,0.,0.]),
            lambda a:a[2]["tail_cards"][0]["frames"][4]["source_owner_tail_bone"].update(bone="tail_1"),
            lambda a:a[2].update(bone_centerline_is_surface=True),
            lambda a:a[2].update(release_or_CPE_admission=True),
            lambda a:a[2].update(scientific_hold="PASS"),
            lambda a:a[1].update(source_blend_sha256="f"*64),
        ]
        for n,fn in enumerate(modifications):
            data=copy.deepcopy(setup);fn(data)
            with self.subTest(case=n):
                with self.assertRaises((ValueError,TypeError,KeyError)):
                    check(*data)
if __name__=="__main__":unittest.main()
