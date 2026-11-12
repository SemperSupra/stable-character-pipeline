"""Pinned research inventory of public anatomical GLB reference candidates.

Do not relicense BodyParts3D/OrganUI under MIT: application code and anatomy
data have different legal terms. This does not bind organs to human skin meshes.
"""
import argparse,hashlib,json,struct,sys,unittest
from pathlib import Path

PROFILES={
  "male":{
    "license":"CC-BY-SA-2.1-JP","runtime":"prostate.glb",
    "components":["glans-penis","prostate","testes","urethra"],
    "source_credit":"BodyParts3D",
    "integration_status":"HOLD_SHAREALIKE_DERIVATIVE_REVIEW",
    "unverified_external":["scrotal_skin","penile_skin","foreskin_variant","perineal_surface"]
  },
  "female":{
    "license":"CC-BY-4.0","runtime":"reproductive.glb",
    "components":["vagina","cervix","left-ovary","right-ovary"],
    "source_credit":"HuBMAP",
    "integration_status":"REFERENCE_ONLY_NOT_RIGGED",
    "unverified_external":["labia_majora","labia_minora","clitoral_hood","clitoral_glans",
                           "external_urethral_opening","vestibule","perineal_surface"]
  }
}
def glb_header(path):
    with path.open("rb") as f:
        h=f.read(12)
        if len(h)!=12:raise ValueError("invalid GLB header length")
        magic,version,length=struct.unpack("<4sII",h)
        if magic!=b"glTF" or version!=2 or length!=path.stat().st_size:
            raise ValueError("GLB v2 length or magic mismatch")
        chunk=f.read(8)
        if len(chunk)!=8:raise ValueError("missing JSON chunk")
        count,kind=struct.unpack("<I4s",chunk)
        if kind!=b"JSON" or count%4:raise ValueError("bad GLB JSON chunk")
        data=f.read(count)
        if len(data)!=count:raise ValueError("truncated GLB JSON")
        doc=json.loads(data.decode("utf-8"))
    if not doc.get("meshes") or not doc.get("nodes"):
        raise ValueError("no renderable geometry")
    return {"nodes":len(doc["nodes"]),"meshes":len(doc["meshes"]),
            "named_nodes":sum(bool(n.get("name")) for n in doc["nodes"])}

def evaluate_manifest(manifest,attr,code_license,sex):
    spec=PROFILES[sex]
    if manifest.get("license")!=spec["license"]:
        raise ValueError("Anatomy data license mismatch")
    if not spec["source_credit"].lower() in attr.lower():
        raise ValueError("Attribution missing source institution")
    if "MIT License" not in code_license:
        raise ValueError("Expected separate MIT application code")
    if manifest.get("runtime",{}).get("file")!=spec["runtime"]:
        raise ValueError("Wrong GLB runtime")
    components={x["id"] for x in manifest.get("structures",[])}
    missing=set(spec["components"])-components
    if missing:raise ValueError("Required reference components missing: "+str(missing))
    if not manifest["runtime"].get("sha256"):
        raise ValueError("No immutable reference mesh hash")
    return spec

def run(args):
    root=args.root
    manifest=json.loads((root/"public/models/manifest.json").read_text())
    attribution=(root/"public/models/ATTRIBUTION.md").read_text()
    code=(root/"LICENSE").read_text()
    spec=evaluate_manifest(manifest,attribution,code,args.sex)
    glb_path=root/"public/models"/spec["runtime"]
    sha=hashlib.sha256(glb_path.read_bytes()).hexdigest()
    if sha!=manifest["runtime"]["sha256"]:
        raise ValueError("GLB model bytes disagree with upstream manifest")
    if glb_path.stat().st_size!=manifest["runtime"]["bytes"]:
        raise ValueError("GLB byte size mismatch")
    mesh=glb_header(glb_path)
    structures=manifest["structures"]
    data={
      "status":"PASS_REFERENCE_ASSET_HASH_AND_ANATOMY_INVENTORY_ONLY",
      "subject":args.sex,"repo":args.repo,"source_revision":args.sha,
      "model_sha256":sha,"model_bytes":glb_path.stat().st_size,
      "model_license":spec["license"],"software_license":"MIT",
      "source_credit":spec["source_credit"],
      "total_structures":len(structures),
      "source_elements":sum(len(x.get("elements",x.get("nodes",[]))) for x in structures),
      "required_reference_structures_present":spec["components"],
      "unverified_external_anatomy":spec["unverified_external"],
      "glb_counts":mesh,
      "integration_status":spec["integration_status"],
      "rights_and_quality_holds":[
        "Not integrated, sculpted, skinned or dynamically constrained to MPFB/MHR",
        "No per-region cinematic external genital acceptance",
        "ShareAlike anatomical license cannot silently become CC0/MIT",
        "Source models are educational anatomical reference, not personalized geometry",
        "Source coordinates were recentered/rescaled and require independent unit and alignment validation"
      ]
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
    print("R014_ANATOMY_SOURCE",json.dumps({k:v for k,v in data.items() if k not in ("rights_and_quality_holds",)},sort_keys=True))
class NegativeControls(unittest.TestCase):
    def sample(self,sex):
        spec=PROFILES[sex]
        return {"license":spec["license"],
                "runtime":{"file":spec["runtime"],"sha256":"123"},
                "structures":[{"id":s} for s in spec["components"]]}
    def test_male_license_valid(self):
        self.assertTrue(evaluate_manifest(self.sample("male"),"BodyParts3D CC BY-SA 2.1 Japan","MIT License","male"))
    def test_female_license_valid(self):
        self.assertTrue(evaluate_manifest(self.sample("female"),"HuBMAP CC BY 4.0","MIT License","female"))
    def test_code_license_not_data_license(self):
        x=self.sample("male");x["license"]="MIT"
        with self.assertRaises(ValueError):evaluate_manifest(x,"BodyParts3D","MIT License","male")
    def test_reproductive_missing_structure_reject(self):
        x=self.sample("female");x["structures"]=[]
        with self.assertRaises(ValueError):evaluate_manifest(x,"HuBMAP","MIT License","female")
    def test_mismatched_anatomy_source(self):
        with self.assertRaises(ValueError):evaluate_manifest(self.sample("male"),"HuBMAP","MIT License","male")

if __name__=="__main__":
    if "--self-test" in sys.argv:
        unittest.main(argv=[sys.argv[0]],verbosity=2)
    else:
        p=argparse.ArgumentParser()
        p.add_argument("--root",type=Path,required=True)
        p.add_argument("--sex",choices=list(PROFILES),required=True)
        p.add_argument("--repo",required=True)
        p.add_argument("--sha",required=True)
        p.add_argument("--out",type=Path,required=True)
        run(p.parse_args())
