// Package causality evaluates synthetic target/ankle/sole residual decomposition.
// No inference of anatomical validity, real Blender provenance or actual causation.
package causality
import ("errors";"fmt";"math")
type Vec [3]float64
type Trace struct {
 Tick int
 Stance bool
 Target Vec
 SolvedAnkle Vec
 EvaluatedAnkle Vec
 EvaluatedSole Vec
 GroundZ float64
}
type Plan struct{
 Scope string
 SceneSHA256 string
 Actor string
 Foot string
 Samples []Trace
}
type Metrics struct{
 Status string
 StanceCount int
 MaxTargetToSolvedM float64
 MaxSolvedToEvaluatedM float64
 MaxEvaluatedAnkleToSoleM float64
 MaxSoleToGroundM float64
 WorstTick int
}
func finite(v float64)bool{return !math.IsNaN(v)&&!math.IsInf(v,0)}
func dist(a,b Vec)float64{
 sum:=0.0
 for i:=0;i<3;i++{d:=a[i]-b[i];sum+=d*d}
 return math.Sqrt(sum)
}
func Validate(p Plan)(Metrics,error){
 m:=Metrics{Status:"UNQUALIFIED_SOURCE"}
 if p.Scope!="ORIGINAL_SYNTHETIC_ONLY"||len(p.SceneSHA256)!=64||p.Actor==""||(p.Foot!="left"&&p.Foot!="right"){return m,errors.New("missing provenance or foot")}
 for _,c:=range p.SceneSHA256 {if !((c>='0'&&c<='9')||(c>='a'&&c<='f')){return m,errors.New("invalid SHA256")}}
 if len(p.Samples)!=285{return m,errors.New("expected 285 quarter ticks")}
 maxH:=-math.MaxFloat64
 for i,s:=range p.Samples {
  if s.Tick!=i{return m,fmt.Errorf("invalid quarter tick %d",i)}
  for _,v:=range []Vec{s.Target,s.SolvedAnkle,s.EvaluatedAnkle,s.EvaluatedSole} {
   for _,c:=range v {if !finite(c){return m,fmt.Errorf("nonfinite spatial sample %d",i)}}
  }
  if !finite(s.GroundZ){return m,errors.New("nonfinite ground")}
  if !s.Stance{continue}
  m.StanceCount++
  d1:=dist(s.Target,s.SolvedAnkle)
  d2:=dist(s.SolvedAnkle,s.EvaluatedAnkle)
  d3:=dist(s.EvaluatedAnkle,s.EvaluatedSole)
  h:=s.EvaluatedSole[2]-s.GroundZ
  if d1>m.MaxTargetToSolvedM{m.MaxTargetToSolvedM=d1}
  if d2>m.MaxSolvedToEvaluatedM{m.MaxSolvedToEvaluatedM=d2}
  if d3>m.MaxEvaluatedAnkleToSoleM{m.MaxEvaluatedAnkleToSoleM=d3}
  if h>maxH {maxH=h;m.WorstTick=i}
 }
 if m.StanceCount==0{return m,errors.New("missing stance")}
 m.MaxSoleToGroundM=maxH
 m.Status="PASS_SYNTHETIC_RESIDUAL_DECOMPOSITION_ONLY__CAUSE_UNPROVEN"
 return m,nil
}
