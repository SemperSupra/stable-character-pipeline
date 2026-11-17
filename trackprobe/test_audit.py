import copy
import unittest

import numpy as np
import audit

def make_mask(start):
    arr=np.zeros((256,256),dtype=np.float32)
    arr[40:70,start:start+30]=3.0
    return arr

def fixture():
    cam={"type":"PERSP","lens_mm":65.0,"sensor_width_mm":36.0,
         "resolution":[256,256],"shift_x":0.0,"shift_y":0.0}
    frames={}
    for i,(key,delta) in enumerate(audit.OFFSETS.items()):
        rays=[]
        for j in range(64):
            rays.append({"x":8+16*(j%8),"y":8+16*(j//8),
                         "stable":True,"pass_index":3 if j<20 else 1,
                         "camera_axis_depth":5.0,"ray_distance":5.3})
        frames[key]={
            "frame_index":int(key),"source_head_x_delta":delta,
            "source_geometry_sha256":str(i+1)*64,
            "camera_sha256":audit.perspective.canonical_hash(cam),
            "head_mesh_pass_index":3,
            "head_center_projection_px":[55+{0:0,1:12,2:-10}[int(key)],55],
            "source_stable_rays":64,
            "source_stable_head_rays":20,
            "source_rays":rays,
            "files":{
                "beauty.png":{"sha256":"a"*64,"bytes":2048},
                "render_passes.exr":{"sha256":"b"*64,"bytes":2048}
            }
        }
    return {
        "schema":"r073.original.synthetic.exr.object-track.v1",
        "status":"SOURCE_TRACKING_CAPTURE_PENDING_INDEPENDENT_IMAGE",
        "rights":"ORIGINAL_SYNTHETIC",
        "qualification":"NOT_REAL_IDENTITY_OPTICAL_FLOW_OR_MAKEHUMAN",
        "scene_id":"original-synthetic-head-v1",
        "original_source_script_sha256":audit.sha(audit.ROOT/"renderlab"/"synthetic_scene.py"),
        "perspective_script_sha256":audit.sha(audit.ROOT/"perspprobe"/"scene.py"),
        "camera":cam,"camera_sha256":audit.perspective.canonical_hash(cam),
        "source_semantic_object_names":sorted(audit.HEAD_NAMES),
        "source_semantic_object_index":3,
        "source_motion_type":"RIGID_HEAD_TRANSLATION_WITH_SEMANTIC_EXR_ID",
        "frames":frames
    }

def three_frames():
    arrays={"0":make_mask(40),"1":make_mask(52),"2":make_mask(30)}
    masks={};stats={}
    for key,arr in arrays.items():
        masks[key],stats[key]=audit.mask_centroid(arr)
    projections={"0":[55,55],"1":[67,55],"2":[45,55]}
    return masks,stats,projections

class TestSourceKnownSemanticTracking(unittest.TestCase):
    def test_approved_original_source_and_true_semantic_motion(self):
        self.assertEqual(len(audit.validate(fixture())),3)
        mask,stats,source=three_frames()
        result=audit.compare_motion(mask,stats,source)
        self.assertAlmostEqual(result["0_to_1"]["real_EXR_index_centroid_dx_px"],12)
        self.assertAlmostEqual(result["0_to_2"]["real_EXR_index_centroid_dx_px"],-10)

    def test_reversed_object_track_and_frozen_mask_fail_closed(self):
        mask,stats,source=three_frames()
        x=copy.deepcopy(source)
        x["1"]=[42,55]
        with self.assertRaisesRegex(ValueError,"REVERSED_RENDERED_SEGMENTATION_DIRECTION"):
            audit.compare_motion(mask,stats,x)
        mask2=copy.deepcopy(mask)
        stats2=copy.deepcopy(stats)
        mask2["1"]=mask2["0"].copy()
        stats2["1"]=dict(stats2["0"])
        with self.assertRaises(ValueError):
            audit.compare_motion(mask2,stats2,source)

    def test_missing_or_nonfinite_semantic_mask(self):
        for arr in (
            np.zeros((256,256),dtype=np.float32),
            np.full((256,256),np.nan,dtype=np.float32),
            np.zeros((64,64),dtype=np.float32)
        ):
            with self.assertRaises(ValueError):
                audit.mask_centroid(arr)

    def test_bad_claims_and_wrong_native_metadata_rejected(self):
        for mutate in (
            lambda m:m.update(rights="THIRD_PARTY_PROTECTED_CHARACTER"),
            lambda m:m.update(qualification="REAL_PERSON_IDENTITY_PASSED"),
            lambda m:m.update(source_semantic_object_index=1),
            lambda m:m.update(original_source_script_sha256="0"*64),
            lambda m:m["camera"].update(lens_mm=35.0),
            lambda m:m["frames"]["1"].update(frame_index=2),
            lambda m:m["frames"]["1"].update(source_head_x_delta=0),
            lambda m:m["frames"]["1"].update(camera_sha256="f"*64),
            lambda m:m["frames"]["1"].update(source_geometry_sha256=m["frames"]["0"]["source_geometry_sha256"]),
            lambda m:m["frames"]["1"]["source_rays"][0].update(camera_axis_depth=float("nan")),
            lambda m:m["frames"]["1"]["source_rays"][1].update(x=8,y=8),
            lambda m:m["frames"].pop("2"),
        ):
            m=fixture();mutate(m)
            with self.assertRaises(ValueError):
                audit.validate(m)

if __name__=="__main__":
    unittest.main()
