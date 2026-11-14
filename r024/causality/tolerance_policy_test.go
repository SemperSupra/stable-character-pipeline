package causality
import "testing"

// The candidate must not self-authorize broad numerical tolerances that conceal
// an otherwise RED regression in physical separation or sliding.
func TestSelfAuthorizedToleranceBypassRejected(t *testing.T) {
 scenarios:=[]struct{name string;change func(*Pair)}{
  {"hover 1 metre tolerance",func(p *Pair){
   p.After.Samples[150].EvaluatedSole[2]+=.02
   p.ToleranceM=1
  }},
  {"slip 10 m/s tolerance",func(p *Pair){
   p.After.Samples[150].EvaluatedSole[0]+=.05
   p.ToleranceSpeedMPS=10
  }},
  {"small nonzero measurement slack",func(p *Pair){p.ToleranceM=1e-7}},
 }
 for _,tc:=range scenarios {t.Run(tc.name,func(t *testing.T){
  p:=pairFixture();tc.change(&p)
  c,e:=Compare(p)
  if e==nil||c.Status!="UNQUALIFIED_PAIR"{t.Fatalf("self-relaxed gate accepted: %+v, %v",c,e)}
 })}
}
