package causality

import (
 "errors"
 "fmt"
 "math"
)

// Pair explicitly distinguishes a same-source before/after synthetic comparison
// from evidence that two real scenes were generated from identical source assets.
type Pair struct {
 SourceSHA256 string
 Before Plan
 After Plan
 ContactBandM float64
 ToleranceM float64
 ToleranceSpeedMPS float64
}
type ContactStats struct {
 StanceCount int
 ContactCount int
 Coverage float64
 PeakHoverM float64
 PeakPenetrationM float64
 PeakSoleSlipMPS float64
}
type Comparison struct {
 Status string
 Before ContactStats
 After ContactStats
}
func sourceDigest(s string)bool{
 if len(s)!=64{return false}
 for _,c:=range s {if !((c>='0'&&c<='9')||(c>='a'&&c<='f')){return false}}
 return true
}
func stats(p Plan,band float64)(ContactStats,error){
 s:=ContactStats{PeakHoverM:0,PeakPenetrationM:0}
 // Exactly 4 quarter samples at 12 fps = 48Hz. A new stance segment starts
 // whenever the previous tick is not labelled stance.
 for i,t:=range p.Samples{
  if !t.Stance{continue}
  s.StanceCount++
  h:=t.EvaluatedSole[2]-t.GroundZ
  if math.Abs(h)<=band{s.ContactCount++}
  if h>s.PeakHoverM{s.PeakHoverM=h}
  if -h>s.PeakPenetrationM{s.PeakPenetrationM=-h}
  if i>0&&p.Samples[i-1].Stance{
   prev:=p.Samples[i-1].EvaluatedSole
   dx:=t.EvaluatedSole[0]-prev[0]
   dy:=t.EvaluatedSole[1]-prev[1]
   slip:=math.Hypot(dx,dy)*48
   if !finite(slip){return s,errors.New("nonfinite slip")}
   if slip>s.PeakSoleSlipMPS{s.PeakSoleSlipMPS=slip}
  }
 }
 if s.StanceCount==0{return s,errors.New("empty stance")}
 s.Coverage=float64(s.ContactCount)/float64(s.StanceCount)
 return s,nil
}
func Compare(p Pair)(Comparison,error){
 c:=Comparison{Status:"UNQUALIFIED_PAIR"}
 if !sourceDigest(p.SourceSHA256)||!finite(p.ContactBandM)||p.ContactBandM<=0||
  !finite(p.ToleranceM)||p.ToleranceM<0||
  !finite(p.ToleranceSpeedMPS)||p.ToleranceSpeedMPS<0{
  return c,errors.New("missing source pin or invalid declared measurement tolerance")
 }
 // The paired candidate is not itself an authority to relax regression policy.
 // No independent policy signature/registry is implemented in this module.
 // Until one exists, tolerances MUST be exactly zero. Floating noise should
 // be resolved by a stable evaluation protocol, never a candidate override.
 if p.ToleranceM!=0||p.ToleranceSpeedMPS!=0{
  return c,errors.New("nonzero tolerances require an external trusted policy; not admitted in this synthetic gate")
 }
 if _,e:=Validate(p.Before);e!=nil{return c,fmt.Errorf("baseline: %w",e)}
 if _,e:=Validate(p.After);e!=nil{return c,fmt.Errorf("candidate: %w",e)}
 if p.Before.Actor!=p.After.Actor||p.Before.Foot!=p.After.Foot{
  return c,errors.New("actor/foot changed")
 }
 if p.Before.SceneSHA256==p.After.SceneSHA256 {
  return c,errors.New("before/after scene hashes identical; change evidence missing")
 }
 for i:=range p.Before.Samples{
  a,b:=p.Before.Samples[i],p.After.Samples[i]
  if a.Stance!=b.Stance||a.GroundZ!=b.GroundZ{
   return c,fmt.Errorf("stance labels or ground changed at tick %d",i)
  }
 }
 // Aggregate maxima can conceal local damage: a pre-existing 80 mm hover
 // can mask a new 25 mm hover at a previously grounded tick. Evaluate each
 // time-aligned stance sample before considering aggregate non-regression.
 localRegression:=false
 for i:=range p.Before.Samples{
  a,b:=p.Before.Samples[i],p.After.Samples[i]
  if !a.Stance{continue}
  ha:=a.EvaluatedSole[2]-a.GroundZ
  hb:=b.EvaluatedSole[2]-b.GroundZ
  if math.Max(0,hb)>math.Max(0,ha)+p.ToleranceM ||
   math.Max(0,-hb)>math.Max(0,-ha)+p.ToleranceM ||
   (math.Abs(ha)<=p.ContactBandM && math.Abs(hb)>p.ContactBandM){
   localRegression=true
  }
  if i>0&&p.Before.Samples[i-1].Stance {
   prevA:=p.Before.Samples[i-1].EvaluatedSole
   prevB:=p.After.Samples[i-1].EvaluatedSole
   slipA:=math.Hypot(a.EvaluatedSole[0]-prevA[0],a.EvaluatedSole[1]-prevA[1])*48
   slipB:=math.Hypot(b.EvaluatedSole[0]-prevB[0],b.EvaluatedSole[1]-prevB[1])*48
   if slipB>slipA+p.ToleranceSpeedMPS {localRegression=true}
  }
 }
 var e error
 c.Before,e=stats(p.Before,p.ContactBandM);if e!=nil{return c,e}
 c.After,e=stats(p.After,p.ContactBandM);if e!=nil{return c,e}
 // Do not allow coverage regressions hidden inside one coarse rounded number.
 if localRegression||c.After.ContactCount<c.Before.ContactCount||
  c.After.PeakHoverM>c.Before.PeakHoverM+p.ToleranceM||
  c.After.PeakPenetrationM>c.Before.PeakPenetrationM+p.ToleranceM||
  c.After.PeakSoleSlipMPS>c.Before.PeakSoleSlipMPS+p.ToleranceSpeedMPS{
  c.Status="RED_NUMERIC_REGRESSION__NO_PHYSICAL_CONTACT_CLAIM"
  return c,nil
 }
 c.Status="NO_DECLARED_NUMERIC_REGRESSION__PHYSICAL_CONTACT_UNQUALIFIED"
 return c,nil
}
