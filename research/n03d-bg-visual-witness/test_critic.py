"""BG adversarial synthetic source/film/actor semantics; no fake mp4 pass."""
import hashlib,math,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from critic import validate
def fixture(root):
    root=Path(root)
    subjects=[{"actor":a,"rig":r,"bones":163 if r=="default" else 53,
            "same_morphology_19158_vertex_delta_m":0.,
            "source_frames":[120,475],"true_physical_gait_accepted":False}
        for a in ("AsterOriginal","JuniperOriginal") for r in ("default","game_engine")]
    videos=[]
    for k in ("front","oblique"):
        path=root/(k+"_movie.mp4")
        path.write_bytes((k.encode()*12000)[:13000])
        videos.append({"camera":k,"file":path.name,"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
                       "bytes":path.stat().st_size,
                       "source_rights_attribution":"MakeHuman CC0 + Ian Mason 100STYLE CC BY4",
                       "mvp_accepted":False})
    return {"schema":"scp.n03d-bg.two-camera-source-safe-visual-witness.v1",
            "source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
            "source_MPF_upstream":"9de0707fdc88438d7c53a1a2ac7937d9221e2431",
            "source_bvh_blob":"a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61",
            "shoes01_CC0_archive_sha256":"ded3f70428505eabbf1f6d7b5f61196a7366ef20757103d276ad0ed336c35ada",
            "official_blender":[5,2,4],"native_scene_h264_12fps_frames":72,
            "visual_full_biomechanics_verified":False,
            "user_protected_Naomi_Alison_used":False,
            "physical_gait_accepted":False,"mvp_accepted":False,
            "status":"PASS_NARROW_AUTHENTIC_2_CAMERA_FILM_HOLD_VISUAL_QUALITY",
            "actual_separate_source_original_actors":subjects,
            "native_source_to_shoe_observations":[{"native_frame":f,"source_frame":120+5*f,
                   "actor_observations":[{}]*4} for f in (0,35,71)],
            "videos":videos}
class BG(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.x=fixture(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def test_no_false_video_on_metadata_fixture(self):
        z=validate(self.x,self.tmp.name,allow_decoding=False)
        self.assertEqual(z["status"],"HOLD_METADATA_ONLY_NO_VIDEO_DECODING")
        self.assertFalse(z["real_native_H264_12fps_72_decoded_frames"])
    def test_wrong_source_sha(self):
        self.x["source_bvh_blob"]="0"*40
        with self.assertRaisesRegex(ValueError,"SPOOFED_FILM_OR_SOURCE_RIGHTS"):
            validate(self.x,self.tmp.name,False)
    def test_forged_protected_media(self):
        self.x["user_protected_Naomi_Alison_used"]=True
        with self.assertRaisesRegex(ValueError,"SPOOFED_FILM_OR_SOURCE_RIGHTS"):
            validate(self.x,self.tmp.name,False)
    def test_forged_full_gait_acceptance(self):
        self.x["visual_full_biomechanics_verified"]=True
        with self.assertRaisesRegex(ValueError,"SPOOFED_FILM_OR_SOURCE_RIGHTS"):
            validate(self.x,self.tmp.name,False)
    def test_movie_byte_modified(self):
        (Path(self.tmp.name)/"front_movie.mp4").write_bytes(b"z"*18000)
        with self.assertRaisesRegex(ValueError,"VIDEO_BYTES_CHANGED"):
            validate(self.x,self.tmp.name,False)
    def test_missing_camera(self):
        self.x["videos"].pop()
        with self.assertRaisesRegex(ValueError,"NO_TRUE_DUAL_CAMERA"):
            validate(self.x,self.tmp.name,False)
    def test_wrong_source_frame(self):
        self.x["native_source_to_shoe_observations"][1]["source_frame"]=294
        with self.assertRaisesRegex(ValueError,"VISUAL_SOURCE_CLOCK"):
            validate(self.x,self.tmp.name,False)
    def test_same_morphology_falsifier(self):
        self.x["actual_separate_source_original_actors"][0]["same_morphology_19158_vertex_delta_m"]=.003
        with self.assertRaisesRegex(ValueError,"WRONG_RIG_MOTION_OR_SHAPE"):
            validate(self.x,self.tmp.name,False)
    def test_video_number_held(self):
        self.x["native_scene_h264_12fps_frames"]=24
        with self.assertRaisesRegex(ValueError,"SPOOFED_FILM_OR_SOURCE_RIGHTS"):
            validate(self.x,self.tmp.name,False)
    def test_wrong_license(self):
        self.x["videos"][0]["source_rights_attribution"]="Geno"
        with self.assertRaisesRegex(ValueError,"SOURCE_RIGHTS_FILM_SIZE"):
            validate(self.x,self.tmp.name,False)
if __name__=="__main__":unittest.main()
