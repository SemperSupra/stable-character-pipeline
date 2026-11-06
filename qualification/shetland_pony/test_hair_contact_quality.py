import math
import unittest
from hair_contact_quality import classify,FRAMES,REGION_CARDS,OBSTACLES

def sample(frames=(1,2),bad=None):
    rows=[]
    for f in frames:
        for region,obstacles in OBSTACLES.items():
            for obs in obstacles:
                crossing=bad==(f,region,obs)
                rows.append({"frame":f,"region":region,"obstacle":obs,
                             "face_pairs":2 if crossing else 0,
                             "card_count":1 if crossing else 0,
                             "tip_samples":REGION_CARDS[region],
                             "tips_within_5mm":3 if crossing else 0,
                             "min_tip_distance_m":.002 if crossing else .012})
    return rows

class HairContactQualityTests(unittest.TestCase):
    def test_true_crossing_positive_and_scientific_hold(self):
        key=(2,"tail","continuous_hind_L_limb")
        r=classify(sample(bad=key),frames=(1,2))
        self.assertEqual(r["regions"]["tail"]["possible_collision_frame_count"],1)
        self.assertEqual(r["regions"]["tail"]["obstacle_contacts"][key[2]]["first_candidate_frame"],2)
        self.assertEqual(r["candidate_collision"],"POSSIBLE_CROSSING")
        self.assertEqual(r["scientific_hold"],"KEEP")
        self.assertFalse(r["visual_acceptance"])
        self.assertFalse(r["release_or_CPE_admission"])
    def test_fully_clean_not_promoted(self):
        r=classify(sample(),frames=(1,2))
        self.assertEqual(r["candidate_collision"],"NO_TRIANGLE_CROSSING_OBSERVED")
        self.assertFalse(r["visual_acceptance"])
        self.assertEqual(r,classify(sample(),frames=(1,2)))
    def test_hostile_missing_duplicate_and_false_witness(self):
        original=sample()
        cases=[original[:-1],original+[original[0]]]
        for case in cases:
            with self.assertRaises(ValueError):classify(case,frames=(1,2))
        for change in ({"card_count":1},{"min_tip_distance_m":math.nan},
                       {"tips_within_5mm":1},{"frame":3},{"tip_samples":1},
                       {"face_pairs":-1},{"tip_samples":True},
                       {"min_tip_distance_m":-.02}):
            rows=sample();rows[0]={**rows[0],**change}
            with self.subTest(change=str(change)):
                with self.assertRaises(ValueError):classify(rows,frames=(1,2))
    def test_no_silent_missing_regions_or_obstacles(self):
        rows=sample(); rows=[x for x in rows if x["region"]!="forelock"]
        with self.assertRaises(ValueError):classify(rows,frames=(1,2))
        with self.assertRaises(ValueError):classify(sample(),frames=(2,1))
        with self.assertRaises(ValueError):classify(sample(),frames=(1,1))
if __name__=="__main__":unittest.main()
