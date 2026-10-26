"""Regression and adversarial tests for synthetic flora/fauna animation binding."""
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).parent))
import ecology_binding as bridge

MODEL="67b503b6903de319739ea35a456dea270739f6fde30938e6c555de6451da972a"

def fixture():
    mapping=json.loads(Path("examples/ecology_scene_map.json").read_text())
    patches=[{"id":k,"biomass_g":160,"capacity_g":200}
             for k in sorted(mapping["patch_positions"])]
    animals=[{"id":name,"kind":meta["kind"],"patch":"paddy-west"}
             for name,meta in sorted(mapping["actor_nodes"].items())]
    frames=[]
    for tick in range(1,4):
        pp=copy.deepcopy(patches)
        for p in pp:
            p["biomass_g"]+=tick*2
        aa=copy.deepcopy(animals)
        if tick==2:
            aa[0]["patch"]="paddy-east"
        frames.append({"tick":tick,"patches":pp,"animals":aa,"events":[]})
    report={"schema":"scp.ecology.v1","frames":frames,"scenario":"unit",
        "seed":26,"fidelity":"earth_prototype","ledger":{
        "initial_g":480,"regrowth_g":18,"consumed_g":0,
        "final_g":498,"balanced":True}}
    report["digest_sha256"]=hashlib.sha256(json.dumps(
        {"frames":frames,"ledger":report["ledger"]},separators=(",",":")).encode()).hexdigest()
    return report,mapping

class BindingTests(unittest.TestCase):
    def test_repeatable(self):
        report,mapping=fixture()
        a=bridge.compile_binding(report,mapping,MODEL)
        b=bridge.compile_binding(copy.deepcopy(report),copy.deepcopy(mapping),MODEL)
        self.assertEqual(a,b)
        self.assertEqual(len(a["frames"]),48)
        self.assertEqual(a["frames"][-1]["ecology_tick"],3)
        self.assertEqual(len(a["frames"][0]["actors"]),6)
        self.assertEqual(len(a["frames"][0]["patches"]),3)
        self.assertNotEqual(a["frames"][0]["patches"][0]["ratio"],a["frames"][-1]["patches"][0]["ratio"])
        for before,after in zip(a["frames"],a["frames"][1:]):
            previous={p["id"]:p["offset"] for p in before["actors"]}
            for actor in after["actors"]:
                dist=sum((x-y)**2 for x,y in zip(actor["offset"],previous[actor["id"]]))**.5
                self.assertLessEqual(dist,2/12+1e-4)
    def test_digest_attack(self):
        report,mapping=fixture()
        report["frames"][0]["patches"][0]["biomass_g"]=999
        with self.assertRaises(ValueError):
            bridge.compile_binding(report,mapping,MODEL)
    def test_wrong_model(self):
        report,mapping=fixture()
        with self.assertRaises(ValueError):
            bridge.compile_binding(report,mapping,"0"*64)
    def test_missing_actor(self):
        report,mapping=fixture()
        del mapping["actor_nodes"]["egret-a"]
        with self.assertRaises(ValueError):
            bridge.compile_binding(report,mapping,MODEL)
    def test_ledger_attack(self):
        report,mapping=fixture()
        report["ledger"]["final_g"]+=12
        with self.assertRaises(ValueError):
            bridge.compile_binding(report,mapping,MODEL)
    def test_bounds(self):
        report,mapping=fixture()
        with self.assertRaises(ValueError):
            bridge.compile_binding(report,mapping,MODEL,count=500)
        mapping["actor_nodes"]["egret-a"]["node"]=mapping["actor_nodes"]["egret-b"]["node"]
        with self.assertRaises(ValueError):
            bridge.compile_binding(report,mapping,MODEL)
    def test_speculative_label(self):
        report,mapping=fixture()
        report["fidelity"]="speculative"
        self.assertEqual(bridge.compile_binding(report,mapping,MODEL)["fidelity"],"speculative")

if __name__=="__main__":
    unittest.main()
