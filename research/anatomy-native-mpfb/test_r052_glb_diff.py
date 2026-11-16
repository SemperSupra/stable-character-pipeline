"""Original tiny glTF fixtures; no donor assets or protected character content."""
import json
import os
import struct
import tempfile
import unittest
from pathlib import Path
from r052_glb_diff import compare

def glb(path,obj,buf=b"\x01\x02\x03\x04",pretty=False):
    source=json.dumps(obj,sort_keys=not pretty,
                      indent=2 if pretty else None,
                      separators=None if pretty else (",",":")).encode("utf-8")
    source+=b" "*((-len(source))%4)
    payload=buf+b"\0"*((-len(buf))%4)
    out=(struct.pack("<4sII",b"glTF",2,12+8+len(source)+8+len(payload))+
         struct.pack("<II",len(source),0x4e4f534a)+source+
         struct.pack("<II",len(payload),0x004e4942)+payload)
    Path(path).write_bytes(out)

class TestGLBForensics(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.a=os.path.join(self.temp.name,"a.glb")
        self.b=os.path.join(self.temp.name,"b.glb")
        self.obj={"asset":{"version":"2.0"},"meshes":[{"name":"synthetic"}],
                  "buffers":[{"byteLength":4}]}
        glb(self.a,self.obj)
    def tearDown(self):
        self.temp.cleanup()
    def test_identical_bytes(self):
        glb(self.b,self.obj)
        x=compare(self.a,self.b)
        self.assertEqual(x["classification"],"BYTE_IDENTICAL")
        self.assertFalse(x["whole_file_changed"])
    def test_json_format_only(self):
        glb(self.b,self.obj,pretty=True)
        x=compare(self.a,self.b)
        self.assertEqual(x["classification"],"SERIALIZATION_OR_PADDING_ONLY_DRIFT")
        self.assertEqual(x["json_changed_paths_limited"],[])
        self.assertFalse(x["binary_chunk_changed"])
    def test_json_meaning_changed(self):
        changed=json.loads(json.dumps(self.obj))
        changed["meshes"][0]["name"]="different"
        glb(self.b,changed)
        x=compare(self.a,self.b)
        self.assertEqual(x["classification"],"JSON_SEMANTIC_DRIFT")
        self.assertIn("$.meshes[0].name",x["json_changed_paths_limited"])
    def test_binary_changed(self):
        glb(self.b,self.obj,b"\x01\x02\x03\x05")
        x=compare(self.a,self.b)
        self.assertEqual(x["classification"],"BINARY_PAYLOAD_DRIFT")
        self.assertTrue(x["binary_chunk_changed"])
    def test_json_and_binary_changed(self):
        changed=dict(self.obj,extra=2)
        glb(self.b,changed,b"\x01\x02\x03\x05")
        self.assertEqual(compare(self.a,self.b)["classification"],
                         "JSON_AND_BINARY_SEMANTIC_DRIFT")
    def test_declared_length_corruption_rejected(self):
        glb(self.b,self.obj)
        payload=bytearray(Path(self.b).read_bytes())
        struct.pack_into("<I",payload,8,len(payload)+4)
        Path(self.b).write_bytes(payload)
        with self.assertRaises(ValueError):
            compare(self.a,self.b)
    def test_missing_chunk_rejected(self):
        glb(self.b,self.obj)
        raw=Path(self.b).read_bytes()
        raw=raw[:-12]
        raw=raw[:8]+struct.pack("<I",len(raw))+raw[12:]
        Path(self.b).write_bytes(raw)
        with self.assertRaises(ValueError):
            compare(self.a,self.b)
    def test_diagnostics_never_contain_raw_changed_value(self):
        changed=dict(self.obj,secret="DO_NOT_EMIT_CHARACTER_VALUE")
        glb(self.b,changed)
        x=compare(self.a,self.b)
        self.assertNotIn("DO_NOT_EMIT_CHARACTER_VALUE",json.dumps(x))
        self.assertIn("$.secret:membership",x["json_changed_paths_limited"])

if __name__=="__main__":
    unittest.main()
