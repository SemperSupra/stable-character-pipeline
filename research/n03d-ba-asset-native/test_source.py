"""BA independent asset header / exact Git blob / rights and no false gait tests."""
import hashlib,json,struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from source import glb,blobsha,asset,independent,report,blend,candidates
def mini_glb(skin=True,animation=True):
    data={"asset":{"version":"2.0"},"nodes":[{"mesh":0,"skin":0} if skin else {"mesh":0}],
          "skins":[{"joints":[1]}] if skin else [],
          "animations":[{"name":"walk","channels":[{"target":{"node":1,"path":"rotation"}}]}] if animation else []}
    chunk=json.dumps(data,separators=(",",":")).encode()
    chunk+=b" " * ((-len(chunk))%4)
    return b"glTF"+struct.pack("<II",2,20+len(chunk))+struct.pack("<I4s",len(chunk),b"JSON")+chunk
class Controls(unittest.TestCase):
    def test_valid_glb_has_skin_and_motion(self):
        a=glb(mini_glb());self.assertTrue(a["rig_skin_structurally_present"])
        self.assertTrue(a["animation_structurally_present"])
    def test_static_glb_has_no_motion_not_hard_fail(self):
        self.assertFalse(glb(mini_glb(animation=False))["animation_structurally_present"])
    def test_no_skin_rejected(self):
        with self.assertRaisesRegex(ValueError,"NO_SKIN"):glb(mini_glb(skin=False))
    def test_truncated_glb_rejected(self):
        with self.assertRaisesRegex(ValueError,"GLB_VERSION_LENGTH"):glb(mini_glb()[:-3])
    def test_bad_version(self):
        v=bytearray(mini_glb());v[4]=3
        with self.assertRaisesRegex(ValueError,"GLB_VERSION_LENGTH"):glb(bytes(v))
    def test_bad_blob(self):
        with self.assertRaisesRegex(ValueError,"UPSTREAM_GIT_BLOB_MISMATCH"):asset(b"1234","0"*40,"model")
    def test_git_blob_expected(self):
        self.assertEqual(blobsha(b"test"),hashlib.sha1(b"blob 4\x00test").hexdigest())
    def test_blend_magic(self):
        self.assertEqual(blend(b"BLENDER-v400somebytes")["blender_binary_structurally_present"],True)
        with self.assertRaisesRegex(ValueError,"BLEND_MAGIC"):blend(b"FAKE---v400somebytes")
    def test_explicit_no_promotion(self):
        z={"schema":"scp.n03d-ba.asset-audit.v1","source_commit":"a"*40,
           "source_only_original_or_public":True,"research_asset_in_runner_only":True,
           "production_admitted":False,"physical_contact_accepted":False,
           "mvp_accepted":False,"status":"SOURCE_BYTES_VERIFIED_STRUCTURAL_ONLY_HOLD",
           "assets":{"model":{"exact_verified":True,"source_git_blob_sha1":"b"*40,
           "sha256":"c"*64,"bytes":5000}}}
        self.assertEqual(independent(z),"HOLD")
        for key in ("production_admitted","physical_contact_accepted","mvp_accepted"):
            bad={**z,key:True}
            with self.assertRaisesRegex(ValueError,"FORGED_GAIT_PROMOTION"):independent(bad)
    def test_registry_rejected_rights(self):
        d=Path(__file__).parent/"registry.json"
        a=candidates(d);self.assertEqual(set(a),{"piston","vsim","cc","rigify"})
        self.assertTrue(all(not r["production_admitted"] for r in a.values()))
if __name__=="__main__":unittest.main()
