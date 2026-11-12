"""Pinned MHR TorchScript functional inference smoke test, CPU only.
This outputs receipts, never upstream weight bytes or protected identities.
"""
import argparse,hashlib,json,time,zipfile
from pathlib import Path
import torch
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--sha256',required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    h=hashlib.sha256(a.archive.read_bytes()).hexdigest()
    assert h==a.sha256,'pinned archive hash mismatches GitHub Release digest'
    with zipfile.ZipFile(a.archive) as z:
        assert 'assets/LICENSE.txt' in z.namelist()
        assert b'Apache License' in z.read('assets/LICENSE.txt')
        # No ZIP bulk extraction, no ZIP slip.
        member='assets/mhr_model.pt'
        with z.open(member) as inp, (a.out/'mhr_model.pt').open('wb') as out:
            import shutil
            shutil.copyfileobj(inp,out)
    torch.manual_seed(0)
    torch.set_num_threads(2)
    started=time.monotonic()
    model=torch.jit.load(str(a.out/'mhr_model.pt'),map_location='cpu')
    model.eval()
    identity=torch.zeros(2,45)
    pose=torch.zeros(2,204)
    face=torch.zeros(2,72)
    identity[1,0]=0.75
    identity[1,20]=0.45
    face[1,0]=0.3
    with torch.no_grad():
        v0,s0=model(identity,pose,face)
        v1,s1=model(identity,pose,face)
        neutral,_=model(torch.zeros(1,45),torch.zeros(1,204),torch.zeros(1,72))
    assert v0.ndim==3 and v0.shape[0]==2 and v0.shape[2]==3,tuple(v0.shape)
    assert torch.isfinite(v0).all()
    assert torch.isfinite(v1).all()
    repeat=(v0-v1).abs().max().item()
    delta=(v0[0]-v0[1]).abs().max().item()
    assert repeat<=1e-6,('nondeterministic outputs',repeat)
    assert delta>1e-5,('latent controls do not perturb mesh',delta)
    out={
      'status':'PASS_CPU_TORCHSCRIPT_PARAMETER_RESPONSE_STRUCTURAL_ONLY',
      'archive_sha256':h,'assets_code_license':'embedded Apache-2.0 LICENSE text inspected',
      'mhr_model_members':1,'vertex_count':int(v0.shape[1]),
      'max_repeat_vertex_abs':repeat,'max_variant_vertex_abs':delta,
      'elapsed_s':round(time.monotonic()-started,2),
      'torch_version':torch.__version__,
      'parametric_dimensions':{'identity':45,'pose':204,'face':72},
      'limits':['Not a male/female semantic classifier','No topology/faces/rig export',
                'No photorealistic closeup or deform quality qualification',
                'No real full-body camera render, soft-tissue physics or output model weights',
                'Needs independent visual assessment and license obligations review']
    }
    (a.out/'inference_receipt.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print('R014_MHR_INFERENCE',json.dumps(out,sort_keys=True))
    (a.out/'mhr_model.pt').unlink()
if __name__=='__main__':main()
