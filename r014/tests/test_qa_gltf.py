import json, struct, tempfile, unittest
from pathlib import Path
from r014.qa_gltf import qualify,load_glb

def sample():
    return {'meshes':[{'primitives':[{'attributes':{'POSITION':0,'JOINTS_0':1,'WEIGHTS_0':2},'targets':[{'POSITION':3}]}]}],
            'accessors':[{'count':4},{'count':4},{'count':4},{'count':4},{'count':2}],
            'nodes':[{},{}],'skins':[{'joints':[0,1],'inverseBindMatrices':4}],
            'animations':[{'samplers':[{}],'channels':[{'sampler':0,'target':{'node':1}}]}]}

class Contract(unittest.TestCase):
    def test_positive(self): self.assertEqual(qualify(sample())['status'],'PASS_STRUCTURAL_ONLY')
    def test_reject_missing_weights(self):
        x=sample();del x['meshes'][0]['primitives'][0]['attributes']['WEIGHTS_0']
        self.assertEqual(qualify(x)['status'],'FAIL')
    def test_reject_bad_ibm(self):
        x=sample();x['accessors'][4]['count']=1
        self.assertIn('invalid inverse bind matrices',qualify(x)['errors'])
    def test_reject_bad_animation(self):
        x=sample();x['animations'][0]['channels'][0]['target']['node']=42
        self.assertIn('invalid animation node',qualify(x)['errors'])
    def test_require_animation(self):
        x=sample();x['animations']=[]
        self.assertIn('no animation',qualify(x)['errors'])
        self.assertEqual(qualify(x,require_animation=False)['status'],'PASS_STRUCTURAL_ONLY')
    def test_glb_length_guard(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'t.glb';j=json.dumps(sample()).encode();j+=b' '*(-len(j)%4)
            b=b'glTF'+struct.pack('<II',2,20+len(j))+struct.pack('<I4s',len(j),b'JSON')+j
            p.write_bytes(b);self.assertEqual(load_glb(p),sample())
            p.write_bytes(b+b'BAD!')
            with self.assertRaises(ValueError):load_glb(p)
if __name__=='__main__':unittest.main()
