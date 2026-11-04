import copy,json,struct,tempfile,unittest
from pathlib import Path
from generate_original_glb import make_demo
from verify_original_glb import decode,verify,WitnessError

class OriginalOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.p=Path(cls.tmp.name)/'ok.glb';make_demo(cls.p)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def test_accept_author_generated_glb(self):
        r=verify(self.p)
        self.assertEqual(r['characters'],2);self.assertGreater(r['blended_vertices'],300)
    def mutate_json(self,change):
        raw=self.p.read_bytes();d,b=decode(raw);change(d)
        text=json.dumps(d,sort_keys=True,separators=(',',':')).encode();text+=b' '*((-len(text))%4)
        out=struct.pack('<4sII',b'glTF',2,12+8+len(text)+8+len(b))+struct.pack('<I4s',len(text),b'JSON')+text+struct.pack('<I4s',len(b),b'BIN\0')+b
        q=Path(self.tmp.name)/'bad.glb';q.write_bytes(out)
        with self.assertRaises(WitnessError):verify(q)
    def test_missing_original_figure(self):self.mutate_json(lambda d:d['skins'].pop())
    def test_fabricated_rights_source(self):self.mutate_json(lambda d:d['extras'].update(third_party_models=True))
    def test_fabricated_human_gait_acceptance(self):self.mutate_json(lambda d:d['extras'].update(human_gait_acceptance='PASS'))
    def test_rig_joint_count_short(self):self.mutate_json(lambda d:d['skins'][0]['joints'].pop())
    def test_missing_animation_channel(self):self.mutate_json(lambda d:d['animations'][0]['channels'].clear())
    def test_insufficient_mesh(self):self.mutate_json(lambda d:d['meshes'][0]['primitives'].clear())
    def test_missing_skin_weights(self):self.mutate_json(lambda d:d['meshes'][0]['primitives'][0]['attributes'].pop('WEIGHTS_0'))
    def test_invalid_total_size(self):
        raw=bytearray(self.p.read_bytes());struct.pack_into('<I',raw,8,len(raw)+1)
        q=Path(self.tmp.name)/'badlength.glb';q.write_bytes(raw)
        with self.assertRaises(WitnessError):verify(q)

if __name__=='__main__':unittest.main()
