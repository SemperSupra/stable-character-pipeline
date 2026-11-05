"""CLI/agent parity tests are independent of any Blender installation."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from wardrobe_console_v2 import inspect,plan_blender,main,SCHEMA
from modular_wardrobe_v1 import PRESETS,ACTORS

class ConsoleTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.dir=Path(self.t.name)
        self.data=self.dir/"input.glb"
        self.data.write_bytes(b"test source")
        self.m=self.dir/"contract.json"
        self.doc={
           "schema":"scp.original_wardrobe_manifest.v1",
           "subjects":list(ACTORS),
           "presets":{k:list(v) for k,v in PRESETS.items()},
           "actor_slots":{a:{s:{"node":n} for n,s in enumerate(("body","hair","top","bottom","alt_top","alt_bottom"))} for a in ACTORS},
           "derived_sha256":hashlib.sha256(self.data.read_bytes()).hexdigest(),
           "separate_new_geometry_for_alternate":True}
        self.m.write_text(json.dumps(self.doc))
    def test_source_bound_inspection(self):
        r=inspect(self.m,self.data)
        self.assertEqual(r["schema"],SCHEMA)
        self.assertTrue(r["independent_alt_cuts"])
        self.assertFalse(r["human_appearance_accepted"])
        self.assertEqual(r["presets"]["unclothed"],["body","hair"])
    def test_forged_manifest_fails_closed(self):
        self.doc["derived_sha256"]="0"*64
        self.m.write_text(json.dumps(self.doc))
        with self.assertRaisesRegex(ValueError,"SOURCE_MANIFEST_SHA_MISMATCH"):
            inspect(self.m,self.data)
    def test_preset_drift_fails_closed(self):
        self.doc["presets"]["alternate"]=["body","hair","top"]
        self.m.write_text(json.dumps(self.doc))
        with self.assertRaisesRegex(ValueError,"PRESET_CONTRACT_DRIFT"):
            inspect(self.m)
    def test_exact_non_destructive_blender_argv(self):
        path=self.dir/"source.blend"
        path.write_bytes(b"fake editable source for argv planning")
        out=self.dir/"derived.blend"
        receipt=self.dir/"derived.json"
        result=plan_blender(path,out,receipt,"alternate","AsterOriginal")
        self.assertEqual(result["argv"][0],"blender")
        self.assertIn("--python-exit-code",result["argv"])
        self.assertIn("--actor",result["argv"])
        self.assertEqual(result["argv"][-6:],
             ["--actor","AsterOriginal","--out",str(out),"--receipt",str(receipt)])
        self.assertTrue(result["source_unchanged_required"])
        self.assertEqual(path.read_bytes(),b"fake editable source for argv planning")
    def test_path_collision_and_actor_falsifier(self):
        path=self.dir/"source.blend"
        path.write_bytes(b"existing")
        with self.assertRaisesRegex(ValueError,"SOURCE_OVERWRITE_REFUSED"):
            plan_blender(path,path,self.dir/"receipt.json","signature","all")
        with self.assertRaisesRegex(ValueError,"UNKNOWN_ACTOR"):
            plan_blender(path,self.dir/"out.blend",self.dir/"rcpt.json","signature","Intruder")
    def test_cli_inspect_returns_same_contract(self):
        value=main(["inspect","--manifest",str(self.m),"--input",str(self.data)])
        self.assertEqual(value["presets"],inspect(self.m,self.data)["presets"])

if __name__=="__main__":unittest.main()
