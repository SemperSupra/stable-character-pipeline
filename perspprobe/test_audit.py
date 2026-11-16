import copy
import json
import tempfile
import unittest
import numpy as np
from pathlib import Path

import audit


def fixture():
    source_sha=audit.sha(audit.SOURCE)
    original_geom="a"*64
    cases={}
    for label,lens in audit.LENS_VALUES.items():
        camera={
            "type":"PERSP",
            "lens_mm":lens,
            "sensor_width_mm":36.0,
            "sensor_fit":"HORIZONTAL",
            "shift_x":0.0,
            "shift_y":0.0,
            "clip_start":0.1,
            "clip_end":100.0,
            "world_matrix":[1.0,0,0,0,0,1.0,0,0,0,0,1.0,0,0,0,0,1.0],
            "resolution":[256,256],
            "pixel_aspect":[1.0,1.0],
        }
        rays=[]
        for i in range(64):
            rays.append({
                "x":8+16*(i%8),
                "y":8+16*(i//8),
                "stable":True,
                "pass_index":1,
                "ray_distance":5.5,
                "camera_axis_depth":5.0,
                "geometric_normal":[0.0,0.0,1.0],
                "object_name":"fixture-original-head",
            })
        files={
            "beauty.png":{"sha256":"b"*64,"bytes":1024},
            "render_passes.exr":{"sha256":"c"*64,"bytes":2048},
        }
        cases[label]={
            "camera":camera,
            "camera_sha256":audit.canonical_hash(camera),
            "source_geometry_sha256":original_geom,
            "ray_sample_count":len(rays),
            "stable_count":len(rays),
            "rays":rays,
            "arms":{"baseline":copy.deepcopy(files),
                    "physical_material":copy.deepcopy(files)}
        }
    return {
        "schema":"r057.perspective.native.v1",
        "status":"PERSPECTIVE_SOURCE_RAY_CAPTURED_PENDING_EXR_CRITIC",
        "rights":"ORIGINAL_SYNTHETIC",
        "qualification":"NOT_PHOTOREALISM_OR_PRIVATE_HUMAN_EVIDENCE",
        "source_scene_id":"original-synthetic-head-v1",
        "source_script_sha256":source_sha,
        "geometry_sha256":original_geom,
        "resolution":256,
        "lenses":cases,
    }

class TestPerspectiveNativeCameraIdentity(unittest.TestCase):
    def test_original_synthetic_positive_contract(self):
        m=fixture()
        assert len(audit.validate_manifest(m))==2

    def test_false_material_owner_rights_and_source_hash(self):
        for key,value in [
            ("rights","PERSON_PROTECTED"),
            ("qualification","ACTUAL_OWNER_PHOTOREAL"),
            ("source_script_sha256","0"*64),
            ("status","PROMOTED"),
        ]:
            m=fixture()
            m[key]=value
            with self.subTest(key=key):
                with self.assertRaises(ValueError):audit.validate_manifest(m)

    def test_wrong_lens_and_cross_lens_geometry(self):
        for mutate in [
            lambda m:m["lenses"]["lens_35"]["camera"].update(lens_mm=65.0),
            lambda m:m["lenses"]["lens_35"]["camera"].update(shift_x=0.4),
            lambda m:m["lenses"]["lens_65"].update(source_geometry_sha256="d"*64),
            lambda m:m["lenses"]["lens_65"]["camera"].update(type="ORTHO"),
            lambda m:m["lenses"]["lens_65"]["camera"].update(pixel_aspect=[1.0,0.9]),
        ]:
            m=fixture()
            mutate(m)
            with self.assertRaises(ValueError):audit.validate_manifest(m)

    def test_rays_fail_closed_on_nan_duplicate_and_id_swap(self):
        for mutate in [
            lambda m:m["lenses"]["lens_35"]["rays"][0].update(camera_axis_depth=float("nan")),
            lambda m:m["lenses"]["lens_35"]["rays"][0].update(ray_distance=4.5),
            lambda m:m["lenses"]["lens_35"]["rays"][0].update(pass_index=99),
            lambda m:m["lenses"]["lens_35"]["rays"][0].update(stable="false"),
            lambda m:m["lenses"]["lens_35"]["rays"][1].update(x=8,y=8),
            lambda m:m["lenses"]["lens_35"]["rays"][1].update(geometric_normal=[0.0,0.0,0.0]),
        ]:
            m=fixture()
            mutate(m)
            with self.assertRaises(ValueError):audit.validate_manifest(m)

    def test_perspective_axes_must_differ_from_ray_distance(self):
        m=fixture()
        for lens in ("lens_35","lens_65"):
            for r in m["lenses"][lens]["rays"]:
                r["ray_distance"]=r["camera_axis_depth"]
        with self.assertRaisesRegex(ValueError,"UNTESTED_PERSPECTIVE_RAY_VS_AXIS"):
            audit.validate_manifest(m)

    def test_incomplete_material_matrix_rejected(self):
        m=fixture()
        del m["lenses"]["lens_65"]["arms"]["physical_material"]
        with self.assertRaises(ValueError):audit.validate_manifest(m)

    def test_numeric_axial_source_positive_and_reject_wrong_depth(self):
        m=fixture()
        rays=m["lenses"]["lens_35"]["rays"]
        pix={"depth":{"Z":np.full((256,256),5.0,dtype=np.float32)},
             "object":{"X":np.full((256,256),1.0,dtype=np.float32)}}
        result=audit.compare_axial_depth(rays,pix)
        self.assertEqual(result["joint_correct"],64)
        self.assertEqual(result["max_abs_axial_depth_error_among_correct"],0)
        for r in rays[:3]:
            pix["depth"]["Z"][r["y"],r["x"]]=5.2
        with self.assertRaisesRegex(ValueError,"REAL_EXR_AXIAL_DEPTH"):
            audit.compare_axial_depth(rays,pix)

    def test_numeric_axial_index_swap_and_nan_fail_closed(self):
        m=fixture()
        rays=m["lenses"]["lens_65"]["rays"]
        for mutation in ("index_swap","nonfinite_depth"):
            pix={"depth":{"Z":np.full((256,256),5.0,dtype=np.float32)},
                 "object":{"X":np.full((256,256),1.0,dtype=np.float32)}}
            for r in rays[:3]:
                if mutation=="index_swap":
                    pix["object"]["X"][r["y"],r["x"]]=2.0
                else:
                    pix["depth"]["Z"][r["y"],r["x"]]=np.nan
            with self.subTest(mutation=mutation):
                with self.assertRaisesRegex(ValueError,"REAL_EXR_AXIAL_DEPTH"):
                    audit.compare_axial_depth(rays,pix)

    def test_strict_json_dupes_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"fake.json"
            p.write_text('{"foo":1,"foo":2}',encoding="utf-8")
            with self.assertRaises(ValueError):audit.ortho.strict_json(p)

if __name__=="__main__":
    unittest.main()
