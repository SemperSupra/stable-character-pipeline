import copy,unittest
from contact_pose_batch_v1 import assemble,validate,BatchError,ACTORS,SLOTS,FULL,SCHEMA,FALSE_KEYS

def sample(frames):
    d={'schema':SCHEMA,'source_sha256':'a'*64,'backend':'synthetic-fixture',
       'frames':frames,'frame_count':len(frames),'actors':{},'any_crossings':True,
       'interpretation':'SURFACE_TRIANGLE_CROSSINGS_OBSERVED'}
    for key in FALSE_KEYS:d[key]=False
    for a in ACTORS:
        d['actors'][a]={'slots':{s:[{'frame':f,'triangle_contact_pairs':1,
           'body_triangle_count':2,'garment_triangle_count':3} for f in frames] for s in SLOTS},
           'any_crossings':True}
    return d
class BatchTests(unittest.TestCase):
    def setUp(self):self.parts=[sample(['rest',*range(8)])]+[sample(list(range(n,n+8))) for n in range(8,72,8)]
    def test_full_valid(self):
        x=assemble(self.parts);self.assertEqual(x['frames'],FULL);self.assertEqual(x['frame_count'],73)
        self.assertFalse(x['native_blender_evaluated']);self.assertFalse(x['release_approved'])
    def test_shuffled_rejected(self):
        with self.assertRaisesRegex(BatchError,'NOT_COMPLETE'):assemble(self.parts[::-1])
    def test_missing_rejected(self):
        with self.assertRaisesRegex(BatchError,'NOT_COMPLETE'):assemble(self.parts[:-1])
    def test_duplicate_rejected(self):
        with self.assertRaisesRegex(BatchError,'NOT_COMPLETE'):assemble(self.parts+self.parts[-1:])
    def test_source_mismatch(self):
        d=copy.deepcopy(self.parts);d[3]['source_sha256']='b'*64
        with self.assertRaisesRegex(BatchError,'SOURCE_OR_BACKEND'):assemble(d)
    def test_false_approval(self):
        d=copy.deepcopy(self.parts);d[0]['release_approved']=True
        with self.assertRaisesRegex(BatchError,'FALSE_SCIENCE'):assemble(d)
    def test_negative_pair_rejected(self):
        d=copy.deepcopy(self.parts);d[2]['actors']['AsterOriginal']['slots']['costume_top'][0]['triangle_contact_pairs']=-1
        with self.assertRaisesRegex(BatchError,'INVALID_PAIR'):assemble(d)
    def test_dropped_actor_rejected(self):
        d=copy.deepcopy(self.parts);del d[2]['actors']['JuniperOriginal']
        with self.assertRaisesRegex(BatchError,'BAD_ACTORS'):assemble(d)
    def test_mislabeled_clock_rejected(self):
        d=copy.deepcopy(self.parts);d[1]['actors']['AsterOriginal']['slots']['costume_top'][0]['frame']=2
        with self.assertRaisesRegex(BatchError,'MISMATCHED_ROW_CLOCK'):assemble(d)
    def test_wrong_global_claim(self):
        d=copy.deepcopy(self.parts);d[2]['any_crossings']=False
        with self.assertRaisesRegex(BatchError,'FALSIFIED_GLOBAL'):assemble(d)
if __name__=='__main__':unittest.main()
