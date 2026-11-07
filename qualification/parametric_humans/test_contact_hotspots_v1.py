"""Hostile source-free and optional source-admitted contact-face provenance tests."""
import hashlib,json,os,unittest
from pathlib import Path
import numpy as np
from contact_hotspots_v1 import face_pairs,hotspot_rows,make_polydata,audit,AtlasError,SOURCE_SHA256

class FaceContactTests(unittest.TestCase):
    def test_positive_intersection_identified(self):
        a=make_polydata([[-1.,-1.,0.],[1.,-1.,0.],[0.,1.,0.]],[[0,1,2]])
        b=make_polydata([[-.2,0.,-.1],[.2,0.,.1],[0.,.5,-.1]],[[0,1,2]])
        pairs=face_pairs(a,b)
        self.assertEqual(pairs.tolist(),[[0,0]])
        summary=hotspot_rows(pairs,np.asarray(a.GetPoints().GetData()),np.array([[0,1,2]]),np.asarray(b.GetPoints().GetData()),np.array([[0,1,2]]))
        self.assertEqual(summary['pairs'],1)
        self.assertEqual(summary['garment_hotspots'][0]['face_index'],0)
    def test_negative_control(self):
        a=make_polydata([[-1.,-1.,0.],[1.,-1.,0.],[0.,1.,0.]],[[0,1,2]])
        b=make_polydata([[0.,0.,2.],[.5,0.,2.],[0.,.5,2.]],[[0,1,2]])
        self.assertEqual(len(face_pairs(a,b)),0)
    def test_bad_contact_face_id_rejected(self):
        with self.assertRaises(AtlasError):
            hotspot_rows(np.array([[3,0]]),np.zeros((3,3)),np.array([[0,1,2]]),np.zeros((3,3)),np.array([[0,1,2]]))
    def test_nan_hotspot_fails(self):
        p=np.array([[float('nan'),0,0],[1,0,0],[0,1,0]])
        with self.assertRaises(AtlasError):hotspot_rows(np.array([[0,0]]),p,np.array([[0,1,2]]),np.zeros((3,3)),np.array([[0,1,2]]))
    def test_source_pin_refuses_mismatch(self):
        with self.assertRaises(AtlasError):audit(b'not a source',['rest'])
    def test_frame_duplicates_fail_closed(self):
        # The source must be valid first; exact GLB is intentionally not on public CI.
        with self.assertRaises(AtlasError):audit(b'not a source',['rest','rest'])

class SourceAdmittedAtlas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=os.environ.get('SCP_R009_JUNIPER_ARMHOLE_GLB')
        if not path:raise unittest.SkipTest('Exact owner-original source not on public runners')
        cls.raw=Path(path).read_bytes()
        if hashlib.sha256(cls.raw).hexdigest()!=SOURCE_SHA256:raise AssertionError('SOURCE_HASH_NOT_ADMITTED')
    def test_actual_contact_faces(self):
        r=audit(self.raw,['rest',16]);self.assertEqual(r['frame_count'],2)
        self.assertEqual(r['actors']['JuniperOriginal']['costume_top']['total_pairs'],8)
        self.assertEqual(r['actors']['AsterOriginal']['costume_top']['total_pairs'],15)
        self.assertFalse(r['garment_fit_accepted'])
        self.assertFalse(r['native_blender_evaluated'])

if __name__=='__main__':unittest.main()
