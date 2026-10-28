"""W05 exact source-clock and rights admissions — no bpy needed."""
import json
import tempfile
import unittest
from pathlib import Path
from w05_contract import read_motion

def fixture():
    p={'base':[0,0,0],'pivot':[0,1.5,0],'hinge':[0,-.4,0],'tip':[0,-1,0]}
    return {'schema':'stable-character/r4-w04-synthetic-retarget/1',
            'status':'PASS_SYNTHETIC_LOCAL_TRANSLATION_SOURCE_CLOCK_ONLY',
            'lane':'motion','source_rights':'ORIGINAL_SELF_AUTHORED_SYNTHETIC',
            'target_rights':'ORIGINAL_SELF_AUTHORED_SYNTHETIC',
            'learned_model_inference':False,'metric_3d_recovered':False,
            'real_human_or_animal_contact_measured':False,
            'joint_count':4,'frame_count':3,
            'samples':[{'source_ms':i*1000,'target_local':{**p,'hinge':[i*.05,-.4,0]}} for i in range(3)]}

def run(s):
    with tempfile.TemporaryDirectory() as tmp:
        f=Path(tmp)/'candidate.json';f.write_text(json.dumps(s))
        return read_motion(f)

class Admission(unittest.TestCase):
    def test_expected_original_synthetic(self):
        a,sha=run(fixture())
        self.assertEqual(a,[0,.05,.1]);self.assertEqual(len(sha),64)
    def test_missing_frame(self):
        s=fixture();s['samples'].pop()
        with self.assertRaises(ValueError):run(s)
    def test_time_origin(self):
        s=fixture();s['samples'][0]['source_ms']=1
        with self.assertRaises(ValueError):run(s)
    def test_no_external_rights(self):
        s=fixture();s['source_rights']='UNVERIFIED_EXTERNAL_PERSON'
        with self.assertRaises(ValueError):run(s)
    def test_no_learned_inference(self):
        s=fixture();s['learned_model_inference']=True
        with self.assertRaises(ValueError):run(s)
    def test_missing_joint(self):
        s=fixture();del s['samples'][1]['target_local']['tip']
        with self.assertRaises(ValueError):run(s)
    def test_not_real_depth(self):
        s=fixture();s['samples'][1]['target_local']['hinge'][2]=.1
        with self.assertRaises(ValueError):run(s)
    def test_nan(self):
        s=fixture();s['samples'][1]['target_local']['hinge'][0]=float('nan')
        with self.assertRaises(ValueError):run(s)
    def test_wrong_translation(self):
        s=fixture();s['samples'][2]['target_local']['hinge'][0]=.2
        with self.assertRaises(ValueError):run(s)
if __name__=='__main__':unittest.main()
