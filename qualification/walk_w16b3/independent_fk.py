"""Independent original numeric witness against source v3 two-leg typed frames."""
import json,math,sys
p=json.load(open(sys.argv[1]));r=json.load(open(sys.argv[2]))
assert p["Schema"]=="scp.walk_dual_leg_motion.v3"
assert p["Rights"]=="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
assert p["OriginSHA"]=="e0a42b8d5dfe23334486ff195ac90fe6b7d3a199"
assert p["Basis"]=="BLENDER_RH_Z_UP_SOURCE"
assert p["QuatOrder"]=="GLTF_XYZW_COMPONENTS_Z_UP_FRAME"
assert p["ClockOrigin"]=="SYNTHETIC_ZERO_NO_MEASURED_CLOCK"
assert r["Observations"]==28 and r["SourceOnly"] and r["MaxIKError"]<=1e-8
assert len(p["Actors"])==2
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def rotate(q,v):
 t=[2*x for x in cross(q[:3],v)]
 u=cross(q[:3],t)
 return [v[i]+q[3]*t[i]+u[i] for i in range(3)]
m=0.
for ai,a in enumerate(p["Actors"]):
 assert a["ID"]==("CobaltOriginal","MarigoldOriginal")[ai]
 assert a["Rest"]==["LeftUpper","LeftLower:LeftUpper","RightUpper","RightLower:RightUpper"]
 assert len(a["Frames"])==7
 for fi,f in enumerate(a["Frames"]):
  assert f["Frame"]==(0,12,24,36,48,60,71)[fi]
  assert f["TimeNum"]==f["Frame"] and f["TimeDen"]==12
  assert len(f["Legs"])==2
  for li,l in enumerate(f["Legs"]):
   leg,sign=(("Left",-1),("Right",1))[li]
   assert l["ID"]==leg and l["Parent"]==leg+"Upper" and l["Contact"]=="unknown"
   hip=[f["Root"][0]+.22*sign,f["Root"][1],1.4]
   k=[hip[i]+rotate(l["UpperWorld"],[0,0,-.6])[i] for i in range(3)]
   e=[k[i]+rotate(l["LowerWorld"],[0,0,-.6])[i] for i in range(3)]
   err=max(math.dist(k,l["Knee"]),math.dist(e,l["Ankle"]))
   m=max(m,err)
   assert err<1e-8,(a["ID"],f["Frame"],l["ID"],err)
   if fi==0:
    assert l["UpperWorld"]==l["LowerWorld"]==[0,0,0,1]
   else:
    phase=2*math.pi*f["Frame"]/71+(math.pi if sign<0 else 0)
    target_y=f["Root"][1]+.18*math.sin(phase)
    target_z=.25+.04*max(0,math.cos(phase))
    assert abs(l["Ankle"][1]-target_y)<1e-10
    assert abs(l["Ankle"][2]-target_z)<1e-10
print("W16B3_THIRD_INDEPENDENT_DUAL_LEG_FK_PASS",m)
