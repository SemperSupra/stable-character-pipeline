// Package synthetic is an original, source-independent FK/time oracle.
// It does NOT parse ASF/AMC/PMX/VMD, infer contact, or certify real mocap.
package synthetic

import (
 "errors"
 "fmt"
 "math"
)

type Vec struct { X, Y, Z float64 }
func (v Vec) add(w Vec) Vec { return Vec{v.X+w.X,v.Y+w.Y,v.Z+w.Z} }
func (v Vec) scale(s float64) Vec { return Vec{v.X*s,v.Y*s,v.Z*s} }
func finite(x float64) bool { return !math.IsNaN(x)&&!math.IsInf(x,0) }
func (v Vec) valid() bool { return finite(v.X)&&finite(v.Y)&&finite(v.Z) }

type Quat struct { W, X, Y, Z float64 }
func (q Quat) norm2() float64 { return q.W*q.W+q.X*q.X+q.Y*q.Y+q.Z*q.Z }
func (q Quat) valid() bool {
 n:=q.norm2()
 return finite(q.W)&&finite(q.X)&&finite(q.Y)&&finite(q.Z)&&finite(n)&&math.Abs(n-1)<1e-8
}
func (q Quat) mul(r Quat) Quat {
 return Quat{
  q.W*r.W-q.X*r.X-q.Y*r.Y-q.Z*r.Z,
  q.W*r.X+q.X*r.W+q.Y*r.Z-q.Z*r.Y,
  q.W*r.Y-q.X*r.Z+q.Y*r.W+q.Z*r.X,
  q.W*r.Z+q.X*r.Y-q.Y*r.X+q.Z*r.W,
 }
}
func (q Quat) rotate(v Vec) Vec {
 p:=q.mul(Quat{X:v.X,Y:v.Y,Z:v.Z}).mul(Quat{W:q.W,X:-q.X,Y:-q.Y,Z:-q.Z})
 return Vec{p.X,p.Y,p.Z}
}
func ZRotation(theta float64) Quat { return Quat{W:math.Cos(theta/2),Z:math.Sin(theta/2)} }
func normalize(q Quat) Quat {
 n:=math.Sqrt(q.norm2());return Quat{q.W/n,q.X/n,q.Y/n,q.Z/n}
}
func Slerp(a,b Quat,t float64) (Quat,error) {
 if !a.valid()||!b.valid()||!finite(t)||t<0||t>1 { return Quat{},errors.New("invalid quaternion or interpolation fraction") }
 d:=a.W*b.W+a.X*b.X+a.Y*b.Y+a.Z*b.Z
 if d<0 {b=Quat{-b.W,-b.X,-b.Y,-b.Z};d=-d}
 if d>1 { d=1 }
 if d>0.9995 {
  return normalize(Quat{a.W+t*(b.W-a.W),a.X+t*(b.X-a.X),a.Y+t*(b.Y-a.Y),a.Z+t*(b.Z-a.Z)}),nil
 }
 theta:=math.Acos(d)
 s:=math.Sin(theta)
 if s==0 {return Quat{},errors.New("degenerate interpolation")}
 ca:=math.Sin((1-t)*theta)/s;cb:=math.Sin(t*theta)/s
 return normalize(Quat{ca*a.W+cb*b.W,ca*a.X+cb*b.X,ca*a.Y+cb*b.Y,ca*a.Z+cb*b.Z}),nil
}
type Bone struct { Name string; Parent int; Offset Vec }
type Pose struct { Root Vec; Local []Quat }
type World struct { Position Vec; Rotation Quat }

func FK(bones []Bone,pose Pose,metersPerUnit float64)([]World,error){
 if len(bones)==0||len(bones)!=len(pose.Local)||!pose.Root.valid()||!finite(metersPerUnit)||metersPerUnit<=0{
  return nil,errors.New("missing source skeleton/pose or explicit positive finite unit scale")
 }
 names:=map[string]bool{};roots:=0
 for i,b:=range bones {
  if b.Name==""||names[b.Name]||!b.Offset.valid()||b.Parent>=len(bones)||b.Parent==i||b.Parent< -1||!pose.Local[i].valid(){
   return nil,fmt.Errorf("invalid bone/rotation at %d",i)
  }
  names[b.Name]=true
  if b.Parent == -1 {roots++}
 }
 if roots!=1{return nil,errors.New("expected exactly one root")}
 world:=make([]World,len(bones));state:=make([]uint8,len(bones))
 var visit func(int)error
 visit=func(i int)error{
  if state[i]==1{return errors.New("cycle in source hierarchy")}
  if state[i]==2{return nil}
  state[i]=1;b:=bones[i];local:=pose.Local[i]
  if b.Parent<0{
   world[i]=World{pose.Root.add(local.rotate(b.Offset)).scale(metersPerUnit),local}
  }else{
   if err:=visit(b.Parent);err!=nil{return err}
   p:=world[b.Parent]
   world[i]=World{p.Position.add(p.Rotation.rotate(b.Offset.scale(metersPerUnit))),normalize(p.Rotation.mul(local))}
  }
  state[i]=2;return nil
 }
 for i:=range bones {if err:=visit(i);err!=nil{return nil,err}}
 return world,nil
}
// Target-map presence/uniqueness only. Actual coordinate transforms are a later gate.
func ValidateNamedMap(bones []Bone,mapping map[string]string)error{
 if len(mapping)!=len(bones){return errors.New("incomplete named target mapping")}
 dst:=map[string]bool{}
 for _,b:=range bones {
  t,ok:=mapping[b.Name]
  if !ok||t==""||dst[t]{return errors.New("missing or aliased target-bone mapping")}
  dst[t]=true
 }
 return nil
}

type Key struct { Frame int; Root Vec; Local []Quat }
// ResampleSourceClock is synthetic, exact-clock resampling with no source unit
// inference and no physical anti-aliasing claim. Source frames must be contiguous
// from zero and the last key must land on an exact target frame.
func ResampleSourceClock(keys []Key,sourceFPS,targetFPS int)([]Key,error){
 if sourceFPS<=0||targetFPS<=0||len(keys)<2||len(keys)>100000 || len(keys[0].Local)==0{
  return nil,errors.New("invalid source/target clock or empty pose")
 }
 n:=len(keys[0].Local)
 for i,k:=range keys{
  if k.Frame!=i||!k.Root.valid()||len(k.Local)!=n{return nil,errors.New("noncontiguous source frame/pose")}
  for _,q:=range k.Local {if !q.valid(){return nil,errors.New("nonunit source rotation")}}
 }
 // Prevent overflow and disallow silent end-frame truncation.
 if int64(len(keys)-1)*int64(targetFPS)>int64(math.MaxInt32)*int64(sourceFPS) {
  return nil,errors.New("unbounded target timeline")
 }
 ticks:=int64(len(keys)-1)*int64(targetFPS)
 if ticks%int64(sourceFPS)!=0 {return nil,errors.New("last frame is not exactly representable at target clock")}
 count:=int(ticks/int64(sourceFPS))+1
 if count>100000{return nil,errors.New("target motion budget exceeded")}
 out:=make([]Key,count)
 for j:=range out{
  pos:=float64(j)*float64(sourceFPS)/float64(targetFPS)
  i:=int(math.Floor(pos));if i>=len(keys)-1 {i=len(keys)-2;pos=float64(len(keys)-1)}
  alpha:=pos-float64(i);if alpha<0||alpha>1+1e-9 {return nil,errors.New("source clock interpolation out of bounds")}
  a,b:=keys[i],keys[i+1]
  r:=a.Root.scale(1-alpha).add(b.Root.scale(alpha))
  rots:=make([]Quat,n)
  for k:=range rots {
   q,err:=Slerp(a.Local[k],b.Local[k],alpha);if err!=nil{return nil,err}
   rots[k]=q
  }
  out[j]=Key{Frame:j,Root:r,Local:rots}
 }
 return out,nil
}
