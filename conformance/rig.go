// Package conformance provides synthetic-only animation interchange falsifiers.
// It never loads user-owned models, source footage, or credentials.
package conformance

import (
 "errors"
 "fmt"
 "math"
 "strings"
)
type Bone struct { Name string; Parent int }
type Influence struct { Joint int; Weight float64 }
type Vertex struct { Weights []Influence }
type Rig struct { Bones []Bone; Vertices []Vertex }
type Vec2 struct { X, Z float64 }
func finite(x float64) bool {return !math.IsNaN(x) && !math.IsInf(x,0)}

// ValidateRig checks index bounds, parent-first DAG and skin-weight invariants.
func ValidateRig(r Rig)error{
 if len(r.Bones)==0||len(r.Vertices)==0{return errors.New("EMPTY_RIG")}
 seen:=make(map[string]bool,len(r.Bones))
 for i,b:=range r.Bones {
  n:=strings.ToLower(strings.TrimSpace(b.Name))
  if n==""||seen[n]{return fmt.Errorf("BONE_NAME_INVALID_OR_DUPLICATE:%d",i)}
  seen[n]=true
  if b.Parent< -1||b.Parent>=i{return fmt.Errorf("PARENT_ORDER_OR_CYCLE:%d",i)}
 }
 for i,v:=range r.Vertices{
  if len(v.Weights)<1||len(v.Weights)>4{return fmt.Errorf("INFLUENCE_COUNT:%d",i)}
  indices:=map[int]bool{};sum:=0.0
  for _,w:=range v.Weights{
   if w.Joint<0||w.Joint>=len(r.Bones){return fmt.Errorf("JOINT_INDEX:%d",i)}
   if indices[w.Joint]{return fmt.Errorf("DUPLICATE_INFLUENCE:%d",i)}
   indices[w.Joint]=true
   if !finite(w.Weight)||w.Weight<0||w.Weight>1{return fmt.Errorf("WEIGHT_NONFINITE_OR_RANGE:%d",i)}
   sum+=w.Weight
  }
  if math.Abs(sum-1)>0.005{return fmt.Errorf("WEIGHT_SUM:%d",i)}
 }
 return nil
}
var roles=[]string{"left_thigh","right_thigh","left_shin","right_shin","left_upperarm","right_upperarm"}
func tokens(name string)[]string{
 return strings.FieldsFunc(strings.ToLower(name),func(r rune)bool{return r=='_'||r=='.'||r=='-'||r==' '})
}
func sideOf(name string)string{
 t:=tokens(name)
 for _,s:=range t{if s=="left"||s=="l"{return "left"};if s=="right"||s=="r"{return "right"}}
 compact:=strings.Join(t,"")
 if strings.HasPrefix(compact,"left")||strings.HasSuffix(compact,"left"){return "left"}
 if strings.HasPrefix(compact,"right")||strings.HasSuffix(compact,"right"){return "right"}
 return ""
}
func partOf(name string)string{
 s:=strings.Join(tokens(name),"")
 if strings.Contains(s,"twist")||strings.Contains(s,"helper")||strings.Contains(s,"roll"){return ""}
 switch{
 case strings.Contains(s,"upperleg")||strings.Contains(s,"thigh"):return "thigh"
 case strings.Contains(s,"lowerleg")||strings.Contains(s,"shin")||strings.Contains(s,"calf"):return "shin"
 case strings.Contains(s,"upperarm")||strings.Contains(s,"uparm"):return "upperarm"
 default:return ""
 }
}
// MapWalkRoles rejects missing/ambiguous bones instead of silently guessing.
func MapWalkRoles(bones []Bone)(map[string]string,error){
 out:=make(map[string]string,6)
 for _,b:=range bones{
  side,part:=sideOf(b.Name),partOf(b.Name)
  if side==""||part==""{continue}
  role:=side+"_"+part
  if previous,ok:=out[role];ok{return nil,fmt.Errorf("AMBIGUOUS_ROLE:%s:%s:%s",role,previous,b.Name)}
  out[role]=b.Name
 }
 for _,role:=range roles{if _,ok:=out[role];!ok{return nil,fmt.Errorf("ROLE_MISSING:%s",role)}}
 return out,nil
}
// SolveTwoLink returns the knee of a synthetic planar two-link leg.
// kneeSign is +/-1; no real person's joint placement is inferred.
func SolveTwoLink(root,target Vec2,upper,lower,kneeSign float64)(Vec2,error){
 for _,v:=range []float64{root.X,root.Z,target.X,target.Z,upper,lower,kneeSign}{
  if !finite(v){return Vec2{},errors.New("NONFINITE_IK")}
 }
 if upper<=0||lower<=0||math.Abs(kneeSign)!=1{return Vec2{},errors.New("INVALID_IK_PARAMETER")}
 dx,dz:=target.X-root.X,target.Z-root.Z
 d:=math.Hypot(dx,dz)
 if d<1e-9||d>upper+lower+1e-8||d<math.Abs(upper-lower)-1e-8{return Vec2{},errors.New("IK_UNREACHABLE")}
 a:=(upper*upper-lower*lower+d*d)/(2*d);h2:=upper*upper-a*a
 if h2< -1e-8{return Vec2{},errors.New("IK_UNREACHABLE")}
 h:=math.Sqrt(math.Max(0,h2));ux,uz:=dx/d,dz/d
 return Vec2{X:root.X+a*ux-kneeSign*h*uz,Z:root.Z+a*uz+kneeSign*h*ux},nil
}
// ContactDrift checks synthetic stance displacement, not natural human gait.
func ContactDrift(samples []Vec2)(float64,error){
 if len(samples)<2{return 0,errors.New("CONTACT_SAMPLES_MISSING")}
 first:=samples[0];largest:=0.0
 for _,p:=range samples{
  if !finite(p.X)||!finite(p.Z){return 0,errors.New("NONFINITE_CONTACT")}
  d:=math.Hypot(p.X-first.X,p.Z-first.Z)
  if d>largest{largest=d}
 }
 return largest,nil
}
