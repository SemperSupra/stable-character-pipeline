"""Fail-closed 72-frame signed-vertex contact diagnostic; no cloth acceptance."""
import json
import os
from pathlib import Path
import unittest
from observe_makehuman35_garment_v0 import _validated_frames, FRAMES
from observe_makehuman35_garment_72_v1 import evaluate, ALL_FRAMES, EXACT_FITTED_SHA, SCHEMA

SOURCE = Path(os.getenv('R009_MH35_HYBRID', str(Path(__file__).with_name('aster_juniper_cloth_clearance_hybrid_trim_v0.glb'))))

class FrameGate(unittest.TestCase):
    def test_default_sparse_is_unchanged(self):
        self.assertEqual(_validated_frames(FRAMES), ('rest',0,24,48,71))
    def test_full72_has_rest_and_no_duplicates(self):
        self.assertEqual(_validated_frames(ALL_FRAMES), ALL_FRAMES)
        self.assertEqual(len(ALL_FRAMES), 73)
    def test_malicious_window_fail_closed(self):
        for frames in ((),('rest',),('rest',72),('rest',-1),('rest',True),('rest',1,1),
                       ('rest',20,19),('static',0),('rest',0.0),list(FRAMES),
                       ('rest',*range(72),72)):
            with self.subTest(frames=repr(frames)), self.assertRaises(ValueError):
                _validated_frames(frames)
    def test_source_pin_and_nonpromotion(self):
        self.assertEqual(len(EXACT_FITTED_SHA),64)
        self.assertEqual(SCHEMA,'scp.r009.makehuman35.signed_wardrobe_contact_72_v1')
        with self.assertRaisesRegex(ValueError,'EXACT_FITTED_SOURCE_SHA_MISMATCH'):
            evaluate(b'bad')

@unittest.skipUnless(SOURCE.exists(), 'Exact public-safe source-original candidate absent from public CI')
class ActualFitted(unittest.TestCase):
    def test_actual_72_signed_and_sparse_unchanged(self):
        import hashlib
        raw=SOURCE.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),EXACT_FITTED_SHA)
        report=evaluate(raw)
        self.assertEqual(report['signed_sample_count'],584)
        self.assertEqual(set(report['actors']),{'AsterOriginal','JuniperOriginal'})
        self.assertFalse(report['cloth_fitting_accepted'])
        self.assertFalse(report['native_blender_evaluated'])
        self.assertFalse(report['full_motion_72_frame_collision_qualified'])
        for actor,data in report['actors'].items():
            self.assertTrue(data['all_sign_calibrated'])
            self.assertEqual(set(data['slots']),{'costume_top','costume_bottom','costume_trim','footwear'})
            for slot,rows in data['slots'].items():
                self.assertEqual(len(rows),73)
                self.assertEqual([r['frame'] for r in rows],list(ALL_FRAMES))
                self.assertTrue(all(r['sign_calibrated'] and not r['penetration_accepted'] for r in rows))
            self.assertGreater(report['technical_summary'][actor]['footwear']['max_fraction_gt_5mm'],.19)
            self.assertGreater(report['technical_summary'][actor]['costume_bottom']['max_fraction_gt_5mm'],.01)
            self.assertEqual(report['technical_summary'][actor]['costume_top']['max_fraction_gt_5mm'],0.0)
            self.assertEqual(report['technical_summary'][actor]['costume_trim']['max_fraction_gt_5mm'],0.0)

if __name__=='__main__':unittest.main()
