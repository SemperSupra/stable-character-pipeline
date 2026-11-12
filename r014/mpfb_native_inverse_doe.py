"""Source-native MPFB inverse-morphology experiment: make 72 REAL adult geometry samples.

Each of two independent shard jobs changes official MakeHuman body macros and
measures actually evaluated Blender mesh surfaces, not a synthetic formula.
Compare an actual learned CPU inverse regressor against mean and 1-NN; do not
reinterpret this as text-to-human or validated physical dimensions.
"""
import argparse
import hashlib
import importlib
import json
import math
import sys
from pathlib import Path

import bpy
import addon_utils
import numpy as np

SOURCE="6ff1eb358f6c1959ced77e79e6dd2406d9a71f49"
MACROS=("height","weight","muscle","proportions")
BATCH=36
def service(suffix,name):
    for module_name in tuple(sys.modules):
        if module_name.endswith(suffix):
            module=importlib.import_module(module_name)
            if hasattr(module,name):return getattr(module,name)
    raise RuntimeError("PINNED_MPFB_SERVICE_UNAVAILABLE_"+suffix+"_"+name)

def radical_inverse(n,b):
    result=0.0;scale=1.0/b
    while n:
        n,d=divmod(n,b);result+=scale*d;scale/=b
    return result

def cases(shard):
    anchors=[
       (0.50,0.50,0.50,0.50),
       (0.20,0.20,0.35,0.25),
       (0.80,0.72,0.80,0.75),
       (0.52,0.85,0.27,0.35),
    ]
    unique=list(anchors)
    for i in range(1,1+BATCH-len(anchors)):
        unique.append(tuple(round(0.15+0.70*radical_inverse(i,b),7)
                            for b in (2,3,5,7)))
    assert len(unique)==BATCH and len(set(unique))==BATCH
    return [{"id":i,"gender":float(shard),"macros":dict(zip(MACROS,v))}
            for i,v in enumerate(unique)]

def vertices(obj):
    deps=bpy.context.evaluated_depsgraph_get()
    ev=obj.evaluated_get(deps)
    mesh=ev.to_mesh()
    try:return np.asarray([tuple(float(v) for v in vertex.co) for vertex in mesh.vertices],dtype=np.float64)
    finally:ev.to_mesh_clear()

def fingerprint(points):
    h=hashlib.sha256()
    for p in points:
        h.update(",".join(f"{float(v):.7f}" for v in p).encode("ascii"));h.update(b";")
    return h.hexdigest()

def measure(points):
    lo=points.min(axis=0);hi=points.max(axis=0)
    dimensions=hi-lo
    zspan=float(dimensions[2])
    assert np.all(np.isfinite(points)) and zspan>0.5 and len(points)>1000
    features=[float(d) for d in dimensions]
    slice_receipts=[]
    for fraction in (0.35,0.48,0.58,0.69,0.80):
        z=float(lo[2]+fraction*zspan)
        band=points[np.abs(points[:,2]-z) <= max(0.009,zspan*0.008)]
        if len(band)>=4:
            width=float(np.max(band[:,0])-np.min(band[:,0]))
            depth=float(np.max(band[:,1])-np.min(band[:,1]))
        else:
            width=None;depth=None
        slice_receipts.append({"normalized_height_fraction":fraction,
                               "sampled_vertices":len(band),
                               "width_x_native_units":None if width is None else round(width,7),
                               "depth_y_native_units":None if depth is None else round(depth,7)})
        features.extend([0.0 if width is None else width,0.0 if depth is None else depth])
    return {"native_xspan":round(float(dimensions[0]),7),
            "native_yspan":round(float(dimensions[1]),7),
            "native_zspan":round(zspan,7),
            "horizontal_slices":slice_receipts,
            "measured_feature_vector":[round(v,7) for v in features],
            "evaluated_vertices":len(points),
            "evaluated_shape_sha256_rounded_7":fingerprint(points)}

def run_regression(samples):
    x=np.asarray([r["measurement"]["measured_feature_vector"] for r in samples])
    y=np.asarray([[r["macros"][k] for k in MACROS] for r in samples])
    assert np.all(np.isfinite(x)) and np.all(np.isfinite(y))
    # Fixed deterministic split: minimum eight independent test macro targets.
    train=[i for i in range(BATCH) if i%4!=0]
    test=[i for i in range(BATCH) if i%4==0]
    assert len(train)==27 and len(test)==9
    x_train=x[train];x_test=x[test]
    y_train=y[train];y_test=y[test]
    center=x_train.mean(axis=0)
    scale=x_train.std(axis=0)
    scale[scale<1e-8]=1.
    z_train=(x_train-center)/scale
    z_test=(x_test-center)/scale
    # Native finite-dimensional linear ridge inverse geometry->macro baseline,
    # NOT prompt->MPFB and NOT original published Semantify weights.
    alpha=0.35
    a=np.column_stack([np.ones(len(train)),z_train])
    b=np.column_stack([np.ones(len(test)),z_test])
    identity=np.eye(a.shape[1]);identity[0,0]=0.
    w=np.linalg.solve(a.T@a+alpha*identity,a.T@y_train)
    pred_ridge=np.clip(b@w,0,1)
    pred_mean=np.broadcast_to(y_train.mean(axis=0),y_test.shape)
    distance=np.sum(((z_test[:,None,:]-z_train[None,:,:]))**2,axis=-1)
    nearest=y_train[np.argmin(distance,axis=1)]
    methods={"constant_train_mean":pred_mean,"nearest_native_feature":nearest,"ridge_native_feature":pred_ridge}
    errors={k:float(np.mean(np.abs(v-y_test))) for k,v in methods.items()}
    per_dim={k:{name:round(float(np.mean(np.abs(v[:,j]-y_test[:,j]))),7)
                 for j,name in enumerate(MACROS)} for k,v in methods.items()}
    return {"status":"PASS_SOURCE_NATIVE_HELDOUT_INVERSE_BASELINES",
            "scope":"measured native 3D model geometry -> official normalized MPFB macro controls, NOT text input or actual human cm",
            "train_records":len(train),"test_records":len(test),
            "source_basis":"actual source-native Blender evaluated mesh, 13 geometric span/slice features",
            "features":x.shape[1],"target_macro_names":list(MACROS),
            "l1_native_control_error":{k:round(v,7) for k,v in errors.items()},
            "per_target_native_control_l1":per_dim,
            "ridge_alpha":alpha,"split":"case index mod4=0 held out",
            "model_promotion":"HOLD_INSAMPLE_SMALL_DATASET",
            "mesh_collision_or_geometry_validity":"NOT_QUALIFIED"}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--shard",choices=(0,1),type=int,required=True)
    ap.add_argument("--out",type=Path,required=True)
    aa=ap.parse_args(sys.argv[sys.argv.index("--")+1:])
    aa.out.mkdir(parents=True,exist_ok=True)
    addon="bl_ext.r014lab.mpfb"
    if addon not in bpy.context.preferences.addons:addon_utils.enable(addon,default_set=False)
    assert addon in bpy.context.preferences.addons,"NO_OFFICIAL_MPFB_ADDON"
    Human=service("mpfb.services.humanservice","HumanService")
    Props=service("mpfb.entities.objectproperties","HumanObjectProperties")
    Target=service("mpfb.services.targetservice","TargetService")
    scene=bpy.context.scene
    scene.frame_set(1)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    body=Human.create_human()
    assert len(body.data.vertices)>1000
    sampled=[]
    def set_controls(cfg):
        Props.set_value("gender",cfg["gender"],entity_reference=body)
        Props.set_value("age",0.65,entity_reference=body)
        for key in MACROS:Props.set_value(key,cfg["macros"][key],entity_reference=body)
        Target.reapply_macro_details(body)
        bpy.context.view_layer.update()
    design=cases(aa.shard)
    for cfg in design:
        set_controls(cfg)
        current=vertices(body)
        record={"case_id":f"source_mpbf_{aa.shard}_{cfg['id']:03d}",
                "gender_macro":cfg["gender"],"age_macro":0.65,
                "macros":cfg["macros"],"measurement":measure(current)}
        sampled.append(record)
    # Reset from extreme/low-discrepancy case to EXACT original 0.5 baseline;
    # catch macro accumulation/persistent-geometry leakage.
    set_controls(design[0])
    repeated=vertices(body)
    reference=sampled[0]["measurement"]
    max_repeated_delta=0.0
    assert len(repeated)==reference["evaluated_vertices"]
    max_repeated_delta=float(max(abs(x-y) for x,y in zip(
        reference["measured_feature_vector"],measure(repeated)["measured_feature_vector"])))
    assert max_repeated_delta<1e-6,("MACRO_REPLAY_GEOMETRY_DRIFT",max_repeated_delta)
    distinct=len({r["measurement"]["evaluated_shape_sha256_rounded_7"] for r in sampled})
    assert distinct==BATCH,("NON_DISTINCT_NATIVE_MORPH_SAMPLES",distinct)
    variation={
       key:{"min":round(min(r["measurement"][key] for r in sampled),7),
            "max":round(max(r["measurement"][key] for r in sampled),7)}
       for key in ("native_xspan","native_yspan","native_zspan")
    }
    training=run_regression(sampled)
    out={
       "schema":"r014.mpfb.native_inverse_doe.v1","status":"PASS_REAL_NATIVE_GEOMETRY_DOE_AND_INVERSE_CPU_BASELINES",
       "shard":aa.shard,"source_mpfb_pin":SOURCE,"source_mpbf_macro_gender":aa.shard,
       "age_macro":0.65,"age_inference":"not actual human age; morph macro only",
       "actual_samples":len(sampled),"distinct_actual_evaluated_shapes":distinct,
       "raw_vs_evaluated":"measured Blender dependency-graph evaluated positions, not base mesh bounds",
       "dimensions_native":variation,"fixed_baseline_replay_max_measurement_difference":max_repeated_delta,
       "regressor":training,
       "content_policy":"synthetic adult body controls only; CPE semantics not remapped, private source imagery absent",
       "rights":"upstream source-pinned research MPFB; no third party binary models committed",
       "not_qualified":["real cm measurement","facial realism","skin hair eye fit",
                        "external reproductive anatomy","full rig compatibility at every DoE point",
                        "natural-language mapper","CPE policy promotion","4k photoreal video"],
       "merge_release":"HOLD"}
    (aa.out/f"native_inverse_doe_shard_{aa.shard}.json").write_text(
        json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf8")
    with (aa.out/f"native_inverse_doe_samples_{aa.shard}.jsonl").open("w",encoding="utf8") as f:
        for row in sampled:f.write(json.dumps(row,sort_keys=True,separators=(",",":"))+"\n")
    print("R014_NATIVE_DOE_SUMMARY",json.dumps(out,sort_keys=True))
    # JSONL is small, synthetic and has no images; emit aggregate only in log.
if __name__=="__main__":main()
