package causality
import ("math";"strings";"testing")
func fixture()Plan{
 p:=Plan{Scope:"ORIGINAL_SYNTHETIC_ONLY",SceneSHA256:strings.Repeat("a",64),Actor:"ASTER",Foot:"left"}
 for i:=0;i<285;i++{p.Samples=append(p.Samples,Trace{Tick:i,Stance:i>=100&&i<=268,Target:Vec{0,0,.008},SolvedAnkle:Vec{0,0,.018},EvaluatedAnkle:Vec{0,0,.018},EvaluatedSole:Vec{0,0,.088},GroundZ:.008})}
 return p
}
func TestSynthetic(t *testing.T){m,e:=Validate(fixture());if e!=nil||m.StanceCount!=169||math.Abs(m.MaxSoleToGroundM-.08)>1e-9||!strings.Contains(m.Status,"CAUSE_UNPROVEN"){t.Fatalf("%+v %v",m,e)}}
func TestTamper(t *testing.T){
 tests:=[]struct{name string;edit func(*Plan)}{
 {"wrong scope",func(p *Plan){p.Scope="A001"}},
 {"no provenance",func(p *Plan){p.SceneSHA256="bad"}},
 {"missing tick",func(p *Plan){p.Samples=p.Samples[:284]}},
 {"reordered tick",func(p *Plan){p.Samples[264].Tick=263}},
 {"no stance",func(p *Plan){for i:=range p.Samples{p.Samples[i].Stance=false}}},
 {"bad target",func(p *Plan){p.Samples[264].Target[1]=math.NaN()}},
 {"bad ground",func(p *Plan){p.Samples[264].GroundZ=math.Inf(1)}},
 {"wrong foot",func(p *Plan){p.Foot="unknown"}},
 }
 for _,x:=range tests{t.Run(x.name,func(t *testing.T){p:=fixture();x.edit(&p);if _,e:=Validate(p);e==nil{t.Fatal("invalid fixture accepted")}})}
}
func TestLargeSoleOffsetIsNotCausalProof(t *testing.T){
 p:=fixture();m,e:=Validate(p);if e!=nil{t.Fatal(e)}
 if m.MaxEvaluatedAnkleToSoleM<.06||!strings.Contains(m.Status,"CAUSE_UNPROVEN"){t.Fatal("mechanism prematurely inferred")}
}

func TestFiniteInputDerivedOverflowRejected(t *testing.T){
 cases:=[]struct{name string;edit func(*Plan)}{
  {"squared distance overflow",func(p *Plan){p.Samples[150].Target[0]=1e200}},
  {"coordinate subtraction overflow",func(p *Plan){p.Samples[150].Target[0]=1e308;p.Samples[150].SolvedAnkle[0]=-1e308}},
  {"signed ground clearance overflow",func(p *Plan){p.Samples[150].EvaluatedSole[2]=1e308;p.Samples[150].GroundZ=-1e308}},
 }
 for _,tc:=range cases{t.Run(tc.name,func(t *testing.T){
  p:=fixture();tc.edit(&p)
  m,e:=Validate(p)
  if e==nil||m.Status=="PASS_SYNTHETIC_RESIDUAL_DECOMPOSITION_ONLY__CAUSE_UNPROVEN"{t.Fatalf("nonfinite derived metric accepted: %+v %v",m,e)}
 })}
}
