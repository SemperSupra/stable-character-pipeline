import copy
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
import audit

def fixture():
    depth=np.full((256,256),8.0,dtype=np.float32)
    index=np.full((256,256),1.0,dtype=np.float32)
    rays=[]
    for k in range(64):
        x=8+16*(k%8)
        y=8+16*(k//8)
        rays.append({"x":x,"y":y,"stable":True,"pass_index":1,
                     "depth_from_camera_plane":8.0,
                     "geometric_normal":[0.,0.,1.],
                     "object_name":"original-synthetic-head"})
    return rays,{"depth":{"Z":depth},"object":{"X":index}}

class TestR045DepthReprojection(unittest.TestCase):
    def test_matching_native_rays(self):
        rays,data=fixture()
        result=audit.compare_known_rays(rays,data)
        self.assertEqual(result["native_stable_rays"],64)
        self.assertEqual(result["joint_correct"],64)

    def test_wrong_depth_fail_closed(self):
        rays,data=fixture()
        for r in rays[:3]:data["depth"]["Z"][r["y"],r["x"]]+=0.20
        with self.assertRaisesRegex(ValueError,"CAMERA_DEPTH_OR_OBJECT"):
            audit.compare_known_rays(rays,data)

    def test_wrong_object_id_fail_closed(self):
        rays,data=fixture()
        for r in rays[:3]:data["object"]["X"][r["y"],r["x"]]=2.
        with self.assertRaisesRegex(ValueError,"CAMERA_DEPTH_OR_OBJECT"):
            audit.compare_known_rays(rays,data)

    def test_nan_depth_rejected(self):
        rays,data=fixture()
        for r in rays[:3]:data["depth"]["Z"][r["y"],r["x"]]=np.nan
        with self.assertRaisesRegex(ValueError,"CAMERA_DEPTH_OR_OBJECT"):
            audit.compare_known_rays(rays,data)

    def test_missing_rays_and_dimensions(self):
        rays,data=fixture()
        with self.assertRaisesRegex(ValueError,"INSUFFICIENT"):
            audit.compare_known_rays(rays[:10],data)
        data["depth"]["Z"]=data["depth"]["Z"][:8]
        with self.assertRaisesRegex(ValueError,"INVALID_EXR_SHAPE"):
            audit.compare_known_rays(rays,data)

    def test_duplicate_json_and_nonfinite(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"manifest.json"
            for payload in ('{"a":1,"a":2}', '{"a":NaN}'):
                p.write_text(payload,encoding="utf-8")
                with self.assertRaises(ValueError):audit.strict_json(p)

    def test_source_known_stability_uses_correct_pixel(self):
        rays,data=fixture()
        # One deliberate source-flagged silhouette sample is excluded;
        # approval must still be based on >=64 independently stable rays.
        rays[0]["stable"]=False
        with self.assertRaisesRegex(ValueError,"INSUFFICIENT"):
            audit.compare_known_rays(rays,data)

if __name__=="__main__":
    unittest.main()
