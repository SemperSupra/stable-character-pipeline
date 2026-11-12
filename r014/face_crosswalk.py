"""R014 source-pinned MHR/MPFB face-control interface inventory.
No asset-pack downloads, medical/FACS acceptance or inferred 1:1 coverage.
"""
import argparse,ast,json
from pathlib import Path

DIRECT_CANDIDATES={
    "eyesClosed_L":"eyeBlinkLeft","eyesClosed_R":"eyeBlinkRight",
    "jawDrop":"jawOpen","jawThrust":"jawForward",
    "jawSidewaysLeft":"jawLeft","jawSidewaysRight":"jawRight",
    "mouthLeft":"mouthLeft","mouthRight":"mouthRight",
    "cheekPuff_L":"cheekPuff","cheekPuff_R":"cheekPuff",
    "innerBrowRaiser_L":"browInnerUp","innerBrowRaiser_R":"browInnerUp",
    "lipCornerPuller_L":"mouthSmileLeft","lipCornerPuller_R":"mouthSmileRight",
    "lipCornerDepressor_L":"mouthFrownLeft","lipCornerDepressor_R":"mouthFrownRight",
    "lipPucker_L":"mouthPucker","lipPucker_R":"mouthPucker",
}
# These are only semantic suggestions, NOT validated response equivalence or a
# substitute for direct learned/artist-certified transfer curves.
def static_declared_sequence(path,name):
    tree=ast.parse(Path(path).read_text())
    for node in tree.body:
        if isinstance(node,ast.AnnAssign) and isinstance(node.target,ast.Name) and node.target.id==name:
            return list(ast.literal_eval(node.value))
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name) and target.id==name:
                    return list(ast.literal_eval(node.value))
    raise ValueError("missing source constant "+name+" in "+str(path))

def assemble(mhr,mpfb):
    errors=[]
    if len(mhr)!=72 or len(set(mhr))!=72:errors.append("MHR_72_DISTINCT_REQUIRED")
    if len(mpfb)!=52 or len(set(mpfb))!=52:errors.append("MPFB_52_DISTINCT_REQUIRED")
    if errors:raise ValueError(",".join(errors))
    table=[{"mhr_name":name,"mhr_coefficient":i,"mhr_fbx_morph":"shape_"+str(45+i),
            "mpfb_semantic_candidate":DIRECT_CANDIDATES.get(name),
            "transfer_status":"UNQUALIFIED_SEMANTIC_SUGGESTION" if name in DIRECT_CANDIDATES else "UNMAPPED"}
            for i,name in enumerate(mhr)]
    missing=[x for x in table if x["mpfb_semantic_candidate"] not in mpfb
             and x["mpfb_semantic_candidate"] is not None]
    if missing:raise ValueError("crosswalk references nonexisting controls: "+str(missing))
    return {"status":"PASS_SOURCE_INVENTORY_ONLY","mhr_expression_count":len(mhr),
            "mpfb_arkit_count":len(mpfb),
            "mhr_identity_coefficient_count":45,
            "mhr_total_nonbasis_shape_keys_expected":117,
            "mapped_semantic_suggestions":sum(x["mpfb_semantic_candidate"] is not None for x in table),
            "controls":table,
            "limitations":["MHR expression shapes follow FACS but do not correspond 1:1 to FACS AUs",
                           "MPFB ARKit faceunits require separately installed faceunits01 target pack",
                           "FACS/ARKit mapping semantics and response amplitudes must be independently calibrated",
                           "No native video, close-up acting or eye/lip physical realism assessed"]}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--mhr",type=Path,required=True)
    p.add_argument("--mpfb",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    mhr=static_declared_sequence(args.mhr,"FACE_EXPRESSION_NAMES")
    mpfb=static_declared_sequence(args.mpfb,"ARKIT_FACEUNITS")
    results=assemble(mhr,mpfb)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(results,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:v for k,v in results.items() if k!="controls"},sort_keys=True))
