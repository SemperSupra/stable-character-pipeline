"""Minimal bounded Lipschitz majorant for reach-preserving world-space pelvis motion.

Given nonnegative per-frame minimum required lowering r[t], find the pointwise
minimum x[t] >= r[t] with |x[t]-x[t-1]| <= slope. Unlike a symmetric
fixed-width max filter, it cannot introduce >slope one-frame steps.
Research-only: no physical dynamics, acceleration or floor collision proof.
"""
import math

def envelope(raw, slope, cap):
    if not raw or not all(math.isfinite(v) and v >= 0. for v in raw):
        raise ValueError("invalid nonnegative finite source reach requirements")
    if not math.isfinite(slope) or not 0 < slope <= cap or not math.isfinite(cap):
        raise ValueError("invalid envelope limits")
    n=len(raw)
    if max(raw)>cap+1e-12:
        raise ValueError("source target out of bounded pelvis reach")
    out=list(map(float,raw))
    for i in range(n-2,-1,-1):
        out[i]=max(out[i],out[i+1]-slope)
    for i in range(1,n):
        out[i]=max(out[i],out[i-1]-slope)
    if any(v>cap+1e-10 for v in out):
        raise ValueError("envelope violates pelvis cap")
    if any(out[i]+1e-10<raw[i] for i in range(n)):
        raise AssertionError("source reach lost")
    if any(abs(out[i]-out[i-1])>slope+1e-10 for i in range(1,n)):
        raise AssertionError("source slope bound lost")
    return out

if __name__=="__main__":
    assert all(abs(a-b)<1e-12 for a,b in zip(envelope([0.,.12,0.],.01,.2),[.11,.12,.11]))
    assert envelope([.02]*8,.01,.2)==[.02]*8
    assert all(abs(a-b)<1e-12 for a,b in zip(envelope([0.,.02,.04,.06],.01,.2),[.03,.04,.05,.06]))
    for bad in ([float("nan")],[-1.],[]):
        try: envelope(bad,.01,.2)
        except ValueError: pass
        else: raise AssertionError("forged input accepted")
    for bad in ([0.,.21],[0.,float("inf")]):
        try: envelope(bad,.01,.2)
        except ValueError: pass
        else: raise AssertionError("forged input accepted")
    for s in (0.,-.1,.21):
        try: envelope([0.,.01],s,.2)
        except ValueError: pass
        else: raise AssertionError("forged slope accepted")
    print("R014_LIPSCHITZ_PELVIS_SOURCE_GATES_PASS")
