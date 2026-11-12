"""R014: actual MHR model identity-latent sensitivity DOE, research not human qualification.

Only deidentified official synthetic MHR model inputs (zero pose/face).
Output numerical evidence, never original model weights or private media.
MHR shape axes are opaque: no cm/sex/age/body-shape label calibration here.
"""
import argparse, hashlib, io, json, math, os, sys, zipfile
from pathlib import Path
import torch
import numpy as np

ARCHIVE_DIGEST = "e4f4f205cd87c0fa106577ba1de4fc763e4eb197c924461d2ef7e6944e9d6b94"
LATENTS = 45
POSE = 204
FACE = 72
EPS = .35
VERTEX_SAMPLE_STRIDE = 31

def spans(vertices):
    """Geometric axis-aligned extents in raw MHR units; not anthropometry."""
    a = np.asarray(vertices, np.float64)
    if a.ndim != 2 or a.shape[1] != 3 or not np.isfinite(a).all():
        raise ValueError("invalid 3d mesh points")
    return np.ptp(a, axis=0).tolist()

def perturbation_stats(neutral, plus, minus, epsilon=EPS):
    a,b,c = [np.asarray(v, dtype=np.float64) for v in (neutral, plus, minus)]
    if a.shape != b.shape or a.shape != c.shape or a.ndim != 2 or a.shape[1] != 3:
        raise ValueError("vertex topology mismatch in sensitivity experiment")
    if not np.isfinite(a).all() or not np.isfinite(b).all() or not np.isfinite(c).all():
        raise ValueError("nonfinite vertices")
    if not (0 < epsilon < 1):
        raise ValueError("invalid perturbation")
    dplus=b-a
    dminus=c-a
    deriv=(b-c)/(2*epsilon)
    asym=np.linalg.norm(dplus+dminus,axis=1)
    combined=np.linalg.norm(dplus,axis=1)+np.linalg.norm(dminus,axis=1)
    return {
        "rms_central_derivative_raw_units_per_control":float(np.sqrt(np.mean(deriv**2))),
        "max_positive_perturbation_raw_units":float(np.max(np.abs(dplus))),
        "max_negative_perturbation_raw_units":float(np.max(np.abs(dminus))),
        "relative_oddness_residual":float(np.sum(asym)/max(np.sum(combined),1e-12)),
        "positive_aabb_spans_raw_units":spans(b),
        "negative_aabb_spans_raw_units":spans(c),
    }, deriv

def run_model(model, rows):
    x = torch.tensor(rows,dtype=torch.float32)
    zero_pose=torch.zeros((len(rows),POSE),dtype=torch.float32)
    zero_face=torch.zeros((len(rows),FACE),dtype=torch.float32)
    with torch.no_grad():
        mesh,_=model(x,zero_pose,zero_face)
    if tuple(mesh.shape)[0]!=len(rows) or mesh.ndim!=3 or mesh.shape[-1]!=3:
        raise ValueError("MHR TorchScript output shape changed")
    if not torch.isfinite(mesh).all():
        raise ValueError("MHR returned nonfinite mesh")
    return mesh.detach().cpu().numpy()

def selftest():
    import unittest
    class Checks(unittest.TestCase):
        def test_symmetric_linear(self):
            base=np.array([[0,0,0],[1,2,3]],float)
            plus=base+0.35
            minus=base-0.35
            r,d=perturbation_stats(base,plus,minus)
            self.assertAlmostEqual(r["relative_oddness_residual"],0)
            self.assertTrue(np.allclose(d,1))
        def test_shape_mismatch_fails(self):
            with self.assertRaises(ValueError):
                perturbation_stats(np.zeros((2,3)),np.zeros((3,3)),np.zeros((2,3)))
        def test_nonfinite_fails(self):
            a=np.zeros((2,3));a[0,0]=float("nan")
            with self.assertRaises(ValueError):
                perturbation_stats(a,np.zeros((2,3)),np.zeros((2,3)))
        def test_nonlinearity_witness(self):
            a=np.zeros((2,3));p=a+(.35+.35**2);m=a+(-.35+.35**2)
            r,d=perturbation_stats(a,p,m)
            self.assertGreater(r["relative_oddness_residual"],0)
            self.assertTrue(np.isfinite(d).all())
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Checks)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(2)

def main():
    if "--self-test" in sys.argv:
        selftest()
        return
    p=argparse.ArgumentParser()
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--shard",type=int,choices=(0,1),required=True)
    args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    h=hashlib.sha256(args.archive.read_bytes()).hexdigest()
    if h!=ARCHIVE_DIGEST:
        raise ValueError("official pinned MHR release SHA mismatch")
    with zipfile.ZipFile(args.archive) as z:
        if z.testzip() is not None:
            raise ValueError("corrupt archive")
        names=set(z.namelist())
        if not {"assets/LICENSE.txt","assets/mhr_model.pt"} <= names:
            raise ValueError("missing pinned MHR license/model member")
        if b"Apache License" not in z.read("assets/LICENSE.txt"):
            raise ValueError("missing MHR asset license")
        model_bytes=z.read("assets/mhr_model.pt")
    # Avoid persistent extracted weights: load from in-memory stream.
    torch.set_num_threads(2)
    torch.manual_seed(0)
    model=torch.jit.load(io.BytesIO(model_bytes),map_location="cpu")
    model.eval()
    model_digest=hashlib.sha256(model_bytes).hexdigest()
    del model_bytes
    zero=[0.0]*LATENTS
    neutral=run_model(model,[zero])[0]
    neutral_repeat=run_model(model,[zero])[0]
    if not np.array_equal(neutral,neutral_repeat):
        raise ValueError("non-deterministic neutral inference")
    if not (1000 < len(neutral) < 300000):
        raise ValueError("unexpected model topology")
    axes=list(range(args.shard, LATENTS, 2))
    observations=[]
    samples=[]
    for start in range(0,len(axes),4):
        group=axes[start:start+4]
        rows=[]
        for axis in group:
            positive=zero.copy();positive[axis]=EPS
            negative=zero.copy();negative[axis]=-EPS
            rows.extend((positive,negative))
        meshes=run_model(model,rows)
        for j,axis in enumerate(group):
            metrics,deriv=perturbation_stats(neutral,meshes[2*j],meshes[2*j+1])
            observations.append({"latent_index":axis,**metrics})
            samples.append(deriv[::VERTEX_SAMPLE_STRIDE].reshape(-1))
    # These are only sampled vertex-space linear-response overlaps.
    J=np.asarray(samples,dtype=np.float64)
    norms=np.linalg.norm(J,axis=1)
    unit=J/np.maximum(norms[:,None],1e-15)
    gram=unit@unit.T
    sv=np.linalg.svd(J,compute_uv=False)
    rank=int(np.sum(sv>max(sv[0]*1e-6,1e-12))) if len(sv) else 0
    max_offdiag=float(np.max(np.abs(gram-np.eye(len(axes))))) if len(axes)>1 else 0
    status=("PASS_MHR_OPAQUE_SHAPE_RESPONSE_RESEARCH_ONLY"
            if np.isfinite(J).all() and neutral.shape==(len(neutral),3)
            else "HOLD_INVALID_RESPONSE")
    receipt={
        "schema":"r014.mhr.opaque_morph_sensitivity.v1",
        "status":status,
        "archive_sha256":h,
        "model_pt_sha256":model_digest,
        "source_model":"facebookresearch/MHR v1.0.1, pinned official public asset",
        "shard":args.shard,
        "control_indices":axes,
        "epsilon":EPS,
        "shape_control_count":LATENTS,
        "pose_control_count":POSE,
        "face_control_count":FACE,
        "mesh_vertices":len(neutral),
        "geometry_units":"OPAQUE_MHR_NATIVE_UNCALIBRATED",
        "neutral_aabb_spans_raw_units":spans(neutral),
        "sampled_vertex_stride":VERTEX_SAMPLE_STRIDE,
        "sampled_jacobian_rank":rank,
        "sampled_max_absolute_axis_correlation":max_offdiag,
        "per_latent":observations,
        "positive_admission":"NUMERICAL_RESPONSE_ONLY",
        "required_next":"Independent anatomical landmarks, anthropometry units, pose interactions, saved/reopened Blender mesh parity and visual QA",
        "limitations":[
            "No slider meaning, centimeters, gender/age/anatomical semantics inferred",
            "No proof that TorchScript neural corrections export to Blender/glTF",
            "No face/hands/reproductive organ completeness, calibrated soft tissue or collisions",
            "No 1080p/4K images or motion, no photoreal acceptance",
            "Single finite-difference step; J rank/correlation is sampled and local",
            "Research original synthetic bodies only; no protected likeness or user photos"]
    }
    path=args.out/("mhr_morph_sensitivity_shard_"+str(args.shard)+".json")
    path.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print("R014_MHR_NATIVE_SENSITIVITY",json.dumps({
        "status":status,"shard":args.shard,"controls":len(axes),
        "vertices":len(neutral),"rank":rank,"max_abs_corr":max_offdiag
    },sort_keys=True))

if __name__=="__main__":
    main()
