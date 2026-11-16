import copy
import unittest
import numpy as np
import audit

def fixture():
    camera={
      "type":"PERSP","lens_mm":65.0,"sensor_width_mm":36.0,
      "resolution":[256,256],"shift_x":0.0,"shift_y":0.0
    }
    rays=[]
    for i in range(64):
        rays.append({"x":8+16*(i%8),"y":8+16*(i//8),
                     "stable":True,"pass_index":1,
                     "geometric_normal":[0.0,0.0,1.0]})
    files={"beauty.png":{"sha256":"a"*64,"bytes":1024},
           "render_passes.exr":{"sha256":"b"*64,"bytes":2048}}
    return {
        "schema":"r059.original.synthetic.shading_normals.v1",
        "status":"NATIVE_GEOMETRY_CAPTURE_PENDING_INDEPENDENT_EXR",
        "rights":"ORIGINAL_SYNTHETIC",
        "qualification":"NOT_REAL_HUMAN_PHYSICS_OR_ANATOMY",
        "scene_id":"original-synthetic-head-v1",
        "source_script_sha256":audit.sha(audit.ORIGINAL),
        "perspective_script_sha256":audit.sha(audit.PERSPECTIVE),
        "geometry_sha256":"c"*64,
        "camera":camera,
        "camera_sha256":audit.persp.canonical_hash(camera),
        "source_stable_samples":64,
        "source_rays":rays,
        "arms":{"baseline":copy.deepcopy(files),
                "physical_material":copy.deepcopy(files)}
    }

def exr_normals():
    return {k:np.zeros((256,256),dtype=np.float32) if k!="Z" else
            np.ones((256,256),dtype=np.float32) for k in "XYZ"}

class TestOriginalNormalPass(unittest.TestCase):
    def test_valid_original_source_contract_and_normal_orientation(self):
        rays,_=audit.validate(fixture())
        r=audit.analyze_normal(rays,exr_normals())
        self.assertEqual(r["finite_unit_length"],64)
        self.assertEqual(r["facing_native_source"],64)

    def test_reverse_normals_fails(self):
        rays,_=audit.validate(fixture())
        p=exr_normals()
        for r in rays[:12]:
            p["Z"][r["y"],r["x"]]=-1.0
        with self.assertRaisesRegex(ValueError,"NORMAL_PASS_DISAGREES"):
            audit.analyze_normal(rays,p)

    def test_nan_and_zero_normals_fail(self):
        rays,_=audit.validate(fixture())
        for v in (float("nan"),0.0):
            p=exr_normals()
            for r in rays[:4]:
                p["Z"][r["y"],r["x"]]=v
            with self.assertRaisesRegex(ValueError,"INVALID_FINITE_UNIT_NORMALS"):
                audit.analyze_normal(rays,p)

    def test_corrupt_metadata_fails_closed(self):
        for mutate in (
            lambda m:m.update(rights="UNKNOWN_PERSON"),
            lambda m:m.update(qualification="REAL_SHADING_NORMAL_TRUTH"),
            lambda m:m.update(source_script_sha256="0"*64),
            lambda m:m["camera"].update(lens_mm=35.0),
            lambda m:m["source_rays"][0].update(geometric_normal=[0,0,0]),
            lambda m:m["source_rays"][1].update(x=8,y=8),
            lambda m:m["source_rays"][0].update(stable="true"),
        ):
            m=fixture()
            mutate(m)
            with self.assertRaises(ValueError):
                audit.validate(m)

    def test_reject_incomplete_control_pair(self):
        m=fixture()
        del m["arms"]["physical_material"]
        with self.assertRaisesRegex(ValueError,"INCOMPLETE_MATERIALS"):
            audit.validate(m)

if __name__=="__main__":
    unittest.main()
