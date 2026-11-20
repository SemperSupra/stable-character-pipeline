#!/usr/bin/env python3
"""N03D source-safe numerical contact DoE, no real identities or upstream restricted code.
Synthetic 2D shoe-foot rigid transform: evaluates actual sole support vertices, not an ankle proxy.
This is a screening/critic oracle only; NOT native MPFB gait qualification.
"""
import argparse, hashlib, itertools, json, math, statistics, unittest
from dataclasses import dataclass

@dataclass(frozen=True)
class Shoe:
    heel: float
    toe: float
    thickness: float
    arch: float
    def local(self):
        return [(-self.heel, -self.thickness), (0.0, -self.arch), (self.toe, -self.thickness)]

SHOES = {
    "rigid": Shoe(0.11, 0.16, 0.042, 0.020),
    "articulated_proxy": Shoe(0.11, 0.16, 0.042, 0.027),
    "compliant_proxy": Shoe(0.11, 0.16, 0.039, 0.022),
}
# Stance foot ought to remain at the same world-space support site.
# Independent motion cases are blocks; frames are correlated, not independent replicates.
CASES = {
    "stance_early": [(-0.06 + 0.015*t, 0.042 - 0.006*t, 0.20 - 0.025*t) for t in range(7)],
    "stance_late": [(0.025 + 0.014*t, 0.042 - 0.004*t, -0.05 - 0.02*t) for t in range(7)],
    "stance_noisy": [(0.015*math.sin(t), 0.040 + 0.005*math.cos(t), 0.1*math.sin(t/2)) for t in range(7)],
}
def geometry(shoe, pose):
    x,z,a=pose; ca,sa=math.cos(a),math.sin(a)
    return [(x+ca*lx-sa*lz,z+sa*lx+ca*lz) for lx,lz in shoe.local()]

def evaluate(shoe, poses):
    frames=[geometry(shoe,p) for p in poses]
    # Per-frame worst negative geometry, and stance displacement on the SAME sole vertex.
    penetration=max((max(0.0,-z) for f in frames for _,z in f),default=0)
    slip=max((math.hypot(f[i][0]-frames[0][i][0],f[i][1]-frames[0][i][1]) for f in frames for i in (0,2)),default=0)
    clearance=max((max(0.0,min(z for _,z in f)) for f in frames),default=0)
    tracking=statistics.mean(math.dist(a,b) for a,b in zip(poses,ORIGINAL)) if False else 0
    return dict(max_penetration_m=penetration,max_stance_anchor_displacement_m=slip,max_floating_m=clearance)

def adapt(shoe, poses, solver):
    if solver=="legacy": return poses
    # Guard the two support anchors in world coordinates rather than a tail/ankle joint.
    initial=geometry(shoe,poses[0])
    support=min((0,2),key=lambda k: abs(initial[k][1]))
    target=(initial[support][0],0.0)
    out=[]
    for x,z,a in poses:
        angle=a if solver=="geometry_translation" else 0.0
        sx,sz=geometry(shoe,(0,0,angle))[support]
        out.append((target[0]-sx, -sz,angle))
    return out

def run():
    records=[]
    for shape, case, solver in itertools.product(SHOES,CASES,("legacy","geometry_translation","geometry_rotation")):
        shoe=SHOES[shape]; source=CASES[case]; fixed=adapt(shoe,source,solver)
        metrics=evaluate(shoe,fixed)
        # Preserve source trajectory error; do not hide motion corruption behind contact improvement.
        metrics["mean_pose_deviation_m_equiv"]=statistics.mean(math.sqrt((x-a)**2+(z-b)**2+(0.1*(q-r))**2) for (x,z,q),(a,b,r) in zip(fixed,source))
        records.append(dict(geometry=shape,case=case,solver=solver,metrics=metrics))
    return records

class TestCritics(unittest.TestCase):
    def test_detects_penetration(self):
        self.assertGreater(evaluate(SHOES["rigid"],[(0,0,0)])["max_penetration_m"],0.03)
    def test_detects_sliding(self):
        shoe=SHOES["rigid"]
        self.assertGreater(evaluate(shoe,[(0,0.042,0),(0.05,0.042,0)])["max_stance_anchor_displacement_m"],0.04)
    def test_detects_floating(self):
        self.assertGreater(evaluate(SHOES["rigid"],[(0,0.2,0)])["max_floating_m"],0.1)
    def test_corrected_support_touches_floor(self):
        shoe=SHOES["rigid"]; corrected=adapt(shoe,CASES["stance_early"],"geometry_rotation")
        self.assertAlmostEqual(min(z for _,z in geometry(shoe,corrected[2])),0.0,places=9)
    def test_not_confuse_ankle_with_shoe(self):
        # Zero ankle height penetrates even with a perfectly stationary ankle.
        self.assertGreater(evaluate(SHOES["rigid"],[(0,0,0)]*4)["max_penetration_m"],0)
    def test_treatments_deterministic(self):
        self.assertEqual(run(),run())
    def test_no_artificial_zero_slip_for_legacy(self):
        values=run()
        self.assertTrue(any(r["metrics"]["max_stance_anchor_displacement_m"]>0.02 for r in values if r["solver"]=="legacy"))
    def test_full_factorial(self):
        self.assertEqual(len(run()),27)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",default="n03d-doe-receipt.json");p.add_argument("--test",action="store_true");args=p.parse_args()
    if args.test:
        unittest.main(argv=["n03d"],exit=False)
    else:
        records=run()
        payload={"schema":"scp.n03d.synthetic_screen.v1","qualification":"RESEARCH_ONLY_NOT_NATIVE_GAIT","design":{"geometry":list(SHOES),"case_blocks":list(CASES),"solver":["legacy","geometry_translation","geometry_rotation"]},"observations":records}
        raw=json.dumps(payload,sort_keys=True,indent=2).encode()
        with open(args.output,"wb") as f:f.write(raw+b"\n")
        print(json.dumps({"sha256":hashlib.sha256(raw+b"\n").hexdigest(),"treatments":len(records),"output":args.output,"status":"SYNTHETIC_ONLY"},sort_keys=True))
