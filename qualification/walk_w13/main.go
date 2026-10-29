package main

// W13: original source-only analytic 3D two-bone IK. It is not Ozz code.
// Exposes immutable start, world target, pole, bone lengths, reachability and
// a separate clamped target; no skinned rig or real-human claim.
import (
 "crypto/sha256"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "math"
 "os"
)
const Rights="ORIGINAL_PROGRAMMATIC_PROCEDURAL_ONLY"
const FixtureSchema="scp.ik3d.fixtures.v1"
const Basis="RIGHT_HANDED_XYZ_Y_UP_UNCALIBRATED"
const Scope="ANALYTIC_3D_TWO_SEGMENT_POLE_SELECTED_NO_JOINT_LIMITS"
type Vec [3]float64
func sub(a,b Vec)Vec{return Vec{a[0]-b[0],a[1]-b[1],a[2]-b[2]}}
func add(a,b Vec)Vec{return Vec{a[0]+b[0],a[1]+b[1],a[2]+b[2]}}
func mul(a Vec,s float64)Vec{return Vec{a[0]*s,a[1]*s,a[2]*s}}
func dot(a,b Vec)float64{return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]}
func norm(a Vec)float64{return math.Sqrt(dot(a,a))}
func finiteVec(v Vec)bool{for _,x:=range v{if math.IsNaN(x)||math.IsInf(x,0){return false}};return true}
func finite(x float64)bool{return !math.IsNaN(x)&&!math.IsInf(x,0)}
type Case struct{
 ID string `json:"id"`
 Start Vec `json:"start"`
 Target Vec `json:"target"`
 Pole Vec `json:"pole"`
 Upper float64 `json:"upper"`
 Lower float64 `json:"lower"`
 SoftenMargin float64 `json:"soften_margin"`
}
type Fixtures struct{
 Schema string `json:"schema"`
 Rights string `json:"source_rights"`
 Basis string `json:"coordinate_basis"`
 Units string `json:"units"`
 Algorithm string `json:"algorithm"`
 Cases []Case `json:"cases"`
}
type Result struct{
 ID string `json:"id"`
 Status string `json:"status"`
 Reached bool `json:"reached"`
 Start Vec `json:"start"`
 Knee Vec `json:"knee"`
 End Vec `json:"end"`
 Target Vec `json:"target"`
 EffectiveTarget Vec `json:"effective_target"`
 UpperResidual float64 `json:"upper_residual"`
 LowerResidual float64 `json:"lower_residual"`
 TargetGap float64 `json:"target_gap"`
 PoleSide float64 `json:"pole_side"`
}
func Solve(c Case)(Result,error){
 if c.ID==""||!finiteVec(c.Start)||!finiteVec(c.Target)||!finiteVec(c.Pole)||
 !finite(c.Upper)||!finite(c.Lower)||!finite(c.SoftenMargin)||
 c.Upper<=0||c.Lower<=0||c.SoftenMargin<=0||
 c.SoftenMargin>=math.Min(c.Upper,c.Lower)/4{
  return Result{},errors.New("IK_INVALID_INPUT")
 }
 toTarget:=sub(c.Target,c.Start);d:=norm(toTarget)
 if d<=1e-10{return Result{},errors.New("IK_ZERO_TARGET_DIRECTION")}
 minReach:=math.Abs(c.Upper-c.Lower)
 if d<=minReach+1e-8{return Result{},errors.New("IK_INNER_REACH_UNATTAINABLE")}
 forward:=mul(toTarget,1/d)
 poleVec:=sub(c.Pole,c.Start)
 polePlanar:=sub(poleVec,mul(forward,dot(poleVec,forward)))
 n:=norm(polePlanar)
 if n<=1e-8{return Result{},errors.New("IK_SINGULAR_POLE")}
 p:=mul(polePlanar,1/n)
 maxReach:=c.Upper+c.Lower-c.SoftenMargin
 if maxReach<=minReach+1e-8{return Result{},errors.New("IK_BAD_SOFTEN_ENVELOPE")}
 effectiveD:=d
 reached:=true
 if d>maxReach{effectiveD=maxReach;reached=false}
 effective:=add(c.Start,mul(forward,effectiveD))
 along:=(c.Upper*c.Upper-c.Lower*c.Lower+effectiveD*effectiveD)/(2*effectiveD)
 height2:=c.Upper*c.Upper-along*along
 if height2< -1e-10{return Result{},errors.New("IK_NEGATIVE_RADICAND")}
 if height2<0{height2=0}
 knee:=add(add(c.Start,mul(forward,along)),mul(p,math.Sqrt(height2)))
 if !finiteVec(knee){return Result{},errors.New("IK_NONFINITE_KNEE")}
 status:="REACHED"
 if !reached{status="SOFTENED_UNREACHABLE"}
 r:=Result{ID:c.ID,Status:status,Reached:reached,Start:c.Start,
 Knee:knee,End:effective,Target:c.Target,EffectiveTarget:effective,
 UpperResidual:math.Abs(norm(sub(knee,c.Start))-c.Upper),
 LowerResidual:math.Abs(norm(sub(effective,knee))-c.Lower),
 TargetGap:norm(sub(effective,c.Target)),PoleSide:dot(sub(knee,c.Start),p)}
 if r.UpperResidual>1e-8||r.LowerResidual>1e-8||r.PoleSide<=0{
  return Result{},errors.New("IK_GEOMETRY_OR_POLE_SIDE_INVALID")
 }
 return r,nil
}
type Receipt struct{
 Schema string `json:"schema"`
 SourceRights string `json:"source_rights"`
 Basis string `json:"coordinate_basis"`
 SourceSHA string `json:"source_sha256"`
 Algorithm string `json:"algorithm"`
 Solver string `json:"solver"`
 Cases []Result `json:"cases"`
}
func Run(input []byte)(Receipt,error){
 var fs Fixtures
 if err:=json.Unmarshal(input,&fs);err!=nil{return Receipt{},err}
 if fs.Schema!=FixtureSchema||fs.Rights!=Rights||fs.Basis!=Basis||fs.Units!="SOURCE_SCENE_UNCALIBRATED"||fs.Algorithm!=Scope||len(fs.Cases)!=5{
  return Receipt{},errors.New("IK_FIXTURE_RIGHTS_SCHEMA_OR_SET")
 }
 sha:=sha256.Sum256(input)
 r:=Receipt{Schema:"scp.ik3d.receipt.v1",SourceRights:fs.Rights,Basis:fs.Basis,
 SourceSHA:fmt.Sprintf("%x",sha),Algorithm:fs.Algorithm,Solver:"GO_ORIGINAL_ANALYTIC_3D",Cases:[]Result{}}
 seen:=map[string]bool{}
 for _,c:=range fs.Cases{
  if seen[c.ID]{return Receipt{},errors.New("IK_DUPLICATE_CASE")}
  seen[c.ID]=true
  x,e:=Solve(c);if e!=nil{return Receipt{},fmt.Errorf("%s: %w",c.ID,e)}
  r.Cases=append(r.Cases,x)
 }
 return r,nil
}
func main(){
 in:=flag.String("source","","original source fixture JSON")
 out:=flag.String("out","","machine receipt path")
 flag.Parse()
 if *in==""||*out==""{panic("source/out required")}
 b,err:=os.ReadFile(*in);if err!=nil{panic(err)}
 result,err:=Run(b);if err!=nil{panic(err)}
 data,err:=json.MarshalIndent(result,"","  ");if err!=nil{panic(err)}
 if err=os.WriteFile(*out,append(data,10),0644);err!=nil{panic(err)}
 fmt.Printf("W13_GO_ORIGINAL_3D_IK_PASS cases=%d source_sha=%s\n",len(result.Cases),result.SourceSHA)
}
