package main
// W16-B original-only independent solver join; no local-rig or source-clock claim.
import (
 "bytes"
 "crypto/sha256"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "math"
 "os"
 "./solvera"
 "./solverb"
)
type CaseEvidence struct {
 ID string
 Frame int
 TimeNumerator int
 TimeDenominator int
 AStatus string
 BStatus string
 KneeError float64
 WorldFKError float64
 ChildLocalMisuseError float64
}
type Receipt struct {
 Schema string
 SourceRights string
 CoordinateBasis string
 SourceSHA256 string
 ACommit string
 BCommit string
 ClockScope string
 Scope string
 ReachableCompared int
 UnreachablePolicyDifferences int
 MaxKneeError float64
 Cases []CaseEvidence
}
func sub(a,b solverb.V)solverb.V{return solverb.V{a[0]-b[0],a[1]-b[1],a[2]-b[2]}}
func length(a solverb.V)float64{return math.Sqrt(a[0]*a[0]+a[1]*a[1]+a[2]*a[2])}
func cross(a,b solverb.V)solverb.V{return solverb.V{a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]}}
func rotate(q solverb.Q,v solverb.V)solverb.V{
 xyz:=solverb.V{q[0],q[1],q[2]}
 t:=cross(xyz,v)
 for i:=range t {t[i]*=2}
 c:=cross(xyz,t)
 return solverb.V{v[0]+q[3]*t[0]+c[0],v[1]+q[3]*t[1]+c[1],v[2]+q[3]*t[2]+c[2]}
}
func Run(raw []byte)(Receipt,error){
 var f solvera.Fixtures
 d:=json.NewDecoder(bytes.NewReader(raw));d.DisallowUnknownFields()
 if e:=d.Decode(&f);e!=nil{return Receipt{},e}
 var trailing interface{}
 if e:=d.Decode(&trailing);e!=io.EOF{return Receipt{},errors.New("TRAILING_OR_MALFORMED_JSON")}
 if f.Schema!=solvera.FixtureSchema||f.Rights!=solvera.Rights||f.Basis!=solvera.Basis||
 f.Units!="SOURCE_SCENE_UNCALIBRATED"||f.Algorithm!=solvera.Scope||len(f.Cases)!=5 {
  return Receipt{},errors.New("PINNED_SOURCE_ADMISSION_FAILED")
 }
 digest:=sha256.Sum256(raw)
 r:=Receipt{Schema:"scp.walk_w16b_ik_join_receipt.v1",SourceRights:f.Rights,
  CoordinateBasis:f.Basis,SourceSHA256:fmt.Sprintf("%x",digest),
  ACommit:"1967886686d008f8db33e5c90328928d5fe944ed",
  BCommit:"743055edfbfa744b093b9f7a9014891ea83e43d0",
  ClockScope:"SYNTHETIC_12_OVER_1_NOT_SOURCE_MEASURED",
  Scope:"BOUNDED_REACHABLE_POSITION_EQUIVALENCE_UNREACHABLE_POLICY_DIVERGENCE_WORLD_QUATS_NOT_LOCAL_NOT_SKIN_NOT_PRIVATE",
  Cases:[]CaseEvidence{}}
 seen:=map[string]bool{}
 for idx,c:=range f.Cases{
  if c.ID==""||seen[c.ID]{return Receipt{},errors.New("DUPLICATE_OR_MISSING_CASE_ID")}
  seen[c.ID]=true
  a,e:=solvera.Solve(c);if e!=nil{return Receipt{},fmt.Errorf("A_%s: %w",c.ID,e)}
  pole:=sub(solverb.V(c.Pole),solverb.V(c.Start))
  bIn:=solverb.Input{Schema:"scp.walk_3d_ik_synthetic.v1",
   Rights:solvera.Rights,Profile:"forward",
   Hip:solverb.V(c.Start),Ankle:solverb.V(c.Target),Pole:pole,Thigh:c.Upper,Shin:c.Lower}
  b,err:=solverb.Solve(bIn)
  ev:=CaseEvidence{ID:c.ID,Frame:idx*12,TimeNumerator:idx*12,TimeDenominator:12,AStatus:a.Status}
  if !a.Reached{
   if err==nil{return Receipt{},fmt.Errorf("%s:B_FALSE_REACH",c.ID)}
   ev.BStatus="REJECT_UNREACHABLE";r.UnreachablePolicyDifferences++
  }else{
   if err!=nil{return Receipt{},fmt.Errorf("%s:B_FALSE_REJECT:%w",c.ID,err)}
   ev.BStatus="REACHED"
   ev.KneeError=length(sub(solverb.V(a.Knee),b.Knee))
   if ev.KneeError>1e-8{return Receipt{},fmt.Errorf("%s:KNEE_MISMATCH:%g",c.ID,ev.KneeError)}
   if ev.KneeError>r.MaxKneeError{r.MaxKneeError=ev.KneeError}
   upper:=sub(b.Knee,b.Hip);lower:=sub(b.Ankle,b.Knee)
   uw:=rotate(b.UpperLocalQuat,solverb.V{0,-c.Upper,0})
   lw:=rotate(b.LowerLocalQuat,solverb.V{0,-c.Lower,0})
   ev.WorldFKError=math.Max(length(sub(upper,uw)),length(sub(lower,lw)))
   if ev.WorldFKError>1e-8{return Receipt{},fmt.Errorf("%s:WORLD_FK_MISMATCH",c.ID)}
   ev.ChildLocalMisuseError=length(sub(rotate(b.UpperLocalQuat,lw),lower))
   r.ReachableCompared++
  }
  r.Cases=append(r.Cases,ev)
 }
 if r.ReachableCompared!=4||r.UnreachablePolicyDifferences!=1{
  return Receipt{},errors.New("EXPECTED_FOUR_REACHABLE_ONE_SOFTENED")
 }
 return r,nil
}
func main(){
 if len(os.Args)!=3{fmt.Fprintln(os.Stderr,"USAGE: w16b fixture.json receipt.json");os.Exit(2)}
 raw,e:=os.ReadFile(os.Args[1]);if e!=nil{panic(e)}
 r,e:=Run(raw);if e!=nil{panic(e)}
 out,e:=json.MarshalIndent(r,"","  ");if e!=nil{panic(e)}
 if e=os.WriteFile(os.Args[2],append(out,10),0644);e!=nil{panic(e)}
 fmt.Printf("W16B_BOUNDED_JOIN_PASS reachable=%d policy_difference=%d max_knee=%g\n",r.ReachableCompared,r.UnreachablePolicyDifferences,r.MaxKneeError)
}
