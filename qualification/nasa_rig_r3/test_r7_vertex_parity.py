"""Synthetic falsifiers for strict R7 numerical parity (zero source media/model)."""
import copy
import math
import unittest

from r7_vertex_parity import compare, matches_bijective, transform

def specimen():
    verts=[[0.0,0.0,0.0],[1.0,2.0,.05],[.3,.4,-.01]]
    verts=verts + [[float(k)/500,float(k)/1000,0.0] for k in range(3,192)]
    g={"frames":[{"source_second":13+i,"vertices":[v.copy() for v in verts]} for i in range(10)]}
    b={"frames":[{"source_second":13+i,"vertices":[list(transform(v)) for v in verts]} for i in range(10)]}
    return g,b

class StrictReadback(unittest.TestCase):
    def test_exact_transformation(self):
        g,b=specimen()
        r=compare(g,b)
        self.assertEqual(r["status"],"PASS_INDEXED_VERTEX_PARITY")
        self.assertEqual(r["max_indexed_error_camera_plane_units"],0)
        self.assertEqual(r["sample_count"],10)
    def test_reordered_but_same_multiset_not_index(self):
        g,b=specimen()
        b["frames"][2]["vertices"][0],b["frames"][2]["vertices"][1]=b["frames"][2]["vertices"][1],b["frames"][2]["vertices"][0]
        r=compare(g,b)
        self.assertEqual(r["status"],"PASS_POINT_SET_PARITY_INDEX_MAP_UNPROVEN")
        self.assertFalse(r["all_indexed"])
    def test_mutated_position_must_fail(self):
        g,b=specimen()
        b["frames"][5]["vertices"][6][1]+=.01
        r=compare(g,b)
        self.assertEqual(r["status"],"FAIL_NUMERIC_VERTEX_PARITY")
    def test_basis_tamper_must_fail(self):
        g,b=specimen()
        for f in b["frames"]:
            for v in f["vertices"]:
                v[1],v[2]=v[2],v[1]
        self.assertEqual(compare(g,b)["status"],"FAIL_NUMERIC_VERTEX_PARITY")
    def test_missing_time_rejected(self):
        g,b=specimen()
        b["frames"].pop()
        with self.assertRaises(ValueError):compare(g,b)
    def test_one_vertex_not_reused_for_two(self):
        a=[(0,0,0),(.0001,0,0)]
        b=[(0,0,0),(1,0,0)]
        self.assertFalse(matches_bijective(a,b,.0005))
    def test_wider_tolerance_rejected(self):
        g,b=specimen()
        with self.assertRaises(ValueError):compare(g,b,.001)

if __name__=="__main__":
    unittest.main()
