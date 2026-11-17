// Package kinematics qualifies original 3D skeletal invariants for rig conversion.
// No real performer, MPFB/MHR rig, VMD motion, anatomy, contact or VLM.
package kinematics

import ("errors";"math")

type V3 struct{X,Y,Z float64}
func (a V3) Add(b V3)V3{return V3{a.X+b.X,a.Y+b.Y,a.Z+b.Z}}
func (a V3) Sub(b V3)V3{return V3{a.X-b.X,a.Y-b.Y,a.Z-b.Z}}
func (a V3) Mul(s float64)V3{return V3{s*a.X,s*a.Y,s*a.Z}}
func (a V3) Dot(b V3)float64{return a.X*b.X+a.Y*b.Y+a.Z*b.Z}
func (a V3) Cross(b V3)V3{return V3{a.Y*b.Z-a.Z*b.Y,a.Z*b.X-a.X*b.Z,a.X*b.Y-a.Y*b.X}}
func (a V3) Norm()float64{return math.Sqrt(a.Dot(a))}
func finite(n float64)bool{return !math.IsNaN(n)&&!math.IsInf(n,0)}
func (a V3) Valid()bool{return finite(a.X)&&finite(a.Y)&&finite(a.Z)}
func ReflectX(a V3)V3{return V3{-a.X,a.Y,a.Z}}
type Q struct{W,X,Y,Z float64} // typed WXYZ; glTF is XYZW
func Identity()Q{return Q{1,0,0,0}}
func (q Q) Norm()float64{return math.Sqrt(q.W*q.W+q.X*q.X+q.Y*q.Y+q.Z*q.Z)}
func (q Q) Valid()bool{return finite(q.W)&&finite(q.X)&&finite(q.Y)&&finite(q.Z)&&math.Abs(q.Norm()-1)<=1e-6}
func (q Q) Neg()Q{return Q{-q.W,-q.X,-q.Y,-q.Z}}
func (q Q) Dot(r Q)float64{return q.W*r.W+q.X*r.X+q.Y*r.Y+q.Z*r.Z}
func (q Q) Mul(r Q)Q{return Q{
 q.W*r.W-q.X*r.X-q.Y*r.Y-q.Z*r.Z,
 q.W*r.X+q.X*r.W+q.Y*r.Z-q.Z*r.Y,
 q.W*r.Y-q.X*r.Z+q.Y*r.W+q.Z*r.X,
 q.W*r.Z+q.X*r.Y-q.Y*r.X+q.Z*r.W,
}}
func (q Q) Rotate(v V3)V3{
 t:=V3{q.X,q.Y,q.Z}.Cross(v).Mul(2)
 return v.Add(t.Mul(q.W)).Add(V3{q.X,q.Y,q.Z}.Cross(t))
}
func FromAxisAngle(axis V3,a float64)(Q,error){
 if !axis.Valid()||!finite(a)||axis.Norm()<1e-12{return Q{},errors.New("invalid rotation axis-angle")}
 axis=axis.Mul(1/axis.Norm());s:=math.Sin(a/2)
 return Q{math.Cos(a/2),s*axis.X,s*axis.Y,s*axis.Z},nil
}
func MirrorQuatX(q Q)(Q,error){
 if !q.Valid(){return Q{},errors.New("invalid quaternion")}
 // Reflection changes rotation axial-vector parity: q'=(w,x,-y,-z).
 // Reflecting a position is NOT a pure SO(3) quaternion rotation.
 return Q{q.W,q.X,-q.Y,-q.Z},nil
}
func ToGLTF(q Q)([4]float64,error){
 if !q.Valid(){return [4]float64{},errors.New("invalid quaternion")}
 return [4]float64{q.X,q.Y,q.Z,q.W},nil
}
func FromGLTF(v [4]float64)(Q,error){
 q:=Q{v[3],v[0],v[1],v[2]}
 if !q.Valid(){return Q{},errors.New("invalid glTF quaternion")}
 return q,nil
}
func SignContinuous(prev,q Q)(Q,error){
 if !prev.Valid()||!q.Valid(){return Q{},errors.New("bad quaternion sequence")}
 if prev.Dot(q)<0{return q.Neg(),nil}
 return q,nil
}
type Bone struct{ID string;Parent int;RestOffset V3;Local Q}
type Transform struct{Pos V3;Rot Q}
func FK(bones []Bone)([]Transform,error){
 if len(bones)<1||len(bones)>256{return nil,errors.New("invalid bone count")}
 seen:=map[string]bool{}
 out:=make([]Transform,len(bones))
 for i,b:=range bones{
  if b.ID==""||seen[b.ID]||!b.RestOffset.Valid()||!b.Local.Valid(){return nil,errors.New("invalid bone")}
  seen[b.ID]=true
  if b.Parent < -1||b.Parent>=i||((i==0)!=(b.Parent==-1)){return nil,errors.New("not a single rooted topological hierarchy")}
  if b.Parent==-1{out[i]=Transform{b.RestOffset,b.Local};continue}
  parent:=out[b.Parent]
  out[i]=Transform{parent.Pos.Add(parent.Rot.Rotate(b.RestOffset)),parent.Rot.Mul(b.Local)}
  if !out[i].Rot.Valid(){return nil,errors.New("invalid composed rotation")}
 }
 return out,nil
}
func MirrorBonesX(bones []Bone)([]Bone,error){
 out:=make([]Bone,len(bones))
 for i,b:=range bones{
  q,e:=MirrorQuatX(b.Local);if e!=nil{return nil,e}
  out[i]=Bone{b.ID,b.Parent,ReflectX(b.RestOffset),q}
 }
 return out,nil
}
type Influence struct{Bone int;Weight float64}
func SkinPosition(bindWorld V3,bind,animated []Transform,weights []Influence)(V3,error){
 if !bindWorld.Valid()||len(bind)==0||len(bind)!=len(animated)||len(weights)==0{return V3{},errors.New("invalid skin input")}
 out:=V3{};total:=0.0
 for _,inf:=range weights{
  if inf.Bone<0||inf.Bone>=len(bind)||!finite(inf.Weight)||inf.Weight<0||inf.Weight>1{return V3{},errors.New("invalid influence")}
  p:=animated[inf.Bone].Pos.Add(animated[inf.Bone].Rot.Rotate(bindWorld.Sub(bind[inf.Bone].Pos)))
  out=out.Add(p.Mul(inf.Weight));total+=inf.Weight
 }
 if math.Abs(total-1)>1e-6{return V3{},errors.New("skin weights do not sum to one")}
 return out,nil
}
