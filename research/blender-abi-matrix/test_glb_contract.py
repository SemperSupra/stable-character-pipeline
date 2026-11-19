"""Untrusted GLB structure cases; pure stdlib test, no Blender installation needed."""
import json,struct,tempfile,unittest,sys
from pathlib import Path

def parse_glb(path):
 b=Path(path).read_bytes()
 if len(b)<24 or b[:4]!=b"glTF" or struct.unpack_from("<I",b,4)[0]!=2:raise ValueError("BAD_HEADER")
 if struct.unpack_from("<I",b,8)[0]!=len(b):raise ValueError("WRONG_LENGTH")
 n,t=struct.unpack_from("<II",b,12)
 if t!=0x4E4F534A or n<=0 or 20+n>len(b):raise ValueError("BAD_CHUNK")
 data=json.loads(b[20:20+n])
 if not data.get("meshes") or not data.get("skins") or not data.get("animations"):
  raise ValueError("MISSING_REQUIRED_DATA")
 return data
def original_fixture():
 d={"asset":{"version":"2.0"},"meshes":[{"primitives":[{"attributes":{"POSITION":0},"targets":[{"POSITION":1}]}]}],"skins":[{"joints":[0,1]}],"animations":[{"channels":[{"sampler":0,"target":{"node":0,"path":"rotation"}}]}]}
 js=json.dumps(d).encode()
 js+=b" " *((-len(js))%4)
 total=20+len(js)
 return b"glTF"+struct.pack("<II",2,total)+struct.pack("<II",len(js),0x4E4F534A)+js
class GLB(unittest.TestCase):
 def check(self,b):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"fixture.glb";p.write_bytes(b)
   return parse_glb(p)
 def test_control(self):self.assertEqual(len(self.check(original_fixture())["skins"]),1)
 def test_bad_magic(self):
  b=bytearray(original_fixture());b[0]=0
  with self.assertRaises(ValueError):self.check(b)
 def test_bad_byte_length(self):
  b=bytearray(original_fixture());b[8]=0
  with self.assertRaises(ValueError):self.check(b)
 def test_no_skin(self):
  b=original_fixture().replace(b'"skins"',b'"xxxxx"')
  with self.assertRaises(ValueError):self.check(b)
 def test_no_animation(self):
  b=original_fixture().replace(b'"animations"',b'"xxxxxxxxxx"')
  with self.assertRaises(ValueError):self.check(b)
 def test_no_mesh(self):
  b=original_fixture().replace(b'"meshes"',b'"xxxxxx"')
  with self.assertRaises(ValueError):self.check(b)
if __name__=="__main__":unittest.main()
