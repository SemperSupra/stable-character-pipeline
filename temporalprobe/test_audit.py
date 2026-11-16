import copy
import unittest
import numpy as np
import audit

def fixture():
    camera={"type":"PERSP","lens_mm":65.0,"sensor_width_mm":36.0,"resolution":[256,256]}
    frames={}
    for idx,(key,delta) in enumerate(audit.OFFSETS.items()):
        rays=[]
        for k in range(64):
            rays.append({
                "x":8+16*(k%8),"y":8+16*(k//8),"stable":True,
                "pass_index":1,"camera_axis_depth":5.0,
                "ray_distance":5.5,"geometric_normal":[0,0,1],
                "object_name":"original-synthetic-head"
            })
        frames[key]={
          "frame_index":int(key),
          "head_x_delta_source_units":delta,
          "pose_sha256":str(idx+1)*64,
          "geometry_sha256":str(idx+4)*64,
          "camera_sha256":audit.persp.canonical_hash(camera),
          "stable_ray_count":64,
          "rays":rays,
          "files":{
              "beauty.png":{"sha256":"a"*64,"bytes":2048},
              "render_passes.exr":{"sha256":"b"*64,"bytes":4096}
          }
        }
    return {
      "schema":"r060.synthetic.pose_time.v1",
      "status":"ORIGINAL_SOURCE_POSE_CAPTURE_ONLY",
      "qualification":"NOT_RIGGED_SKIN_OR_HUMAN_MOTION",
      "rights":"ORIGINAL_SYNTHETIC","scene_id":"original-synthetic-head-v1",
      "source_script_sha256":audit.sha(audit.ROOT/"renderlab"/"synthetic_scene.py"),
      "perspective_script_sha256":audit.sha(audit.ROOT/"perspprobe"/"scene.py"),
      "exr_z_convention":"CAMERA_AXIS_DEPTH_MINUS_LOCAL_Z",
      "motion_type":"CONTROLLED_MULTI_OBJECT_RIGID_HEAD_TRANSLATION_NOT_SKIN",
      "camera":camera,"camera_sha256":audit.persp.canonical_hash(camera),
      "head_mesh_names":list(audit.ROOT.parts[:0])+[
          "head","nose","mouth","left-sclera","left-iris","left-pupil",
          "left-brow","left-ear","right-sclera","right-iris","right-pupil",
          "right-brow","right-ear"],
      "frames":frames
    }

class TestTemporalNativeEvidence(unittest.TestCase):
    def test_original_three_frame_source_schema(self):
        frames,total=audit.validate(fixture())
        self.assertEqual(len(frames),3)
        self.assertEqual(total,192)

    def test_frame_axis_and_object_mismatch_fails(self):
        m=fixture()
        rays=m["frames"]["0"]["rays"]
        decoded={"depth":{"Z":np.full((256,256),5.0,dtype=np.float32)},
                 "object":{"X":np.full((256,256),1.0,dtype=np.float32)}}
        result=audit.persp.compare_axial_depth(rays,decoded)
        self.assertEqual(result["joint_correct"],64)
        for r in rays[:3]:
            decoded["depth"]["Z"][r["y"],r["x"]]=5.2
        with self.assertRaises(ValueError):
            audit.persp.compare_axial_depth(rays,decoded)

    def test_source_frame_mutations_reject(self):
        for change in (
          lambda m:m["frames"].pop("2"),
          lambda m:m["frames"]["1"].update(head_x_delta_source_units=0.0),
          lambda m:m["frames"]["1"].update(geometry_sha256=m["frames"]["0"]["geometry_sha256"]),
          lambda m:m["frames"]["1"].update(pose_sha256=m["frames"]["0"]["pose_sha256"]),
          lambda m:m["frames"]["1"].update(camera_sha256="e"*64),
          lambda m:m["frames"]["1"]["rays"][0].update(camera_axis_depth=float("nan")),
          lambda m:m["frames"]["1"]["rays"][0].update(ray_distance=0.3),
          lambda m:m.update(rights="UNADMITTED_FACE"),
          lambda m:m.update(motion_type="REAL_HUMAN_WALK"),
          lambda m:m["frames"]["1"]["rays"][1].update(x=8,y=8),
        ):
            m=fixture();change(m)
            with self.assertRaises(ValueError):
                audit.validate(m)

    def test_unqualified_original_video_claim_rejected(self):
        m=fixture()
        m["qualification"]="ACCEPTED_NAOMI_ALISON_VIDEO"
        with self.assertRaisesRegex(ValueError,"FORGED_ADMISSION"):
            audit.validate(m)

if __name__=="__main__":
    unittest.main()
