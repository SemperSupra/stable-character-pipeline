"""Hostile source-independent caudal line-projection tests."""
import math
import unittest
from caudal_segment_oracle import verify

ROOT=[0.,0.,0.]
def row():
    return {"bone":"tail_2","bone_head_world_m":[.03,-.07,0.],
        "bone_tail_world_m":[.03,.07,0.],
        "nearest_bone_centerline_point_m":[.03,0.,0.],
        "bone_segment_fraction":.5,"root_distance_to_bone_centerline_m":.03}
class TestOracle(unittest.TestCase):
    def test_true_projection(self):
        self.assertAlmostEqual(verify(ROOT,row()),.03)
    def test_endpoint_projection(self):
        q=row();root=[.03,-.08,0.]
        q["nearest_bone_centerline_point_m"]=[.03,-.07,0.]
        q["bone_segment_fraction"]=0.
        q["root_distance_to_bone_centerline_m"]=.01
        self.assertAlmostEqual(verify(root,q),.01)
    def test_hostiles(self):
        attacks=[lambda q:q.update(bone_head_world_m=[.03,-.05,0.]),
            lambda q:q.update(bone_tail_world_m=[.03,.01,0.]),
            lambda q:q.update(bone_segment_fraction=.6),
            lambda q:q.update(nearest_bone_centerline_point_m=[.03,.01,0.]),
            lambda q:q.update(root_distance_to_bone_centerline_m=.09),
            lambda q:q.update(bone_head_world_m=[math.nan,-.07,0.]),
            lambda q:q.update(bone_tail_world_m=[.03,-.07,0.]),
            lambda q:q.update(extra="forged"),
            lambda q:q.update(bone_segment_fraction=True),
            lambda q:q.update(root_distance_to_bone_centerline_m=-.03)]
        for n,mut in enumerate(attacks):
            q=row();mut(q)
            with self.subTest(n=n), self.assertRaises(ValueError):
                verify(ROOT,q)
if __name__=="__main__":unittest.main()
