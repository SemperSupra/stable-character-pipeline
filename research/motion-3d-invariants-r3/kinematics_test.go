package kinematics
import ("math";"testing")
func closeV(a,b V3)float64{return a.Sub(b).Norm()}
func qax(t *testing.T,axis V3,angle float64)Q{t.Helper();q,e:=FromAxisAngle(axis,angle);if e!=nil{t.Fatal(e)};return q}
func TestQuaternionStorageAndNoncommutingRotations(t *testing.T){
 q:=qax(t,V3{1,2,3},.9)
 payload,e:=ToGLTF(q);if e!=nil{t.Fatal(e)}
 decoded,e:=FromGLTF(payload);if e!=nil||q.Dot(decoded)<1-1e-12{t.Fatal("xyzw/wxyz drift",decoded,e)}
 if _,e:=FromGLTF([4]float64{0,0,0,2});e==nil{t.Fatal("nonunit gltf accepted")}
 q0:=qax(t,V3{0,0,1},math.Pi/2)
 q1:=qax(t,V3{0,1,0},math.Pi/3)
 v:=V3{1,0,.2}
 a:=q0.Mul(q1).Rotate(v);b:=q1.Mul(q0).Rotate(v)
 if closeV(a,b)<.25{t.Fatal("noncommutative local frames spuriously equivalent")}
 // q and -q same SO(3) pose; enforce temporal sign continuity.
 mirror,e:=SignContinuous(q0,q0.Neg());if e!=nil||closeV(q0.Rotate(v),mirror.Rotate(v))>1e-12||q0.Dot(mirror)<1-1e-12{t.Fatal("antipodal discontinuity")}
 if _,e:=SignContinuous(Q{},q0);e==nil{t.Fatal("zero quaternion accepted")}
}
func TestProperReflectionParity3D(t *testing.T){
 bones:=[]Bone{
  {"root",-1,V3{.2,.3,.1},qax(t,V3{0,1,1},.6)},
  {"left.upper",0,V3{.4,.1,0},qax(t,V3{1,0,1},.5)},
  {"left.forearm",1,V3{.3,0,.08},qax(t,V3{0,1,0},-.4)},
 }
 w,e:=FK(bones);if e!=nil{t.Fatal(e)}
 mirrored,e:=MirrorBonesX(bones);if e!=nil{t.Fatal(e)}
 mw,e:=FK(mirrored);if e!=nil{t.Fatal(e)}
 v:=V3{.12,.37,-.13}
 for i:=range w{
  if closeV(mw[i].Pos,ReflectX(w[i].Pos))>1e-12{t.Fatal("reflected position drift",i,mw[i],w[i])}
  want:=ReflectX(w[i].Rot.Rotate(v))
  got:=mw[i].Rot.Rotate(ReflectX(v))
  if closeV(got,want)>1e-12{t.Fatal("reflected local-frame drift",i,got,want)}
 }
 // A negative determinant mirror cannot be represented by one proper quaternion:
 // reflection reverses a cross-product orientation.
 x,y:=V3{1,0,0},V3{0,1,0}
 if closeV(ReflectX(x.Cross(y)),ReflectX(x).Cross(ReflectX(y)))<1{t.Fatal("reflection was treated as SO(3)")}
}
func TestBindPoseAndWeightedSkinMirror(t *testing.T){
 bindBones:=[]Bone{
  {"root",-1,V3{.08,0,0},Identity()},
  {"left.elbow",0,V3{.46,0,.02},Identity()},
 }
 animated:=[]Bone{
  {"root",-1,V3{.08,0,0},qax(t,V3{0,0,1},.34)},
  {"left.elbow",0,V3{.46,0,.02},qax(t,V3{0,1,0},.71)},
 }
 bind,e:=FK(bindBones);if e!=nil{t.Fatal(e)}
 posed,e:=FK(animated);if e!=nil{t.Fatal(e)}
 point:=V3{.60,.11,.07}
 weights:=[]Influence{{0,.28},{1,.72}}
 deformed,e:=SkinPosition(point,bind,posed,weights);if e!=nil{t.Fatal(e)}
 if closeV(deformed,point)<.015{t.Fatal("actually weighted skin did not move")}
 mb,e:=MirrorBonesX(bindBones);if e!=nil{t.Fatal(e)}
 ma,e:=MirrorBonesX(animated);if e!=nil{t.Fatal(e)}
 bindM,e:=FK(mb);if e!=nil{t.Fatal(e)}
 poseM,e:=FK(ma);if e!=nil{t.Fatal(e)}
 worldM,e:=SkinPosition(ReflectX(point),bindM,poseM,weights);if e!=nil{t.Fatal(e)}
 if closeV(worldM,ReflectX(deformed))>1e-12{t.Fatal("LBS mirror parity drift",worldM,deformed)}
 t.Logf("weighted_synthetic_skin_displacement_m=%.9f mirror_error_m=%.3g",closeV(point,deformed),closeV(worldM,ReflectX(deformed)))
 for _,bad:=range [][]Influence{{{0,.3},{1,.3}},{{0,.28},{4,.72}},{{0,math.NaN()},{1,1}}}{
  if _,e:=SkinPosition(point,bind,posed,bad);e==nil{t.Fatal("invalid skin influences accepted",bad)}
 }
}
func TestMalformedRigAndSourceImmutability(t *testing.T){
 root:=Bone{"root",-1,V3{},Identity()}
 a:=[]Bone{root,{"c",0,V3{.2,0,0},Identity()}}
 if _,e:=FK(a);e!=nil{t.Fatal(e)}
 cases:=[][]Bone{
  {root,{"broken",3,V3{},Identity()}},
  {root,{"root",0,V3{},Identity()}},
  {root,{"bad",0,V3{math.NaN(),0,0},Identity()}},
  {root,{"bad",0,V3{},Q{W:2}}},
  {{"bad",-1,V3{},Identity()},{"orphan",-1,V3{},Identity()}},
 }
 for _,x:=range cases{if _,e:=FK(x);e==nil{t.Fatal("malformed hierarchy passed",x)}}
 _,e:=FK(a);if e!=nil||a[0]!=root{t.Fatal("source mutated")}
}
