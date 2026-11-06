"""Independent hostile checksum/semantic controls for disposable native receipts.

All cases are synthetic local data. Blender is NOT being run by this suite.
"""
import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from disposable_combined_native_v1 import validate_native_receipts, FRAMES, ACTORS, SLOTS


def png_bytes():
    # Minimal, standards-compliant compressed RGB PNG 720x480.
    width, height = 720, 480
    raw = b''.join(b'\0' + b'\0' * (width * 3) for _ in range(height))
    def chunk(name, data):
        return struct.pack('>I', len(data)) + name + data + struct.pack('>I', zlib.crc32(name + data))
    return (b'\x89PNG\r\n\x1a\n' +
            chunk(b'IHDR', struct.pack('>2I5B', width, height, 8, 2, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(raw)) +
            chunk(b'tEXt', b'diagnostic\0' + b'x' * 2100) +
            chunk(b'IEND', b''))


class CombinedNativeNegativeControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.native = {}
        self.bvh = {}
        self.gap = {}
        for label, sha in [('before', 'a' * 64), ('after', 'b' * 64)]:
            samples = [{'frame': f, 'surface_overlap_triangle_pairs': 1 if f == 0 else 0,
                        'collision_free_proven': False} for f in FRAMES]
            self.bvh[label] = {
                'schema': 'scp.r009.original_bvh_surface_contact.v2',
                'motion_frames_evaluated': 72, 'frame_indices': FRAMES,
                'all_72_motion_frames_evaluated_for_bvh': True,
                'native_bvh_positive_negative_calibration': True,
                'collision_free_proven': False, 'garment_fit_accepted': False,
                'human_visual_accepted': False, 'release_approved': False,
                'actor_count': 2, 'slots': list(SLOTS),
                'per_actor_slot': {a: {slot: {
                    'sample_count': 72,
                    'samples': copy.deepcopy(samples),
                    'pairs_total': 1,
                    'frames_with_surface_overlaps': 1}
                    for slot in SLOTS} for a in ACTORS}}
            self.gap[label] = {'motion_frames_evaluated': 72,
                               'frame_indices': FRAMES, 'actor_count': 2,
                               'collision_qualified': False}
            imgs = []
            for k in range(8):
                fname = f'{label}_test_{k}.png'
                data = png_bytes()
                (self.root / fname).write_bytes(data)
                imgs.append({'file': fname, 'frame': 0, 'view': str(k),
                             'sha256': hashlib.sha256(data).hexdigest()})
            self.native[label] = {
                'source_sha256': sha,
                'native_import_render_technical_pass': True,
                'per_actor_per_eye_materials_confirmed': True,
                'imported_armatures': 2, 'imported_meshes': 8,
                'human_visual_accepted': False, 'release_approved': False,
                'native_diagnostic_camera': 'BLENDER_Z_UP_ACTOR_SPECIFIC_WORLD_X_FRONT',
                'closeups_generated': True, 'generated_renders': imgs,
                'bvh_surface_receipt_sha256': None,
                'garment_proxy_receipt_sha256': None}
        self.write()

    def write(self):
        for label in ('before', 'after'):
            bvh = self.root / (label + '_surface_bvh.json')
            gap = self.root / (label + '_garment_proximity.json')
            bvh.write_text(json.dumps(self.bvh[label]))
            gap.write_text(json.dumps(self.gap[label]))
            self.native[label]['bvh_surface_receipt_sha256'] = hashlib.sha256(bvh.read_bytes()).hexdigest()
            self.native[label]['garment_proxy_receipt_sha256'] = hashlib.sha256(gap.read_bytes()).hexdigest()
            (self.root / (label + '_native_blender.json')).write_text(json.dumps(self.native[label]))

    def test_control_pass_two_states(self):
        receipt = validate_native_receipts(self.root)
        self.assertTrue(receipt['native_blender_72_frame_v2_receipts_checked'])
        self.assertEqual(receipt['total_native_diagnostic_views'], 16)
        self.assertFalse(receipt['merge_release_CPE_approval'])
        self.assertEqual(receipt['per_state_bvh_actor_slot_samples'], 432)

    def test_downgraded_parent_v1_rejected(self):
        self.bvh['before']['schema'] = 'scp.r009.original_bvh_surface_contact.v1'
        self.write()
        with self.assertRaisesRegex(ValueError, 'BVH_V2_SCHEMA_REQUIRED'):
            validate_native_receipts(self.root)

    def test_missing_frame_rejected(self):
        self.bvh['before']['per_actor_slot'][ACTORS[0]][SLOTS[0]]['samples'].pop()
        self.write()
        with self.assertRaisesRegex(ValueError, 'BVH_SAMPLED_FRAMES_FORGED'):
            validate_native_receipts(self.root)

    def test_forged_pair_total_rejected(self):
        self.bvh['before']['per_actor_slot'][ACTORS[0]][SLOTS[0]]['pairs_total'] = 19
        self.write()
        with self.assertRaisesRegex(ValueError, 'BVH_METRICS_NOT_RECOMPUTABLE'):
            validate_native_receipts(self.root)

    def test_boolean_as_zero_metric_rejected(self):
        self.bvh['before']['per_actor_slot'][ACTORS[0]][SLOTS[0]]['samples'][0]['surface_overlap_triangle_pairs'] = True
        self.write()
        with self.assertRaisesRegex(ValueError, 'BVH_PAIRS_OR_PER_SAMPLE_HOLD_INVALID'):
            validate_native_receipts(self.root)

    def test_corrupt_png_rejected(self):
        img = self.root / self.native['before']['generated_renders'][0]['file']
        img.write_bytes(img.read_bytes() + b'corrupt')
        with self.assertRaisesRegex(ValueError, 'PNG_BYTE_OR_DIMENSION_MISMATCH'):
            validate_native_receipts(self.root)

    def test_path_traversal_rejected(self):
        self.native['before']['generated_renders'][0]['file'] = '../outside.png'
        self.write()
        with self.assertRaisesRegex(ValueError, 'UNSAFE_RENDER_PATH'):
            validate_native_receipts(self.root)

    def test_duplicate_render_rejected(self):
        self.native['before']['generated_renders'][1] = self.native['before']['generated_renders'][0].copy()
        self.write()
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_RENDER_WITNESS'):
            validate_native_receipts(self.root)

    def test_unauthorized_acceptance_rejected(self):
        self.native['before']['human_visual_accepted'] = True
        self.write()
        with self.assertRaisesRegex(ValueError, 'ILLEGAL_NATIVE_SCIENCE_PROMOTION'):
            validate_native_receipts(self.root)

    def test_receipt_hash_mismatch_rejected(self):
        p = self.root / 'before_surface_bvh.json'
        p.write_text(p.read_text() + ' ')
        with self.assertRaisesRegex(ValueError, 'BVH_RECEIPT_SHA_MISMATCH'):
            validate_native_receipts(self.root)

    def test_same_before_after_rejected(self):
        self.native['after']['source_sha256'] = self.native['before']['source_sha256']
        self.write()
        with self.assertRaisesRegex(ValueError, 'BEFORE_AFTER_SOURCE_MUST_DIFFER'):
            validate_native_receipts(self.root)

    def test_forged_proximity_count_rejected(self):
        self.gap['before']['motion_frames_evaluated'] = 12
        self.write()
        with self.assertRaisesRegex(ValueError, 'PROXIMITY_MUST_BE_DIAGNOSTIC_72F'):
            validate_native_receipts(self.root)


if __name__ == '__main__':
    unittest.main()
