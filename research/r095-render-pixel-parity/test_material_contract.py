import copy
import unittest
from material_contract import validate_manifest, EXPECTED

def example():
    return {"schema":"scp.r095.materials.v1","version":"5.2.4","render":"CYCLES_CPU_8SPP","view_transform":"Standard",
            "objects":{name:{"material":spec["material"],"use_nodes":True,"shader":"ShaderNodeBsdfPrincipled",
                             "surface_connected":True,"color":list(spec["color"]),"roughness":spec["roughness"]}
                       for name,spec in EXPECTED.items()}}

class MaterialContractTest(unittest.TestCase):
    def test_positive(self):
        self.assertTrue(validate_manifest(example(),"5.2.4"))
    def test_missing_floor(self):
        x=example();del x["objects"]["SyntheticFloor"]
        with self.assertRaises(ValueError):validate_manifest(x,"5.2.4")
    def test_implicit_fallback(self):
        x=example();x["objects"]["SyntheticFloor"]["use_nodes"]=False
        with self.assertRaises(ValueError):validate_manifest(x,"5.2.4")
    def test_disconnected_surface(self):
        x=example();x["objects"]["SyntheticMovingSkin"]["surface_connected"]=False
        with self.assertRaises(ValueError):validate_manifest(x,"5.2.4")
    def test_wrong_version(self):
        with self.assertRaises(ValueError):validate_manifest(example(),"5.3.0")
    def test_nonfinite(self):
        x=example();x["objects"]["SyntheticFloor"]["roughness"]=float("nan")
        with self.assertRaises(ValueError):validate_manifest(x,"5.2.4")
    def test_changed_color(self):
        x=example();x["objects"]["SyntheticFloor"]["color"][0]=0.6
        with self.assertRaises(ValueError):validate_manifest(x,"5.2.4")
    def test_implicit_different_shader(self):
        x=example();x["objects"]["SyntheticFloor"]["shader"]="ShaderNodeBsdfDiffuse"
        with self.assertRaises(ValueError):validate_manifest(x,"5.2.4")
if __name__=="__main__":unittest.main()
