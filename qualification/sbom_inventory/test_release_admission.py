import importlib.util
import pathlib
import unittest

HERE=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location("observed",HERE/"observed.py")
inventory=importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)
spec2=importlib.util.spec_from_file_location("release_admission",HERE/"release_admission.py")
admission=importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(admission)
PIP="\n".join(["bpy==4.5.0","numpy==1.26.4","certifi==2026.10.23","cython==3.3.0","requests==2.34.2","zstandard==0.25.0","urllib3==2.8.0","idna==3.20","charset-normalizer==3.5.2"])+"\n"
DEB="\n".join(["ffmpeg\t7:5.1.9"]+["libsample"+str(i)+":amd64\t1.0-1" for i in range(149)])
def candidate():
    return inventory.create(PIP,DEB,"a"*40,inventory.BASE,"sha256:"+"b"*64)
class SupplyAdmission(unittest.TestCase):
    def test_real_generator_to_independent_hold(self):
        result=admission.inspect(candidate())
        self.assertEqual(result["component_count"],159)
        self.assertEqual(result["unverified_components"],159)
        self.assertTrue(result["status"].startswith("HOLD_"))
    def test_attempted_promotion_rejected(self):
        b=candidate()
        b["metadata"]["properties"][0]["value"]="PASS"
        with self.assertRaisesRegex(ValueError,"UNAUTHORIZED_PROMOTION"):
            admission.inspect(b)
    def test_duplicate_component_rejected(self):
        b=candidate()
        b["components"].append(b["components"][0])
        with self.assertRaisesRegex(ValueError,"DUPLICATE_COMPONENT"):
            admission.inspect(b)
    def test_missing_inventory_rejected(self):
        b=candidate()
        b["components"]=b["components"][:100]
        with self.assertRaisesRegex(ValueError,"INCOMPLETE"):
            admission.inspect(b)
    def test_duplicate_property_rejected(self):
        b=candidate()
        b["metadata"]["properties"].append(b["metadata"]["properties"][0])
        with self.assertRaisesRegex(ValueError,"DUPLICATE_PROPERTIES"):
            admission.inspect(b)
if __name__=="__main__":unittest.main()
