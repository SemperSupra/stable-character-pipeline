"""Independent source-bound nonpromoting native surface clearance regression."""
import hashlib, unittest
from pathlib import Path
from costume_garment_v1 import _unpack_glb
from fit_signed_clearance_v0 import derive, ClearanceError, SCHEMA_FIT
from retarget_makehuman_v0 import CANDIDATE_GLB_SHA256,ACTORS
from observe_makehuman35_garment_v0 import inspect

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'aster_juniper_makehuman35_candidate_v0.glb'
DERIVED=ROOT/'aster_juniper_cloth_clearance_hybrid_trim_v0.glb'

class Hostile(unittest.TestCase):
    def test_bad_source_hash_rejected(self):
        with self.assertRaises(ValueError):derive(b'tamper')
    def test_schema_and_pinned_source(self):
        self.assertEqual(len(CANDIDATE_GLB_SHA256),64)
        self.assertEqual(SCHEMA_FIT,'scp.r009.makehuman35.rest_clearance_projection.v0')

@unittest.skipUnless(SOURCE.exists() and DERIVED.exists(),'Exact actual-source GLBs absent')
class ActualSource(unittest.TestCase):
    def test_deterministic_garment_derivative_preserves_source(self):
        raw=SOURCE.read_bytes();known=DERIVED.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),CANDIDATE_GLB_SHA256)
        got,rc=derive(raw)
        self.assertEqual(got,known)
        self.assertEqual(rc['derived_sha256'],hashlib.sha256(known).hexdigest())
        self.assertFalse(rc['native_cloth_qualified'])
        old,ob=_unpack_glb(raw);new,nb=_unpack_glb(known)
        self.assertEqual(old['skins'],new['skins'])
        self.assertEqual(old['animations'],new['animations'])
        self.assertEqual(old['meshes'],new['meshes'][:len(old['meshes'])])
        self.assertEqual(ob,nb[:len(ob)])
        self.assertEqual(len(new['meshes'])-len(old['meshes']),6)
        for actor in ACTORS:
            for slot in ('costume_top','costume_bottom','costume_trim'):
                item=rc['actors'][actor][slot]
                self.assertEqual(item['post_inside_gt_5mm_fraction'],0.)
                self.assertLess(item['projection_max_m'],.06)
                # Face inversion remains a research quality HOLD: even
                # 0.1% cannot be silently characterized as garment acceptance.
                self.assertLess(item['face_normal_direction_reversal_fraction'],.005)
    def test_signed_sparse_motion_not_false_promoted(self):
        raw=DERIVED.read_bytes()
        r=inspect(raw,hashlib.sha256(raw).hexdigest())
        for actor in ACTORS:
            for slot in ('costume_top','costume_bottom','costume_trim'):
                self.assertEqual(len(r['actors'][actor]['slots'][slot]),5)
                self.assertLess(r['actors'][actor]['slots'][slot][0]['negative_gt_5mm_fraction'],.001)
            self.assertGreater(r['actors'][actor]['slots']['footwear'][0]['negative_gt_5mm_fraction'],.15)
        self.assertFalse(r['cloth_fitting_accepted'])
        self.assertFalse(r['full_motion_72_frame_collision_qualified'])

if __name__=='__main__':unittest.main()
