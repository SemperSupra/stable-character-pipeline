import copy
import unittest
import numpy as np
import audit


def identity():
    return [float(i==j) for i in range(4) for j in range(4)]

def translation(dx):
    m=np.eye(4,dtype=np.float64)
    m[0,3]=dx
    return m.reshape(-1).tolist()

def fixture():
    bind=[[0.01*i,0.0,1.0+i/100] for i in range(audit.VERTICES)]
    w=[[0.5,0.5] for _ in bind]
    faces=[]
    for row in range(audit.RINGS-1):
        for k in range(audit.SIDES):
            a=row*audit.SIDES+k
            b=row*audit.SIDES+(k+1)%audit.SIDES
            faces.append([a,b,b+audit.SIDES,a+audit.SIDES])
    source={
      "vertex_bind":bind,"weights":w,"faces":faces,
      "bone_names":["root","tip"],
      "bone_rest_matrices":{"root":identity(),"tip":identity()},
      "rest_mesh_sha256":audit.canonical_hash({
          "vertices":bind,"faces":faces,"weights":w
      })
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
      "source":source,
      "frames":{"0":{},"1":{},"2":{}}
    }

class TestSourceBoundRealArmatureContract(unittest.TestCase):
    def test_original_weighted_mesh_contract(self):
        bind,weights,faces,frames=audit.validate_source(fixture())
        self.assertEqual(bind.shape,(96,3))
        self.assertEqual(weights.shape,(96,2))
        self.assertEqual(set(frames),{"0","1","2"})

    def test_independent_lbs_math_and_wrong_modifier_vertices(self):
        m=fixture()
        bind,w,_,_=audit.validate_source(m)
        mats={"root":identity(),"tip":translation(0.2)}
        expected=bind.copy()
        expected[:,0]+=0.1
        score=audit.verify_lbs(bind,w,mats,expected.tolist())
        self.assertLess(score["max_actual_modifier_vs_independent_lbs_error"],1e-8)
        corrupted=expected.copy();corrupted[20,0]+=0.2
        with self.assertRaisesRegex(ValueError,"ACTUAL_BLENDER_ARMATURE_VS_INDEPENDENT_LBS"):
            audit.verify_lbs(bind,w,mats,corrupted.tolist())

    def test_wrong_weight_sum_sign_and_weight_drift_rejected(self):
        for mutate in (
            lambda m:m["source"]["weights"][2].__setitem__(1,0.75),
            lambda m:m["source"]["weights"][2].__setitem__(1,-0.5),
            lambda m:m["source"]["weights"][2].__setitem__(1,float("nan")),
        ):
            m=fixture();mutate(m)
            with self.assertRaises(ValueError):
                audit.validate_source(m)

    def test_unknown_bone_nonrigid_transform_rejected(self):
        m=fixture()
        bind,w,_,_=audit.validate_source(m)
        for bad in (
            {"root":identity(),"ghost":identity()},
            {"root":identity(),"tip":[2.0 if i==0 else v for i,v in enumerate(identity())]},
            {"root":identity(),"tip":[float("nan") if i==0 else v for i,v in enumerate(identity())]},
        ):
            with self.assertRaises(ValueError):
                audit.verify_lbs(bind,w,bad,bind.tolist())

    def test_rights_source_and_camera_spoof_rejected(self):
        for mutate in (
            lambda m:m.update(rights="SOMEONE_ELSE"),
            lambda m:m.update(qualification="REAL_NAOMI_PASSED"),
            lambda m:m.update(original_source_script_sha256="0"*64),
            lambda m:m["camera"].update(lens_mm=35.0),
            lambda m:m["source"].update(bone_names=["tip","root"]),
            lambda m:m.update(rig_object_id=1),
            lambda m:m["source"]["faces"][0].__setitem__(0,999),
            lambda m:m["frames"].pop("1"),
        ):
            m=fixture();mutate(m)
            with self.assertRaises(ValueError):
                audit.validate_source(m)

if __name__=="__main__":
    unittest.main()
