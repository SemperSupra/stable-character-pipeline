// W06 real engine metamorphism: two actual Babylon MmdRuntime evaluations
// from ORIGINAL and newly serialized/roundtripped VMD source. Go stdlib.
package main
import("crypto/sha256";"encoding/hex";"encoding/json";"fmt";"math";"os";"path/filepath")
type Bone struct{Name string `json:"name"`;World []float64 `json:"world_xyz"`}
type Frame struct{Frame int `json:"frame"`;Bones []Bone `json:"bones"`}
type Case struct{Case string `json:"case"`;MotionSHA string `json:"motion_sha256"`;Snapshots []Frame `json:"snapshots"`}
type Runtime struct{Status string `json:"status"`;Cases []Case `json:"cases"`}
type Transform struct{SourceSHA string `json:"source_sha256"`;DerivedSHA string `json:"derived_sha256"`;Scale float64 `json:"scale"`;Status string `json:"status"`}
func fail(s string){panic(s)}
func load(p string,x any){b,e:=os.ReadFile(p);if e!=nil{panic(e)};if e=json.Unmarshal(b,x);e!=nil{panic(e)}}
func bone(x Frame,n string)[]float64{for _,b:=range x.Bones{if b.Name==n{return b.World}};return nil}
func dist(x,y []float64)float64{if len(x)!=3||len(y)!=3{return math.Inf(1)};s:=0.0;for i:=0;i<3;i++{if math.IsNaN(x[i])||math.IsNaN(y[i])||math.IsInf(x[i],0)||math.IsInf(y[i],0){return math.Inf(1)};s+=math.Pow(x[i]-y[i],2)};return math.Sqrt(s)}
func g10(x Runtime)Case{if x.Status!="PASS_BABYLON_MMD_ACTUAL_BOUND_RUNTIME_31_FRAMES_ONLY"{fail("not real Babylon source 31 frame runtime")};for _,c:=range x.Cases{if c.Case=="g10"{return c}};fail("missing G10");return Case{}}
func validate(a,b Runtime,t Transform)map[string]any{
 const original="e61ae2953c6cd34904fec2c59ae95fe64ed043ce0cde93e1c3d5db3d12ed149c"
 if t.Status!="PASS_NATIVE_MMD_VMD_SERIALIZER_SOURCE_TRANSFORM_RELOAD"||t.SourceSHA!=original||math.Abs(t.Scale-.75)>1e-8{fail("not original pin and authorized mutation")}
 x,y:=g10(a),g10(b)
 if x.MotionSHA!=original||y.MotionSHA!=t.DerivedSHA||len(x.Snapshots)!=31||len(y.Snapshots)!=31{fail("wrong original/morphed real source run")}
 maxError,maxRoot:=0.0,0.0
 samples:=[]map[string]any{}
 for i:=0;i<31;i++{
  u,v:=x.Snapshots[i],y.Snapshots[i]
  if u.Frame!=i||v.Frame!=i{fail("wrong native source timeline")}
  old,new:=bone(u,"足ＩＫ"),bone(v,"足ＩＫ")
  if len(old)!=3||len(new)!=3{fail("source IK track missing")}
  target:=[]float64{old[0]*t.Scale,old[1]*t.Scale,old[2]*t.Scale}
  delta:=dist(target,new);maxError=math.Max(maxError,delta)
  if delta>.002{fail(fmt.Sprintf("real transformed VMD IK controller mismatch at frame %d %.8f",i,delta))}
  hipDelta:=dist(bone(u,"腰"),bone(v,"腰"));maxRoot=math.Max(maxRoot,hipDelta)
  if hipDelta>.002{fail("source-independent unchanged hip moved")}
  ankleError:=dist(bone(v,"足首"),new)
  if ankleError>.05{fail(fmt.Sprintf("transformed real IK solver diverged from target at %d: %.7f",i,ankleError))}
  samples=append(samples,map[string]any{"frame":i,"transformed_goal_error":delta,"ankle_target_distance_source_unit":ankleError})
 }
 if dist(bone(y.Snapshots[30],"足ＩＫ"),[]float64{.2625,.15,0})>.002{fail("actual altered original terminal VMD target not loaded")}
 return map[string]any{"status":"PASS_31_FRAME_REAL_BABYLON_SOLVER_INPUT_TRANSFORM_METAMORPHISM",
  "schema":"scp.mmd.w06-real-source-transformed-runtime.v1",
  "source_sha256":original,"derived_vmd_sha256":t.DerivedSHA,
  "scale":t.Scale,"frame_count":31,"max_target_equivariance_error_source_unit":maxError,
  "max_unchanged_hip_position_error_source_unit":maxRoot,"samples":samples,
  "not_tested":[]string{"real MikuMikuDance app CCD parity","physics and ground contact","all models and arbitrary perturbations","physical-meter scale"}}
}
func main(){
 if len(os.Args)!=5{fail("usage original.json transformed.json transform_receipt.json output.json")}
 var a,b Runtime;var t Transform;load(os.Args[1],&a);load(os.Args[2],&b);load(os.Args[3],&t)
 report:=validate(a,b,t)
 // Fail-closed source-swap, frozen actual controller and forged source digest.
 checks:=[]struct{Name string;F func(*Runtime,*Transform)}{
  {"wrong_derived_sha",func(r *Runtime,t *Transform){t.DerivedSHA="0"}},
  {"frozen_intermediate_controller",func(r *Runtime,t *Transform){
    c:=g10(*r);c.Snapshots[15].Bones[len(c.Snapshots[15].Bones)-1].World=[]float64{4,4,4}
    for j:=range r.Cases{if r.Cases[j].Case=="g10"{r.Cases[j]=c}}
  }},
  {"false_scale",func(r *Runtime,t *Transform){t.Scale=.9}},
 }
 negatives:=[]string{}
 for _,c:=range checks{
  data,_:=json.Marshal(b);var mutated Runtime;_ =json.Unmarshal(data,&mutated);changed:=t;c.F(&mutated,&changed)
  ok:=false
  func(){defer func(){if recover()!=nil{ok=true}}();validate(a,mutated,changed)}()
  if !ok{fail("red mutation escaped: "+c.Name)}
  negatives=append(negatives,c.Name)
 }
 report["rejected_mutations"]=negatives
 data,_:=json.MarshalIndent(report,"","  ");_ =os.MkdirAll(filepath.Dir(os.Args[4]),0755)
 if err:=os.WriteFile(os.Args[4],append(data,'\n'),0644);err!=nil{panic(err)}
 sum:=sha256.Sum256(data);fmt.Println("W06_ACTUAL_NATIVE_TRANSFORM_VERIFIED",hex.EncodeToString(sum[:]),string(data))
}
