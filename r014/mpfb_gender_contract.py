"""Source-pinned MPFB phenotype macro contract; prevent swapped body labels.

The upstream property JSON is authoritative over prose examples. A matching
macro value alone does NOT validate reproductive anatomy or real-person identity.
"""
import argparse, hashlib, json, re, sys, unittest
from pathlib import Path

EXPECTED={"female":0.0,"male":1.0}

def read_contract(source:Path):
    prop_path=source/"entities/objectproperties/humanproperties/gender.json"
    target_path=source/"data/targets/macrodetails/macro.json"
    prop=json.loads(prop_path.read_text())
    macro=json.loads(target_path.read_text())
    assert prop.get("name")=="gender", "unexpected gender property"
    desc=prop.get("description","").lower()
    if not re.search(r"0\.0\s+is\s+female",desc) or not re.search(r"1\.0\s+is\s+male",desc):
        raise ValueError("gender macro source description changed; BLOCK")
    parts=macro.get("macrotargets",{}).get("gender",{}).get("parts",[])
    if len(parts)!=1 or parts[0].get("low")!="female" or parts[0].get("high")!="male":
        raise ValueError("gender macro target endpoints changed; BLOCK")
    return {"model":"MPFB body-shape macro ONLY","expected":EXPECTED,
            "source_property_sha256":hashlib.sha256(prop_path.read_bytes()).hexdigest(),
            "source_macro_sha256":hashlib.sha256(target_path.read_bytes()).hexdigest(),
            "source_property_description":prop["description"],
            "bounds":[parts[0].get("lowest"),parts[0].get("highest")]}

def verify_report(report, expected=EXPECTED):
    people=report.get("characters",[])
    if len(people)!=2 or {x.get("sex") for x in people}!=set(expected):
        raise ValueError("expected exactly one recorded female/male phenotype preset")
    for person in people:
        sex=person["sex"]
        macro=person.get("source_gender_macro")
        if type(macro) not in (int,float) or abs(macro-expected[sex])>1e-9:
            raise ValueError("reversed/unrecorded macro for "+sex)
        age=person.get("source_age_macro")
        if type(age) not in (int,float) or not 0.6<=age<=0.85:
            raise ValueError("intended adult-leaning age preset missing for "+sex)
    return True

class NegativeControls(unittest.TestCase):
    def setUp(self):
        self.fixture={"characters":[{"sex":"female","source_gender_macro":0.0,"source_age_macro":0.65},
                                    {"sex":"male","source_gender_macro":1.0,"source_age_macro":0.65}]}
    def test_correct_preset_pass(self):
        self.assertTrue(verify_report(self.fixture))
    def test_swapped_preset_rejected(self):
        for p in self.fixture["characters"]:p["source_gender_macro"]=1-p["source_gender_macro"]
        with self.assertRaises(ValueError):verify_report(self.fixture)
    def test_unrecorded_macro_rejected(self):
        del self.fixture["characters"][0]["source_gender_macro"]
        with self.assertRaises(ValueError):verify_report(self.fixture)
    def test_underage_leaning_macro_rejected(self):
        self.fixture["characters"][0]["source_age_macro"]=0.1
        with self.assertRaises(ValueError):verify_report(self.fixture)
    def test_duplicate_preset_rejected(self):
        self.fixture["characters"][1]["sex"]="female"
        with self.assertRaises(ValueError):verify_report(self.fixture)

def main():
    if "--self-test" in sys.argv:
        unittest.main(argv=[sys.argv[0]],verbosity=2)
        return
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--receipt",required=True,type=Path)
    p.add_argument("--report",type=Path)
    a=p.parse_args()
    c=read_contract(a.source)
    if a.report:
        verify_report(json.loads(a.report.read_text()))
        c["generated_character_preset_records"]="PASS_SOURCE_CONSISTENT"
    c["status"]="PASS_MPFB_MACRO_METADATA_ONLY"
    c["NOT_QUALIFIED"]=["Observed anatomical completeness","Genital topology",
        "Phenotypic variability or identity","Rendered sex/age perception",
        "Human realism or video-production acceptance"]
    a.receipt.parent.mkdir(parents=True,exist_ok=True)
    a.receipt.write_text(json.dumps(c,sort_keys=True,indent=2)+"\n")
    print("R014_MPFB_GENDER_CONTRACT",json.dumps(c,sort_keys=True))
if __name__=="__main__":
    main()
