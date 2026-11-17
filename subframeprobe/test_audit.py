import copy
import unittest

import audit
def parent_fixture():
    bind=[[0.01*i,0.0,1.0+i/100] for i in range(audit.lbs.VERTICES)]
    weights=[[0.5,0.5] for _ in bind]
    faces=[]
    for row in range(audit.lbs.RINGS-1):
        for k in range(audit.lbs.SIDES):
            a=row*audit.lbs.SIDES+k
            b=row*audit.lbs.SIDES+(k+1)%audit.lbs.SIDES
            faces.append([a,b,b+audit.lbs.SIDES,a+audit.lbs.SIDES])
    identity=[float(i==j) for i in range(4) for j in range(4)]
    source={
        "vertex_bind":bind,"weights":weights,"faces":faces,
        "bone_names":["root","tip"],
        "bone_rest_matrices":{"root":identity,"tip":identity},
        "rest_mesh_sha256":audit.lbs.canonical_hash({
            "vertices":bind,"faces":faces,"weights":weights}),
    }
    cam={"type":"PERSP","lens_mm":65.0,"sensor_width_mm":36.0,
         "resolution":[256,256],"shift_x":0.0,"shift_y":0.0}
    return {
        "schema":"r072.synthetic.skinning.native.v1",
        "status":"NATIVE_ARMATURE_SOURCE_CAPTURE_PENDING_INDEPENDENT_LBS_EXR",
        "rights":"ORIGINAL_SYNTHETIC",
        "qualification":"NOT_REAL_PERSON_OR_MAKEHUMAN_SKINNING",
        "source_scene_id":"original-synthetic-head-v1",
        "motion_type":"TWO_BONE_LINEAR_BLEND_SKINNING_NO_HUMAN",
        "original_source_script_sha256":audit.sha(audit.ROOT/"renderlab"/"synthetic_scene.py"),
        "perspective_script_sha256":audit.sha(audit.ROOT/"perspprobe"/"scene.py"),
        "rig_object_name":"r072-original-weighted-sleeve",
        "rig_object_id":3,
        "camera":cam,"camera_sha256":audit.perspective.canonical_hash(cam),
        "source":source,"frames":{"0":{},"1":{},"2":{}},
    }

def fixture():
    p=parent_fixture()
    source=p["source"]
    camera=p["camera"]
    samples={}
    for index,(name,(time,angle)) in enumerate(audit.KEYS.items()):
        vertices=[[round(v[0]+index*0.055,9),v[1],v[2]] for v in source["vertex_bind"]]
        faces=source["faces"]
        rays=[]
        for i in range(64):
            rays.append({"x":8+(i%8)*16,"y":8+(i//8)*16,
                         "stable":True,"pass_index":3 if i<8 else 1,
                         "camera_axis_depth":5.0,"ray_distance":5.2})
        samples[name]={
            "time_frames":time,
            "source_expected_linear_angle_x":angle,
            "actual_fcurve_angle_x":round(angle,9),
            "evaluated_vertices":vertices,
            "faces_sha256":audit.lbs.canonical_hash(faces),
            "evaluated_mesh_sha256":audit.lbs.canonical_hash({
                "vertices":vertices,"faces":faces}),
            "armature_pose_matrices":{"root":[float(i==j) for i in range(4) for j in range(4)],
                                      "tip":[float(i==j) for i in range(4) for j in range(4)]},
            "rays":rays,"stable_ray_count":64,"rig_stable_ray_count":8,
            "files":{
              "beauty.png":{"sha256":"a"*64,"bytes":1234},
              "render_passes.exr":{"sha256":"b"*64,"bytes":5678}
            }
        }
    return {
      "schema":"r074.original.synthetic.native-subframes.v1",
      "status":"ACTUAL_BLENDER_FCURVE_SUBFRAMES_PENDING_EXR_LBS_AUDIT",
      "rights":"ORIGINAL_SYNTHETIC",
      "qualification":"NOT_REAL_PERSON_SKIN_OR_MMD_RETARGET",
      "source_scene_id":"original-synthetic-head-v1",
      "source_original_sha256":audit.sha(audit.ROOT/"renderlab"/"synthetic_scene.py"),
      "source_skin_sha256":audit.sha(audit.ROOT/"skinprobe"/"scene.py"),
      "source_camera_sha256":audit.sha(audit.ROOT/"perspprobe"/"scene.py"),
      "camera":camera,
      "camera_sha256":audit.perspective.canonical_hash(camera),
      "timebase":"BLENDER_SCENE_FRAMES_WITH_EXPLICIT_SUBFRAME",
      "interpolation":"ACTUAL_BLENDER_FCURVE_LINEAR",
      "keys":[[0,0.0],[1,0.34],[2,-0.29]],
      "source":source,"samples":samples,
    }

class TestActualSubframeContract(unittest.TestCase):
    def test_valid_typed_original_fixture(self):
        bind,w,faces,samples=audit.validate(fixture())
        self.assertEqual(bind.shape,(96,3))
        self.assertEqual(len(samples),5)

    def test_wrong_timebase_and_interpolation_rejected(self):
        for mutate in (
            lambda m:m.update(timebase="BLENDER_DEFAULT_FRAME_ONE"),
            lambda m:m.update(interpolation="GUESS_BEZIER"),
            lambda m:m.update(keys=[[0,0.0],[1,0.34],[2,0.0]]),
            lambda m:m["samples"]["t050"].update(time_frames=1.0),
            lambda m:m["samples"]["t150"].update(actual_fcurve_angle_x=0.34),
            lambda m:m["samples"]["t050"].update(source_expected_linear_angle_x=0.11),
            lambda m:m["samples"].pop("t150"),
        ):
            m=fixture();mutate(m)
            with self.subTest(mutate=mutate):
                with self.assertRaises(ValueError):
                    audit.validate(m)

    def test_replay_pose_geometry_and_false_source_sha(self):
        for mutate in (
            lambda m:m["samples"]["t050"].update(evaluated_mesh_sha256=m["samples"]["t000"]["evaluated_mesh_sha256"]),
            lambda m:m["samples"]["t050"]["evaluated_vertices"][0].__setitem__(0,999),
            lambda m:m["samples"]["t050"].update(faces_sha256="f"*64),
            lambda m:m.update(source_skin_sha256="f"*64),
            lambda m:m.update(rights="UNLICENSED_FACE"),
            lambda m:m.update(qualification="REAL_MAKEHUMAN_SKIN_ACCEPTED"),
        ):
            m=fixture();mutate(m)
            with self.assertRaises(ValueError):
                audit.validate(m)

    def test_mutated_rays_and_missing_images(self):
        for mutate in (
            lambda m:m["samples"]["t050"]["rays"][0].update(stable="true"),
            lambda m:m["samples"]["t050"]["rays"][0].update(pass_index=88),
            lambda m:m["samples"]["t050"]["rays"][0].update(x=24,y=8),
            lambda m:m["samples"]["t050"]["rays"][0].update(x=-1),
            lambda m:m["samples"]["t050"].update(rig_stable_ray_count=0),
            lambda m:m["samples"]["t050"]["files"].pop("render_passes.exr"),
        ):
            m=fixture();mutate(m)
            with self.assertRaises(ValueError):
                audit.validate(m)

    def test_inherited_numpy_independent_weighted_blender_oracle_falsifier(self):
        p=parent_fixture()
        bind,w,_,_=audit.lbs.validate_source(p)
        i=[float(a==b) for a in range(4) for b in range(4)]
        observed=bind.copy()
        self.assertLess(audit.lbs.verify_lbs(bind,w,{"root":i,"tip":i},observed.tolist())
                        ["max_actual_modifier_vs_independent_lbs_error"],1e-9)
        observed[19,0]+=0.03
        with self.assertRaises(ValueError):
            audit.lbs.verify_lbs(bind,w,{"root":i,"tip":i},observed.tolist())

if __name__=="__main__":
    unittest.main()
