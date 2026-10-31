import importlib.util,json
from pathlib import Path
import unittest
source=Path(__file__).with_name("observed.py")
spec=importlib.util.spec_from_file_location("inventory",source)
inv=importlib.util.module_from_spec(spec);spec.loader.exec_module(inv)
def pip():
    return "\n".join(["bpy==4.5.0","numpy==1.26.4","certifi==2026.10.23",
                       "cython==3.3.0","requests==2.34.2","zstandard==0.25.0",
                       "urllib3==2.8.0","idna==3.20","charset-normalizer==3.5.2"])+"\n"
def deb():
    return "\n".join(["ffmpeg\t7:5.1.9","libdummy"+str(i)+":amd64\t1.0-1" for i in range(149)])
def model(pip_text=None,deb_text=None,base=None):
    return inv.create(pip() if pip_text is None else pip_text,
        deb() if deb_text is None else deb_text,"a"*40,
        inv.BASE if base is None else base,"sha256:"+"b"*64)
class InventoryTests(unittest.TestCase):
    def test_stable_cyclonedx_complete_inventory_and_unknowns(self):
        a=model();b=model()
        self.assertEqual(a,b)
        self.assertEqual(a["bomFormat"],"CycloneDX")
        self.assertEqual(a["specVersion"],"1.6")
        self.assertEqual(len(a["components"]),159)
        self.assertEqual(len({c["bom-ref"] for c in a["components"]}),159)
        self.assertEqual(a["metadata"]["properties"][0]["value"],"UNKNOWN_NOT_RELEASE_QUALIFIED")
        self.assertTrue(all("hashes" not in c and "licenses" not in c for c in a["components"]))
        self.assertTrue(all(c["properties"][1]["value"]=="UNKNOWN_NOT_REVIEWED" for c in a["components"]))
        self.assertNotIn("private",json.dumps(a).lower().replace("private-r009",""))
    def test_original_amd64_digest_is_exact(self):
        with self.assertRaisesRegex(ValueError,"BASE_IMAGE_NOT_PINNED"):
            model(base="sha256:"+"c"*64)
    def test_pip_evil_direct_url_rejected(self):
        with self.assertRaisesRegex(ValueError,"NONPINNED_PYTHON_REQUIREMENT"):
            model(pip_text=pip()+"bpy @ https://example.invalid/evil.whl\n")
    def test_python_duplicate_normalized_name_rejected(self):
        with self.assertRaisesRegex(ValueError,"DUPLICATE_PYTHON_PACKAGE"):
            model(pip_text=pip()+"charset_normalizer==3.5.2\n")
    def test_core_bpy_version_drift_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"CORE_BLENDER_DEPENDENCY_DRIFT"):
            model(pip_text=pip().replace("bpy==4.5.0","bpy==4.5.1"))
    def test_debian_missing_ffmpeg_denied(self):
        with self.assertRaisesRegex(ValueError,"DEBIAN_INVENTORY_INCOMPLETE"):
            model(deb_text=deb().replace("ffmpeg\t7:5.1.9","otherpkg\t1.0"))
    def test_debian_duplicate_denied(self):
        with self.assertRaisesRegex(ValueError,"DUPLICATE_DEBIAN_PACKAGE"):
            model(deb_text=deb()+"\nffmpeg\t7:5.1.9")
    def test_unsafe_source_sha_denied(self):
        with self.assertRaisesRegex(ValueError,"SOURCE_SHA_INVALID"):
            inv.create(pip(),deb(),"../private",inv.BASE,"sha256:"+"b"*64)
    def test_local_image_id_is_not_registry_attestation(self):
        with self.assertRaisesRegex(ValueError,"LOCAL_IMAGE_ID_INVALID"):
            inv.create(pip(),deb(),"a"*40,inv.BASE,"some-tag:latest")
if __name__=="__main__":unittest.main()
