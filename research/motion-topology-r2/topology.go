package topology

import (
 "errors"
 "math"
 "strings"
)
type Joint struct { ID,Parent string; Length float64 }
type Skeleton struct { Joints []Joint }
type Pose3 struct { Hip,Knee,Ankle float64 }
type Point struct { X,Y float64 }
type ThreeLink struct { A,B,C float64 }

func (s Skeleton) Validate() error {
 if len(s.Joints)<2||len(s.Joints)>256{return errors.New("unbounded joint count")}
 seen:=make(map[string]Joint,len(s.Joints))
 roots:=0
 for _,j:=range s.Joints{
  if j.ID==""||j.ID==j.Parent{return errors.New("invalid joint id or self-parent")}
  if _,ok:=seen[j.ID];ok{return errors.New("duplicate stable joint id")}
  if !finite(j.Length)||j.Length<0{return errors.New("invalid joint length")}
  if j.Parent==""{roots++}
  seen[j.ID]=j
 }
 if roots!=1{return errors.New("ambiguous root")}
 for _,j:=range s.Joints{
  if j.Parent!=""{
   if _,ok:=seen[j.Parent];!ok{return errors.New("unresolved parent")}
   if strings.HasPrefix(j.ID,"left.")&&strings.HasPrefix(j.Parent,"right."){return errors.New("cross-laterality parent")}
   if strings.HasPrefix(j.ID,"right.")&&strings.HasPrefix(j.Parent,"left."){return errors.New("cross-laterality parent")}
  }
  walk:=map[string]bool{}
  for cur:=j.ID;cur!="";{
   if walk[cur]{return errors.New("cyclic hierarchy")}
   walk[cur]=true
   cur=seen[cur].Parent
  }
 }
 return nil
}
func finite(v float64)bool{return !math.IsNaN(v)&&!math.IsInf(v,0)}
func (r ThreeLink) Validate()error {
 if !finite(r.A)||!finite(r.B)||!finite(r.C)||r.A<=0||r.B<=0||r.C<=0{return errors.New("invalid 3link rig")}
 return nil
}
func FK(r ThreeLink,p Pose3)(Point,Point,Point,error) {
 if e:=r.Validate();e!=nil{return Point{},Point{},Point{},e}
 if !finite(p.Hip)||!finite(p.Knee)||!finite(p.Ankle){return Point{},Point{},Point{},errors.New("nonfinite pose")}
 j1:=Point{r.A*math.Sin(p.Hip),-r.A*math.Cos(p.Hip)}
 j2:=Point{j1.X+r.B*math.Sin(p.Hip+p.Knee),j1.Y-r.B*math.Cos(p.Hip+p.Knee)}
 end:=Point{j2.X+r.C*math.Sin(p.Hip+p.Knee+p.Ankle),j2.Y-r.C*math.Cos(p.Hip+p.Knee+p.Ankle)}
 return j1,j2,end,nil
}
func EffectiveDistal(r ThreeLink,ankle float64)(length,offset float64,err error){
 if e:=r.Validate();e!=nil{return 0,0,e}
 if !finite(ankle){return 0,0,errors.New("nonfinite ankle")}
 x,y:=r.B+r.C*math.Cos(ankle),r.C*math.Sin(ankle)
 return math.Hypot(x,y),math.Atan2(y,x),nil
}
func SolveAtAnkle(r ThreeLink,target Point,ankle float64)(Pose3,error){
 if !finite(target.X)||!finite(target.Y){return Pose3{},errors.New("nonfinite target")}
 length,offset,e:=EffectiveDistal(r,ankle);if e!=nil{return Pose3{},e}
 cosK:=(target.X*target.X+target.Y*target.Y-r.A*r.A-length*length)/(2*r.A*length)
 if cosK>1+1e-10||cosK< -1-1e-10{return Pose3{},errors.New("unreachable source motion for prescribed ankle")}
 cosK=math.Min(1,math.Max(-1,cosK))
 k:=math.Acos(cosK)
 h:=math.Atan2(target.X,-target.Y)-math.Atan2(length*math.Sin(k),r.A+length*math.Cos(k))
 return Pose3{h,k-offset,ankle},nil
}
func Distance(a,b Point)float64{return math.Hypot(a.X-b.X,a.Y-b.Y)}
