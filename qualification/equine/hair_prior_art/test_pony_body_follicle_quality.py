import copy
import math
import unittest
from pony_body_follicle_quality import evaluate
from pony_source_trajectory import classify
from pony52_actual_surface_native import REGION_TARGETS
from test_pony_source_trajectory import fixture

def sample():
    source=fixture()
    gate=classify(source)
    cards=[]
    for guide in source["guides"]:
        root=guide["samples"][0]["root_m"]
        body=REGION_TARGETS[guide["region"]][0]
        projected=[root[0],root[1],root[2]-.02]
        anchor={"source_body_object":body,"rest_triangle_index":0,
                "rest_triangle_vertex_ids":[0,1,2],
                "rest_barycentric":[.2,.3,.5],
                "rest_projection_m":projected[:],"rest_root_to_skin_distance_m":.02,
                "rest_normal_m":[0.,0.,1.],"rest_root_minus_anchor_m":[0.,0.,.02]}
        frames=[]
        for index,item in enumerate(guide["samples"]):
            r=item["root_m"]
            closest=[r[0],r[1],r[2]-.02]
            frames.append({"frame":index+1,"source_root_m":r[:],
                "nearest_body_object":body,"nearest_face_index":0,
                "nearest_face_vertex_ids":[0,1,2],
                "nearest_barycentric":[.2,.3,.5],
                "nearest_body_point_m":closest,
                "nearest_surface_normal":[0.,0.,1.],
                "nearest_unsigned_distance_m":.02,"normal_directional_offset_m":.02,
                "rest_persistent_anchor_point_m":projected[:],
                "rest_anchor_current_unsigned_distance_m":.02,
                "world_fixed_offset_drift_m":0.})
        cards.append({"card_id":guide["card_id"],"region":guide["region"],
                      "owner_bone":guide["owner_bone"],"frames":frames,"rest_anchor":anchor})
    result={"schema":"equine.pony.original_body_follicle_projection_48f.v1",
            "source_blend_sha256":source["source_blend_sha256"],
            "source_capsule_sha256":gate["source_capsule_sha256"],
            "source_kind":"original_synthetic","rig":"PonyRig30",
            "source_original_body_mesh_count":5,
            "source_mesh_names":sorted(set(x for group in REGION_TARGETS.values() for x in group)),
            "frame_count":48,"guide_count":6,"cards":cards,
            "body_closed_volume_validated":False,
            "nearest_geometry_is_signed_inside_outside":False,
            "original_source_roots_snapped":False,
            "projection_admitted_as_animated_follicle":False,
            "visual_scientific_hold":"KEEP","release_or_CPE_admission":False}
    return source,result

class ProjectionTests(unittest.TestCase):
    def test_unsnapped_original_body_follicle_is_not_accepted(self):
        src,obs=sample()
        r=evaluate(src,obs)
        self.assertEqual(r["frames"],48)
        self.assertEqual(r["guides"],6)
        self.assertEqual(r["regions"]["mane"]["sample_count"],96)
        self.assertEqual(r["regions"]["mane"]["nearest_root_to_body_p95_m"],.02)
        self.assertEqual(r["regions"]["tail"]["nearest_face_changes_from_rest_count"],0)
        self.assertFalse(r["candidate_is_retargetable"])
        self.assertFalse(r["normal_directional_offset_is_signed_volume"])
        self.assertEqual(r["science_hold"],"KEEP")
        self.assertEqual(r,evaluate(src,obs))
    def test_articulated_face_changes_are_observations_not_accepted(self):
        src,obs=sample()
        # New face observation does not itself imply movement of the
        # persistent source f1 triangle or an accepted new body follicle.
        g=obs["cards"][0]["frames"][10]
        g["nearest_face_index"]=4
        r=evaluate(src,obs)
        self.assertEqual(r["regions"]["mane"]["nearest_face_changes_from_rest_count"],1)
        self.assertFalse(r["candidate_is_retargetable"])
    def test_provenance_barycentric_forgery_and_bad_source_fail_closed(self):
        src,obs=sample()
        mutations=[
            lambda a:a["cards"].pop(),
            lambda a:a["cards"][0].update(card_id=750),
            lambda a:a["cards"][0]["rest_anchor"].update(rest_barycentric=[.2,.2,.2]),
            lambda a:a["cards"][0]["rest_anchor"].update(rest_triangle_vertex_ids=[0,0,2]),
            lambda a:a["cards"][0]["rest_anchor"].update(rest_root_to_skin_distance_m=0.),
            lambda a:a["cards"][0]["rest_anchor"].update(source_body_object="ground"),
            lambda a:a["cards"][0]["frames"].pop(),
            lambda a:a["cards"][0]["frames"][2].update(frame=2),
            lambda a:a["cards"][0]["frames"][2].update(source_root_m=[0,0,100]),
            lambda a:a["cards"][0]["frames"][2].update(nearest_unsigned_distance_m=float("nan")),
            lambda a:a["cards"][0]["frames"][2].update(nearest_surface_normal=[0,0,0]),
            lambda a:a["cards"][0]["frames"][2].update(nearest_barycentric=[2,0,-1]),
            lambda a:a["cards"][0]["frames"][2].update(rest_anchor_current_unsigned_distance_m=.8),
            lambda a:a["cards"][0]["frames"][2].update(world_fixed_offset_drift_m=.5),
            lambda a:a.update(source_original_body_mesh_count=4),
            lambda a:a.update(original_source_roots_snapped=True),
            lambda a:a.update(body_closed_volume_validated=True),
            lambda a:a.update(visual_scientific_hold="PASS"),
            lambda a:a.update(release_or_CPE_admission=True),
        ]
        for n,mutate in enumerate(mutations):
            with self.subTest(case=n):
                a=copy.deepcopy(obs);mutate(a)
                with self.assertRaises((ValueError,KeyError,TypeError)):
                    evaluate(src,a)

if __name__=="__main__":unittest.main()
