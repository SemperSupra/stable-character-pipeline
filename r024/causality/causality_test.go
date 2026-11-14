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
