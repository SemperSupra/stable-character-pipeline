"""R20 source-byte evidence hostile tests on standalone original synthetic fixtures."""
import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from media_proof import audit,Invalid,SOURCE,CAMERAS

def h(b):return hashlib.sha256(b).hexdigest()
class SourceSafeFixture(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup)
  self.root=Path(self.t.name)
  self.media=self.root/"media";self.evidence=self.root/"evidence"
  for kind in ("cli","http"):
   p=self.media/("r9-"+kind)/"attempt-0001"/"forward"
   (p/"rendered").mkdir(parents=True)
   b=("blend-"+kind).encode();(p/"original_source_grounded_24frame_native.blend").write_bytes(b)
   g=b"source-grounded-glb";(p/"original_synthetic_24frame_skinned.glb").write_bytes(g)
   video={cam:None for cam in CAMERAS}
   for cam in CAMERAS:
    x=("mp4-"+cam).encode();(p/"rendered"/(cam+".mp4")).write_bytes(x);video[cam]=h(x)
   r={"schema":"scp.native-job-result.v1","revision":SOURCE,
    "rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
    "human_behavior":"FAIL_ABSTRACT_LIMBS_ONLY","human_anatomy":"UNKNOWN_NO_INDEPENDENT_JCS_OR_ROM",
    "release":"HELD_R009_NOT_RUN_NOT_ADMITTED","frames":24,"fps":12,
    "actor_ids":["CobaltOriginal","MarigoldOriginal"],
    "source_sha256":h(b"common-source"),"glb_sha256":h(g),
    "blend_sha256":h(b),"video_sha256":video}
   q=self.evidence/("r9-"+kind)/"attempt-0001";q.mkdir(parents=True)
   (q/"result.json").write_text(json.dumps(r))
 def test_exact_public_bytes_still_hold(self):
  r=audit(self.media,self.evidence)
  self.assertEqual(r["decision"],"HOLD_RELEASE_AND_CPE_PROMOTION")
  self.assertEqual(len(r["verified_transport_media_sha"]),3)
 def test_forged_video_denied(self):
  p=self.media/"r9-http"/"attempt-0001"/"forward"/"rendered"/"OriginalFront.mp4"
  p.write_bytes(b"tampered")
  with self.assertRaisesRegex(Invalid,"ORIGINAL_MEDIA_HASH_MISMATCH"):audit(self.media,self.evidence)
 def test_cross_transport_source_denied(self):
  p=self.evidence/"r9-http"/"attempt-0001"/"result.json"
  r=json.loads(p.read_text());r["source_sha256"]=h(b"other");p.write_text(json.dumps(r))
  with self.assertRaisesRegex(Invalid,"TWO_TRANSPORT_SOURCE_MISMATCH"):audit(self.media,self.evidence)
 def test_forged_scientific_promote_denied(self):
  p=self.evidence/"r9-cli"/"attempt-0001"/"result.json"
  r=json.loads(p.read_text());r["human_behavior"]="PASS";p.write_text(json.dumps(r))
  with self.assertRaisesRegex(Invalid,"SCIENTIFIC"):audit(self.media,self.evidence)
if __name__=="__main__":unittest.main()
