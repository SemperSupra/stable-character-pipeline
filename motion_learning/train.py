"""JAX TPU eight-device motion next-pose learner, self-contained synthetic R&D only.

Not an accepted human/animal realism result. No credentials, network, or third-party datasets.
"""
from __future__ import annotations
import argparse
from functools import partial
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np
from synthetic import build, JOINTS

SCHEMA='scp.motion-learning-result.v1'

def create_windows(arr,window=4):
    # Split sequences, not overlapping frames, to prevent train/test leakage.
    x=np.stack([arr[:,i:i+window] for i in range(arr.shape[1]-window)],axis=1)
    y=arr[:,window:]
    return x.reshape((-1,window,arr.shape[2]*3)),y.reshape((-1,arr.shape[2]*3))

def train(domain: str,backend: str='tpu',steps: int=120,batch_per_device: int=32,seed:int=20261027):
    import jax
    import jax.numpy as jnp
    from jax import random
    begin=time.monotonic()
    devices=[d for d in jax.devices() if d.platform==backend]
    if backend=='tpu' and len(devices)!=8: raise RuntimeError('TPU_EIGHT_DEVICE_ATTESTATION_FAILED')
    if not devices: raise RuntimeError('REQUESTED_BACKEND_ABSENT')
    arr,manifest=build(domain,nseq=128,frames=48,seed=seed)
    # Exact sequence holdout: 96 train, 32 validation; no shared sequence windows.
    train_arr,valid_arr=arr[:96],arr[96:]
    mean=train_arr.mean(axis=(0,1)).reshape(-1)
    std=np.maximum(train_arr.std(axis=(0,1)).reshape(-1),.05)
    X,Y=create_windows(train_arr); VX,VY=create_windows(valid_arr)
    x=((X-mean)/std).astype('float32')
    target=((Y-X[:,-1,:])/std).astype('float32')
    vx=((VX-mean)/std).astype('float32')
    vtarget=((VY-VX[:,-1,:])/std).astype('float32')
    nin=x.shape[1]*x.shape[2]; nout=target.shape[1]
    hidden=128
    k1,k2=random.split(random.PRNGKey(seed))
    init={"w1":random.normal(k1,(nin,hidden))*jnp.float32(.06),
          "b1":jnp.zeros((hidden,),jnp.float32),
          "w2":jnp.zeros((hidden,nout),jnp.float32),
          "b2":jnp.zeros((nout,),jnp.float32)}
    def forward(params,flat):
        return jnp.tanh(flat@params['w1']+params['b1'])@params['w2']+params['b2']
    def loss(params,x,y):
        out=forward(params,x.reshape((x.shape[0],-1)))
        return jnp.mean(jnp.square(out-y))
    @partial(jax.pmap,axis_name='replicas',devices=devices)
    def step(params,x,y):
        val,grads=jax.value_and_grad(loss)(params,x,y)
        grads=jax.lax.pmean(grads,'replicas')
        val=jax.lax.pmean(val,'replicas')
        return jax.tree_util.tree_map(lambda a,g:a-jnp.float32(.032)*g,params,grads),val
    params=jax.device_put_replicated(init,devices)
    rng=np.random.default_rng(seed+29)
    global_batch=len(devices)*batch_per_device
    lastloss=None
    for _ in range(steps):
        indices=rng.integers(0,len(x),size=global_batch)
        bx=x[indices].reshape((len(devices),batch_per_device,x.shape[1],x.shape[2]))
        by=target[indices].reshape((len(devices),batch_per_device,nout))
        params,vl=step(params,jnp.asarray(bx),jnp.asarray(by))
        lastloss=vl
    # Block to measure actual completed computation, not async submit only.
    lastloss.block_until_ready()
    par=jax.tree_util.tree_map(lambda a:np.asarray(a[0]),params)
    def predict(a):
        return np.tanh(a.reshape((a.shape[0],-1))@par['w1']+par['b1'])@par['w2']+par['b2']
    predicted=predict(vx)
    residual_mse=float(np.mean(np.square(predicted-vtarget)))
    baseline_mse=float(np.mean(np.square(vtarget)))
    shuffled_target=vtarget[np.random.default_rng(seed+83).permutation(len(vtarget))]
    shuffled_mse=float(np.mean(np.square(predicted-shuffled_target)))
    if not all(np.isfinite(i) for i in (residual_mse,baseline_mse,shuffled_mse)):raise ArithmeticError('NONFINITE_LOSS')
    if residual_mse>=baseline_mse:raise AssertionError('LEARNED_MODEL_NOT_BEATING_PERSISTENCE_BASELINE')
    if residual_mse>=shuffled_mse:raise AssertionError('SHUFFLED_CONTROL_NOT_WORSE')
    # Actual conditional autoregressive generation, held out from fitting.
    history=VX[0].astype(np.float32).copy()
    generated=[]
    for _ in range(24):
        normalized=((history-mean)/std).astype('float32')[None,:,:]
        delta=predict(normalized)[0]*std
        nxt=(history[-1]+delta).astype(np.float32)
        generated.append(nxt.copy())
        history=np.concatenate([history[1:],nxt[None,:]],axis=0)
    generated=np.stack(generated).reshape((24,len(JOINTS[domain]),3))
    reference=valid_arr[0,4:28]
    rollout_mse=float(np.mean(np.square(generated-reference)))
    if not np.isfinite(rollout_mse):raise ArithmeticError('NONFINITE_ROLLOUT')
    metric={"schema":SCHEMA,"status":"PASS","domain":domain,"backend":backend,
            "device_count":len(devices),"device_models":sorted({str(d.device_kind) for d in devices}),
            "jax_version":jax.__version__,"seed":seed,"steps":steps,"batch_per_device":batch_per_device,
            "source_dataset_digest":manifest['data_float32_sha256'],"source_dataset_synthetic":True,
            "train_sequences":96,"validation_sequences":32,"training_window_count":len(x),
            "validation_window_count":len(vx),"joint_count":len(JOINTS[domain]),
            "train_last_loss":float(np.asarray(lastloss)[0]),"heldout_rollout_24_mse":rollout_mse,
            "heldout_residual_mse":residual_mse,"persistence_baseline_mse":baseline_mse,
            "shuffled_control_mse":shuffled_mse,"elapsed_seconds":round(time.monotonic()-begin,3),
            "scope":"synthetic-one-step-motion-prediction-only","physically_valid_motion":"NOT_CLAIMED",
            "real_motion_generation":"NOT_QUALIFIED"}
    return metric,par,mean,std,manifest,generated

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--domain',choices=tuple(JOINTS),required=True)
    p.add_argument('--backend',choices=('cpu','gpu','tpu'),default='tpu')
    p.add_argument('--steps',type=int,default=120)
    p.add_argument('--output',default='/kaggle/working')
    a=p.parse_args()
    if a.steps<1 or a.steps>400: raise SystemExit('INVALID_STEPS')
    out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    try:
        metric,par,mean,std,source,generated=train(a.domain,a.backend,a.steps)
        # Persist model params and stat transforms for reproducible inference.
        path=out/f'{a.domain}-motion-weights.npz'
        if path.exists(): raise FileExistsError(path)
        np.savez(path,**par,mean=mean,std=std)
        metric['checkpoint_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        motion_path=out/f'{a.domain}-generated-motion.npy'
        if motion_path.exists():raise FileExistsError(motion_path)
        np.save(motion_path,generated,allow_pickle=False)
        metric['generated_motion_sha256']=hashlib.sha256(generated.tobytes()).hexdigest()
        metric['generated_frames']=len(generated)
        (out/f'{a.domain}-motion-result.json').write_text(json.dumps(metric,sort_keys=True,indent=2)+'\n')
        print(json.dumps(metric,sort_keys=True))
        return 0
    except Exception as exc:
        failure={"schema":SCHEMA,"status":"FAIL","domain":a.domain,"backend":a.backend,
                 "failure_class":type(exc).__name__,"training_qualified":False}
        (out/f'{a.domain}-motion-result.json').write_text(json.dumps(failure,sort_keys=True,indent=2)+'\n')
        print(json.dumps(failure,sort_keys=True),file=sys.stderr)
        return 2

if __name__=='__main__':sys.exit(main())
