"""Original deterministic synthetic human and quadruped joint trajectories.

Geometry is procedural and stylized: never measured humans/animals, never an
identity-, anatomy-, or biological-realism benchmark.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np

SCHEMA = "scp.synthetic-motion.v1"
JOINTS = {
    "human": ["pelvis", "spine", "neck", "head", "l_shoulder", "l_elbow", "l_wrist", "r_shoulder", "r_elbow", "r_wrist", "l_hip", "l_knee", "l_ankle", "l_toe", "r_hip", "r_knee", "r_ankle", "r_toe"],
    "fauna": ["pelvis", "chest", "neck", "head", "tail", "fl_shoulder", "fl_knee", "fl_paw", "fr_shoulder", "fr_knee", "fr_paw", "bl_hip", "bl_knee", "bl_paw", "br_hip", "br_knee", "br_paw"]
}
GAITS = {"human": ("walk", "jog", "wave", "turn"), "fauna": ("walk", "trot", "gallop", "turn")}
FOOT_JOINTS = {"human": [12,16], "fauna": [7,10,13,16]}

def _rotate(points: np.ndarray, yaw: float) -> np.ndarray:
    c, s = np.cos(yaw), np.sin(yaw)
    return points @ np.array([[c,-s,0.0],[s,c,0.0],[0.0,0.0,1.0]],dtype=np.float32).T

def _human(phase: float, gait: str, speed: float, scale: float) -> np.ndarray:
    b = np.zeros((18,3), dtype=np.float32)
    b[:4] = [[0,0,0.98],[0,0,1.28],[0,0,1.54],[0.05,0,1.75]]
    freq = 1.65 if gait == 'jog' else 1.0
    for side,sh,el,wr,hip,knee,ank,toe in [(-1,4,5,6,10,11,12,13),(1,7,8,9,14,15,16,17)]:
        swing = np.sin(freq*phase + (0 if side<0 else np.pi))
        b[sh]=[0,side*.21,1.47]
        b[el]=[-.04-.12*swing,side*.28,1.17]
        b[wr]=[-.10-.20*swing,side*.29,.93]
        b[hip]=[0,side*.13,.93]
        b[knee]=[.18*swing,side*.13,.53 + .05*max(swing,0)]
        b[ank]=[.32*swing,side*.13,.09+.09*max(swing,0)]
        b[toe]=[.12+.32*swing,side*.13,.045+.09*max(swing,0)]
    if gait=='wave':
        b[7:10] = [[0,.21,1.47],[.08,.28,1.66],[.16+.08*np.sin(2*phase),.28,1.85]]
    b[0:4,2]+= .017*np.sin(2*phase)
    return b * scale

def _fauna(phase: float, gait: str, speed: float, scale: float) -> np.ndarray:
    b=np.zeros((17,3),dtype=np.float32)
    b[:5]=[[-.40,0,.71],[.45,0,.77],[.66,0,.95],[.90,0,.91],[-.80,0,.84+.11*np.sin(phase)]]
    for ix,(front,side) in enumerate([(True,-1),(True,1),(False,-1),(False,1)]):
        start=5+3*ix
        offset = (0 if front else np.pi) if gait == 'trot' else (ix*np.pi/2 if gait == 'walk' else (0 if front else 1.2))
        swing=np.sin(phase + offset)
        x=.45 if front else -.40
        b[start]=[x, side*.23,.68]
        b[start+1]=[x+.12*swing,side*.24,.36+.06*max(swing,0)]
        b[start+2]=[x+.24*swing,side*.24,.06+.12*max(swing,0)]
    b[:2,2]+=.02*np.cos(2*phase)
    return b * scale

def build(domain: str, nseq: int=96, frames: int=48, seed: int=20261027):
    if domain not in JOINTS or nseq<16 or frames<12: raise ValueError('INVALID_SYNTHETIC_SPEC')
    rng=np.random.default_rng(seed)
    data=np.empty((nseq,frames,len(JOINTS[domain]),3),dtype=np.float32)
    metadata=[]
    for i in range(nseq):
        gait=GAITS[domain][i % len(GAITS[domain])]
        speed=float(rng.uniform(.38,1.10))
        scale=float(rng.uniform(.91,1.09))
        phase0=float(rng.uniform(-np.pi,np.pi))
        yaw0=float(rng.uniform(-.15,.15))
        # Shape and speed are independent per sequence: no split-related sharing.
        for k in range(frames):
            t=k/24.0; phase=phase0+2*np.pi*(.55+.65*speed)*t
            yaw=yaw0 + ((.30*t) if gait=='turn' else 0.0)
            local=_human(phase,gait,speed,scale) if domain=='human' else _fauna(phase,gait,speed,scale)
            posed=_rotate(local,yaw)
            posed[:,0]+=speed*t
            posed[:,1]+=.09*np.sin(.41*t+i*.23)
            data[i,k]=posed
        metadata.append({"sequence":i,"gait":gait,"source":"original-procedural-synthetic","observed":False,"fps":24})
    # Stable SOURCE digest independent of .npz zip timestamps.
    digest=hashlib.sha256(data.tobytes(order='C')).hexdigest()
    return data, {"schema":SCHEMA,"domain":domain,"seed":seed,"nseq":nseq,"frames":frames,"fps":24,"joints":JOINTS[domain],"foot_joint_indices":FOOT_JOINTS[domain],"gait_classes":list(GAITS[domain]),"observed":False,"real_world_fidelity":"UNQUALIFIED","rights":"original-synthetic-created-for-this-research","data_float32_sha256":digest,"sequence_metadata":metadata}

def write_dataset(domain: str, output: str, nseq: int=96, frames: int=48, seed: int=20261027):
    dest=Path(output)
    if dest.exists(): raise FileExistsError(dest)
    dest.mkdir(parents=True)
    arr,manifest=build(domain,nseq,frames,seed)
    np.save(dest/'motion.npy', arr, allow_pickle=False)
    (dest/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    return manifest

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('domain',choices=tuple(JOINTS))
    p.add_argument('--output',required=True)
    p.add_argument('--nseq',type=int,default=96)
    p.add_argument('--frames',type=int,default=48)
    a=p.parse_args(); print(json.dumps({k:v for k,v in write_dataset(a.domain,a.output,a.nseq,a.frames).items() if k!='sequence_metadata'},sort_keys=True))
