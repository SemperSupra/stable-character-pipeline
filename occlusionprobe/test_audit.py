import unittest
import numpy as np
import audit

def fixture():
    camera={"type":"PERSP","lens_mm":65.0,"sensor_width_mm":36.0,
            "resolution":[256,256],"shift_x":0.0,"shift_y":0.0}
    frames={}
    for i,case in enumerate(audit.CASES):
        rays=[]
        for j in range(64):
            ray_id=(3 if j<16 else 1) if case=="clear" else (
                (4 if j<8 else 3 if j<20 else 1) if case=="partial"
                else (4 if j<20 else 1))
            rays.append({
                "x":8+(j%8)*16,"y":8+(j//8)*16,
                "stable":True,"pass_index":ray_id,
                "camera_axis_depth":5.0,"ray_distance":5.2,
            })
        nocc=sum(x["pass_index"]==4 for x in rays)
        nhead=sum(x["pass_index"]==3 for x in rays)
        frames[case]={
            "case":case,"frame_index":i,
            "source_occluder_geometry":dict(audit.SOURCE_PARAMS[case]),
            "source_occluder_id":4,"source_head_id":3,
            "camera_sha256":audit.perspective.canonical_hash(camera),
            "source_geometry_sha256":str(i+1)*64,
            "stable_rays":64,
            "head_source_rays":nhead,
            "occluder_source_rays":nocc,
            "rays":rays,
            "files":{"beauty.png":{"sha256":"a"*64,"bytes":1234},
                     "render_passes.exr":{"sha256":"b"*64,"bytes":5678}},
        }
    return {
        "schema":"r075.original.synthetic.real-occlusion.v1",
        "status":"ACTUAL_SOURCE_OCCLUSION_PENDING_INDEPENDENT_EXR",
        "rights":"ORIGINAL_SYNTHETIC",
        "qualification":"NOT_REAL_PERSON_IDENTITY_OR_OCCLUSION_TRACKING",
        "source_scene_id":"original-synthetic-head-v1",
        "source_script_sha256":audit.sha(audit.ROOT/"renderlab"/"synthetic_scene.py"),
        "perspective_script_sha256":audit.sha(audit.ROOT/"perspprobe"/"scene.py"),
        "camera":camera,"camera_sha256":audit.perspective.canonical_hash(camera),
        "source_semantic_head_names":sorted({
            "head","nose","mouth","left-sclera","left-iris","left-pupil",
            "left-brow","left-ear","right-sclera","right-iris","right-pupil",
            "right-brow","right-ear"
        }),
        "source_semantic_head_id":3,
        "source_occluder_id":4,
        "source_motion_type":"KNOWN_STATIONARY_HEAD_MOVING_FOREGROUND_OCCLUDER",
        "cases":frames
    }

def positive_counts():
    return {"clear":{"head":6000,"occluder":0},
            "partial":{"head":3500,"occluder":2000},
            "severe":{"head":350,"occluder":8000}}

class TestRealExrOcclusionContract(unittest.TestCase):
    def test_valid_original_source_and_typed_expected_holds(self):
        frames=audit.validate(fixture())
        self.assertEqual(len(frames),3)
        decision=audit.classify_coverage(positive_counts())
        self.assertEqual(decision["partial"]["decision"],"HOLD_PARTIAL_OCCLUSION_NO_PERSON_ID")
        self.assertEqual(decision["severe"]["decision"],"HOLD_SEVERE_OCCLUSION_NO_PERSON_ID")

    def test_false_visibility_never_promoted_as_tracking(self):
        for mutate in (
            lambda m:m["partial"].update(head=6000),
            lambda m:m["partial"].update(head=100),
            lambda m:m["severe"].update(head=5800),
            lambda m:m["severe"].update(occluder=100),
            lambda m:m["clear"].update(occluder=200),
            lambda m:m["clear"].update(head=50),
            lambda m:m.pop("partial"),
        ):
            counts=positive_counts()
            mutate(counts)
            with self.assertRaises(ValueError):
                audit.classify_coverage(counts)

    def test_actual_pixel_index_nan_and_missing_mask_fail(self):
        pixels=np.zeros((256,256),dtype=np.float32)
        pixels[0:50,0:70]=3.0
        pixels[100:200,0:80]=4.0
        counts=audit.pixel_visibility(pixels)
        self.assertEqual(counts["head"],3500)
        self.assertEqual(counts["occluder"],8000)
        pixels[:]=np.nan
        self.assertEqual(audit.pixel_visibility(pixels)["head"],0)
        with self.assertRaises(ValueError):
            audit.pixel_visibility(np.zeros((64,64),dtype=np.float32))

    def test_source_rights_ray_camera_and_case_tamper_rejected(self):
        for mutate in (
            lambda m:m.update(rights="PROTECTED_FACE"),
            lambda m:m.update(qualification="REAL_PERSON_TRACKING_PASSED"),
            lambda m:m.update(source_script_sha256="f"*64),
            lambda m:m["camera"].update(lens_mm=35.0),
            lambda m:m["cases"]["partial"].update(case="severe"),
            lambda m:m["cases"]["severe"].update(source_occluder_geometry=m["cases"]["partial"]["source_occluder_geometry"]),
            lambda m:m["cases"]["severe"].update(source_geometry_sha256=m["cases"]["partial"]["source_geometry_sha256"]),
            lambda m:m["cases"]["partial"]["rays"][0].update(camera_axis_depth=float("nan")),
            lambda m:m["cases"]["partial"]["rays"][1].update(x=8,y=8),
            lambda m:m["cases"]["partial"].update(occluder_source_rays=0),
            lambda m:m["cases"].pop("clear"),
        ):
            m=fixture()
            mutate(m)
            with self.assertRaises(ValueError):
                audit.validate(m)

if __name__=="__main__":
    unittest.main()
