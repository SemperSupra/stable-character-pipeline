package main

// R4 W04: source-only synthetic rig correspondence and translation
// retargeting. Not actual body recovery, a learned model, or physical contact.
import (
 "crypto/sha256"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "math"
 "os"
 "sort"
)
const class="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
const plane="GLTF_XY_CAMERA_PLANE_UNCALIBRATED"
type Joint struct {ID string `json:"id"`; Parent string `json:"parent"`; Rest [3]float64 `json:"rest"`}
type Rig struct {Name string `json:"name"`; SourceClass string `json:"source_class"`; Plane string `json:"plane"`; Joints []Joint `json:"joints"`}
type Pair struct {Source string `json:"source"`; Target string `json:"target"`}
type Frame struct {SourceMS int `json:"source_ms"`; Local map[string][3]float64 `json:"local"`; Seen map[string]bool `json:"seen"`}
type Sample struct {SourceMS int `json:"source_ms"`; TargetLocal map[string][3]float64 `json:"target_local"`}
type Result struct {
 Schema string `json:"schema"`
 Status string `json:"status"`
 Lane string `json:"lane"`
 InputSHA256 string `json:"input_sha256"`
 JointCount int `json:"joint_count"`
 FrameCount int `json:"frame_count"`
 MaxTargetDelta float64 `json:"max_target_delta_source_units"`
 Samples []Sample `json:"samples,omitempty"`
 SourceRights string `json:"source_rights"`
 TargetRights string `json:"target_rights"`
 RealHumanOrAnimalContactMeasured bool `json:"real_human_or_animal_contact_measured"`
 LearnedModelInference bool `json:"learned_model_inference"`
 Metric3DRecovered bool `json:"metric_3d_recovered"`
 Classification string `json:"classification"`
}
func finite(v [3]float64)bool{return math.IsInf(v[0],0)==false&&math.IsNaN(v[0])==false&&math.IsInf(v[1],0)==false&&math.IsNaN(v[1])==false&&math.IsInf(v[2],0)==false&&math.IsNaN(v[2])==false}
func dist(v [3]float64)float64{return math.Sqrt(v[0]*v[0]+v[1]*v[1]+v[2]*v[2])}
func indexRig(r Rig)(map[string]Joint,string,error){
 if r.Name==""||r.SourceClass!=class||r.Plane!=plane||len(r.Joints)!=4 {return nil,"",errors.New("unadmitted rig provenance, space or joint count")}
 m:=map[string]Joint{};root:=""
 for _,j:=range r.Joints{
   if j.ID==""||!finite(j.Rest)||math.Abs(j.Rest[2])>1e-9{return nil,"",errors.New("invalid local camera-plane transform")}
   if _,ok:=m[j.ID];ok{return nil,"",errors.New("duplicate joint")}
   m[j.ID]=j
   if j.Parent==""{if root!=""{return nil,"",errors.New("multiple roots")};root=j.ID}
 }
 if root==""{return nil,"",errors.New("missing root")}
 for _,j:=range r.Joints{
   if j.Parent!=""{
     if dist(j.Rest)<=1e-8{return nil,"",errors.New("zero-length uncalibrated limb")}
     if _,ok:=m[j.Parent];!ok{return nil,"",errors.New("missing hierarchy parent")}
   }
   seen:=map[string]bool{}
   cur:=j.ID
   for cur!=""{
     if seen[cur]{return nil,"",errors.New("cyclic parent graph")}
     seen[cur]=true
     par,ok:=m[cur]
     if !ok{return nil,"",errors.New("missing parent")}
     cur=par.Parent
   }
 }
 return m,root,nil
}
func check(source,target Rig,pairs []Pair)(map[string]string,map[string]Joint,map[string]Joint,error){
 s,sroot,err:=indexRig(source);if err!=nil{return nil,nil,nil,err}
 t,troot,err:=indexRig(target);if err!=nil{return nil,nil,nil,err}
 if len(pairs)!=len(s){return nil,nil,nil,errors.New("mapping not full coverage")}
 m:=map[string]string{};used:=map[string]bool{}
 for _,p:=range pairs{
   if _,ok:=s[p.Source];!ok{return nil,nil,nil,errors.New("unknown source joint")}
   if _,ok:=t[p.Target];!ok{return nil,nil,nil,errors.New("unknown target joint")}
   if _,ok:=m[p.Source];ok{return nil,nil,nil,errors.New("source joint mapped twice")}
   if used[p.Target]{return nil,nil,nil,errors.New("target joint mapped twice")}
   m[p.Source]=p.Target;used[p.Target]=true
 }
 if m[sroot]!=troot{return nil,nil,nil,errors.New("root correspondence lost")}
 for _,j:=range source.Joints{
    if j.Parent!="" && t[m[j.ID]].Parent!=m[j.Parent]{
        return nil,nil,nil,errors.New("parent ancestry not preserved across rigs")
    }
 }
 return m,s,t,nil
}
func retarget(source,target Rig,pairs []Pair,frames []Frame)([]Sample,float64,error){
 mapping,s,t,err:=check(source,target,pairs)
 if err!=nil{return nil,0,err}
 if len(frames)!=3{return nil,0,errors.New("missing original pose samples")}
 result:=[]Sample{};maxDelta:=0.0
 for i,f:=range frames{
  if f.SourceMS!=i*1000{return nil,0,errors.New("source time gap or interpolation")}
  if len(f.Local)!=len(s)||len(f.Seen)!=len(s){return nil,0,errors.New("pose missing joint fields")}
  item:=Sample{SourceMS:f.SourceMS,TargetLocal:map[string][3]float64{}}
  for sid,j:=range s{
    pose,ok:=f.Local[sid]
    if !ok||!f.Seen[sid]||!finite(pose)||math.Abs(pose[2])>1e-9{
      return nil,0,fmt.Errorf("missing/nonfinite/unobserved camera-plane joint %s",sid)
    }
    dest:=t[mapping[sid]]
    scale:=1.0
    if j.Parent!=""{scale=dist(dest.Rest)/dist(j.Rest)}
    var v [3]float64;var moved [3]float64
    for k:=0;k<3;k++{
      moved[k]=(pose[k]-j.Rest[k])*scale
      v[k]=dest.Rest[k]+moved[k]
    }
    if !finite(v){return nil,0,errors.New("nonfinite target transform")}
    maxDelta=math.Max(maxDelta,dist(moved))
    item.TargetLocal[dest.ID]=v
  }
  result=append(result,item)
 }
 return result,maxDelta,nil
}
func fixture()(Rig,Rig,[]Pair,[]Frame){
 a:=Rig{Name:"synthetic_human_proxy",SourceClass:class,Plane:plane,Joints:[]Joint{
 {ID:"root",Rest:[3]float64{0,0,0}},
 {ID:"hip",Parent:"root",Rest:[3]float64{0,1,0}},
 {ID:"knee",Parent:"hip",Rest:[3]float64{0,-.8,0}},
 {ID:"ankle",Parent:"knee",Rest:[3]float64{0,-.5,0}},
 }}
 b:=Rig{Name:"synthetic_robot_proxy",SourceClass:class,Plane:plane,Joints:[]Joint{
 {ID:"base",Rest:[3]float64{0,0,0}},
 {ID:"pivot",Parent:"base",Rest:[3]float64{0,1.5,0}},
 {ID:"hinge",Parent:"pivot",Rest:[3]float64{0,-.4,0}},
 {ID:"tip",Parent:"hinge",Rest:[3]float64{0,-1,0}},
 }}
 pairs:=[]Pair{{"root","base"},{"hip","pivot"},{"knee","hinge"},{"ankle","tip"}}
 fs:=[]Frame{}
 for i:=0;i<3;i++{
  f:=Frame{SourceMS:i*1000,Local:map[string][3]float64{},Seen:map[string]bool{}}
  for _,j:=range a.Joints{v:=j.Rest;if j.ID=="knee"{v[0]+=float64(i)*.1};f.Local[j.ID]=v;f.Seen[j.ID]=true}
  fs=append(fs,f)
 }
 return a,b,pairs,fs
}
func execute(lane string)(Result,error){
 a,b,pairs,frames:=fixture()
 m:=struct{A Rig;B Rig;Pairs []Pair;Frames []Frame}{a,b,pairs,frames}
 bb,_:=json.Marshal(m);sha:=sha256.Sum256(bb)
 r:=Result{Schema:"stable-character/r4-w04-synthetic-retarget/1",Lane:lane,InputSHA256:fmt.Sprintf("%x",sha),JointCount:4,SourceRights:class,TargetRights:class,
 Classification:"SYNTHETIC_TRANSLATION_MAP_ONLY_NO_REAL_3D_NO_LEARNED_MODEL",RealHumanOrAnimalContactMeasured:false,LearnedModelInference:false,Metric3DRecovered:false}
 switch lane{
 case "map":
  if _,_,_,err:=check(a,b,pairs);err!=nil{return Result{},err}
  r.Status="PASS_SYNTHETIC_NAMED_RIG_CORRESPONDENCE"
 case "motion":
  samples,max,err:=retarget(a,b,pairs,frames);if err!=nil{return Result{},err}
  r.Samples=samples;r.FrameCount=len(samples);r.MaxTargetDelta=max
  if math.Abs(max-.1)>1e-9{return Result{},fmt.Errorf("unexpected target knee motion %.12f",max)}
  // Target knee length = half source knee; 0.2 original delta becomes 0.1.
  if math.Abs(samples[2].TargetLocal["hinge"][0]-.1)>1e-9{return Result{},errors.New("incorrect length scaling")}
  r.Status="PASS_SYNTHETIC_LOCAL_TRANSLATION_SOURCE_CLOCK_ONLY"
 default:return Result{},errors.New("unadmitted lane")
 }
 return r,nil
}
func main(){
 lane:=flag.String("lane","","map or motion")
 out:=flag.String("out","r4w04-receipt.json","output machine receipt")
 flag.Parse()
 r,err:=execute(*lane)
 if err!=nil{fmt.Fprintln(os.Stderr,"R4_W04_FAIL:",err);os.Exit(4)}
 // A deterministic sorted representation across replays; JSON encoding sorts map keys.
 sort.Slice(r.Samples,func(i,j int)bool{return r.Samples[i].SourceMS<r.Samples[j].SourceMS})
 bb,_:=json.MarshalIndent(r,"","  ")
 if err:=os.WriteFile(*out,append(bb,10),0644);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(4)}
 fmt.Println(string(bb))
}
