"""Falsifiable source-exact five-row/six-point distributed-wind witness tests."""
import copy
import math
import unittest
from pony_source_trajectory import classify
from test_pony_wind_groom_transfer import setup
from pony_wind_centerline_oracle import (compare,new_row_receipt,new_curve_receipt,
    sampled_index,sampled_arclength,arc)

def fixtures():
    skin,source45,bare52,curves=setup()
    row45=new_row_receipt(skin,"4.5.15",source45["wind_names"])
    row52=new_row_receipt(skin,"5.2.3",bare52["wind_names"])
    points=new_curve_receipt(skin,curves["source_wind_key_names"])
    for f in range(48):
        for original,trace in ((source45,row45),(bare52,row52)):
            row=[]
            for g in original["frames"][f]["guides"]:
                root=g["root_m"];tip=g["tip_m"]
                samples=[[root[k]*(1-j/4)+tip[k]*j/4 for k in range(3)] for j in range(5)]
                row.append({"card_id":g["card_id"],"region":g["region"],"points_world_m":samples})
            trace["frames"].append({"frame":f+1,"wind_weights":original["frames"][f]["wind_weights"][:],"guides":row})
        rows=[]
        for g in curves["frames"][f]["guides"]:
            root=g["actual_root_m"];tip=g["actual_tip_m"]
            samples=[[root[k]*(1-j/5)+tip[k]*j/5 for k in range(3)] for j in range(6)]
            g["curve_polyline_length_m"]=arc(samples)
            rows.append({"card_id":g["card_id"],"region":g["region"],"points_world_m":samples})
        points["frames"].append({"frame":f+1,
            "wind_weights":curves["source_wind_effective_weights_per_frame"][f][:],
            "guides":rows})
    return skin,source45,bare52,curves,row45,row52,points

class CenterlineTests(unittest.TestCase):
    def test_clean_staged_geometry_is_only_engineering_pass(self):
        q=compare(*fixtures())
        self.assertEqual(q["verdict"],"INDEX_LINEAR_SOURCE_POINTS_MATCH_CURVE_ENGINEERING_ONLY")
        self.assertEqual(q["scientific_hold"],"KEEP")
        self.assertFalse(q["release_or_CPE_admission"])
        self.assertEqual(q["source_52_to_curve_52_index_resampled_point_p95_m_by_region"]["mane"],0.)
        self.assertEqual(q,compare(*fixtures()))
    def test_centerline_source_disagreement_cannot_hide_in_matching_root_tip(self):
        q=fixtures()
        for row in q[5]["frames"]:
            for g in row["guides"]:
                g["points_world_m"][2][0]+=.06
        a=compare(*q)
        self.assertEqual(a["verdict"],"FIVE_ROW_ORIGINAL_SOURCE_DIFFERS_ACROSS_BLENDER_VERSIONS_HOLD")
        self.assertGreater(a["original_45_to_bare_52_five_row_relative_p95_m_by_region"]["tail"],.04)
    def test_distributed_curve_bending_lost_but_root_and_tip_same(self):
        q=fixtures()
        for row in q[6]["frames"]:
            for g in row["guides"]:
                for j in range(1,5):g["points_world_m"][j][1]+=.05*math.sin(math.pi*j/5)
                guide=next(x for x in q[3]["frames"][row["frame"]-1]["guides"] if x["card_id"]==g["card_id"])
                guide["curve_polyline_length_m"]=arc(g["points_world_m"])
        a=compare(*q)
        self.assertEqual(a["verdict"],"DISTRIBUTED_FIVE_ROW_TO_SIX_CURVE_TRANSFER_DIFFERENCE_SCIENCE_HOLD")
        self.assertGreater(a["source_52_to_curve_52_index_resampled_point_p95_m_by_region"]["mane"],.02)
        self.assertEqual(a["source_52_to_curve_52_root_max_m_by_region"]["mane"],0.)
    def test_index_and_arclength_reparam_do_not_match_unconditionally(self):
        points=[(0,0,0),(.01,0,0),(.04,0,0),(.09,0,0),(.3,0,0)]
        self.assertGreater(math.dist(sampled_index(points)[2],sampled_arclength(points)[2]),.02)
        self.assertAlmostEqual(arc(points),.3)
    def test_hostile_abi_and_forged_points(self):
        attackers=[
            lambda x:x[4].update(source_blend_sha256="a"*64),
            lambda x:x[4].update(release_admission=True),
            lambda x:x[5].update(original_blender_version="4.5.15"),
            lambda x:x[6].update(mode="physics"),
            lambda x:x[6].update(scientific_hold="PASS"),
            lambda x:x[5]["frames"].pop(),
            lambda x:x[5]["frames"][9].update(frame=8),
            lambda x:x[4]["frames"][2]["guides"][0].update(card_id=999),
            lambda x:x[5]["frames"][9]["guides"][0]["points_world_m"].pop(),
            lambda x:x[6]["frames"][8]["guides"][1]["points_world_m"][1].__setitem__(2,float("nan")),
            lambda x:x[6]["frames"][8]["guides"][1]["points_world_m"][1].__setitem__(2,500.),
            lambda x:x[5]["frames"][3]["wind_weights"].__setitem__(1,.8),
            lambda x:x[6]["frames"][3]["guides"][0]["points_world_m"][0].__setitem__(0,12),
            lambda x:x[6]["frames"][3]["guides"][0]["points_world_m"][-1].__setitem__(0,12),
            lambda x:x[3]["frames"][0]["guides"][0].update(curve_polyline_length_m=0.)
        ]
        for i,attack in enumerate(attackers):
            data=copy.deepcopy(fixtures());attack(data)
            with self.subTest(i=i),self.assertRaises((ValueError,TypeError,KeyError)):
                compare(*data)

if __name__=="__main__":unittest.main()
