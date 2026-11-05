"""Offline standard-library negative controls for non-destructive fictional heading overlay."""
import hashlib,json,struct,tempfile,unittest
from pathlib import Path
from heading_overlay import produce,Reject,decode

def fixture():
    nodes=[{'name':'AsterOriginal_SceneRoot'}, {'name':'JuniperOriginal_SceneRoot'}]+[{'name':f'joint-{i}'} for i in range(34)]
    ch=[{'sampler':0,'target':{'node':0,'path':'translation'}},{'sampler':0,'target':{'node':1,'path':'translation'}}]
    ch += [{'sampler':0,'target':{'node':2+i,'path':'rotation'}} for i in range(20)]
    return {'asset':{'version':'2.0'},'extras':{'source_class':'ORIGINAL_SELF_AUTHORED_SYNTHETIC','third_party_models':False},
      'nodes':nodes,'skins':[{'joints':list(range(2,19))},{'joints':list(range(19,36))}],
      'meshes':[],'animations':[{'channels':ch,'samplers':[]}],
      'buffers':[{'byteLength':4}],'bufferViews':[],'accessors':[]}

def glb(j):
    jb=json.dumps(j,separators=(',',':')).encode();jb+=b' '*((-len(jb))%4)
    binary=b'\0\0\0\0';return struct.pack('<4sII',b'glTF',2,12+8+len(jb)+8+len(binary))+struct.pack('<I4s',len(jb),b'JSON')+jb+struct.pack('<I4s',4,b'BIN\0')+binary

class HeadingOverlayTests(unittest.TestCase):
    def setUp(self):
      self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.src=self.root/'source.glb';self.out=self.root/'output.glb';self.rec=self.root/'receipt.json'
      self.save(fixture())
    def tearDown(self):self.tmp.cleanup()
    def save(self,j):self.src.write_bytes(glb(j));self.sha=hashlib.sha256(self.src.read_bytes()).hexdigest()
    def run_ok(self):return produce(self.src,self.out,self.rec,self.sha)
    def fail(self,code):
       with self.assertRaisesRegex(Reject,code):self.run_ok()
       self.assertFalse(self.out.exists());self.assertFalse(self.rec.exists())
    def test_success_roots_animated_source_untouched(self):
       r=self.run_ok();a,b=decode(self.out.read_bytes());self.assertEqual(r['source_sha256'],self.sha)
       self.assertEqual(a['nodes'][0]['rotation'][1],-0.7071067811865475)
       self.assertEqual(a['nodes'][1]['rotation'][1],0.7071067811865475)
       self.assertEqual(a['animations'][0]['channels'],fixture()['animations'][0]['channels'])
       self.assertEqual(self.sha,hashlib.sha256(self.src.read_bytes()).hexdigest())
       self.assertEqual(b,b'\0\0\0\0')
    def test_wrong_sha_rejected(self):
       self.sha='0'*64;self.fail('SOURCE_SHA256_MISMATCH')
    def test_source_not_original(self):
       d=fixture();d['extras']['third_party_models']=True;self.save(d);self.fail('SOURCE_NOT_ORIGINAL_FICTIONAL')
    def test_short_skin(self):
       d=fixture();d['skins'][0]['joints'].pop();self.save(d);self.fail('EXPECTED_SKINS_MISSING')
    def test_missing_root(self):
       d=fixture();d['nodes'][0]['name']='Other';self.save(d);self.fail('MISSING_SOURCE_ROOT')
    def test_duplicate_root(self):
       d=fixture();d['nodes'][2]['name']='AsterOriginal_SceneRoot';self.save(d);self.fail('DUPLICATE_SOURCE_ROOT')
    def test_existing_root_rotation(self):
       d=fixture();d['nodes'][0]['rotation']=[0,0,0,1];self.save(d);self.fail('ROOT_ALREADY_ROTATED')
    def test_existing_root_matrix(self):
       d=fixture();d['nodes'][0]['matrix']=[1]*16;self.save(d);self.fail('ROOT_ALREADY_ROTATED')
    def test_animated_root_rotation(self):
       d=fixture();d['animations'][0]['channels'].append({'sampler':0,'target':{'node':0,'path':'rotation'}});self.save(d);self.fail('ROOT_ROTATION_ANIMATED')
    def test_missing_translation(self):
       d=fixture();d['animations'][0]['channels'][0]['target']['path']='scale';self.save(d);self.fail('MISSING_ROOT_TRANSLATION')
    def test_same_source_and_output_refused(self):
       with self.assertRaisesRegex(Reject,'PATHS_MUST_BE_DISTINCT'):produce(self.src,self.src,self.rec,self.sha)
    def test_truncated_glb(self):
       self.src.write_bytes(self.src.read_bytes()[:-1]);self.sha=hashlib.sha256(self.src.read_bytes()).hexdigest();self.fail('GLB_BAD_LENGTH')

if __name__=='__main__':unittest.main()
