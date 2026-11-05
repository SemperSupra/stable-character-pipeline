import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path
from check_horse import inspect

def synthetic_asset():
    obj={"asset":{"version":"2.0"},"skins":[{"joints":[1]}],"meshes":[{"primitives":[]}],
         "animations":[{"name":f"clip{i}","channels":[{"sampler":0,"target":{"node":1,"path":"rotation"}}]} for i in range(10)]}
    b=json.dumps(obj).encode()
    b+=b" " *((-len(b))%4)
    return b"glTF"+struct.pack("<II",2,20+8+len(b))+struct.pack("<II",len(b),0x4E4F534A)+b

class SourceTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/"file.glb"
        self.payload=synthetic_asset()
        self.path.write_bytes(self.payload)
        self.desc={"size_bytes":len(self.payload),"git_blob_sha1":hashlib.sha1(b"blob "+str(len(self.payload)).encode()+b"\0"+self.payload).hexdigest()}
    def tearDown(self):
        self.temp.cleanup()
    def test_valid_fixture(self):
        self.assertEqual(inspect(self.path,self.desc)["animation_count"],10)
    def test_tamper(self):
        self.path.write_bytes(self.payload+b"forgery")
        with self.assertRaises(AssertionError):
            inspect(self.path,self.desc)
    def test_wrong_sha(self):
        self.desc["git_blob_sha1"]="0"*40
        with self.assertRaises(AssertionError):
            inspect(self.path,self.desc)
    def test_too_few_animations(self):
        self.assertEqual(inspect(self.path,self.desc)["retarget_state"],"NOT_RUN")
if __name__=="__main__":
    unittest.main()
