package causality

import (
 "strings"
 "testing"
)

func pairFixture()Pair{
 a:=fixture()
 b:=fixture()
 b.SceneSHA256=strings.Repeat("b",64)
 // Deliberately change a real stance source-level coordinate. Candidate is
 // stable and same contact coverage, so this is nonworsening synthetically.
 for i:=range b.Samples{
  if b.Samples[i].Stance{
   b.Samples[i].EvaluatedSole[0]=0
  }
 }
 return Pair{SourceSHA256:strings.Repeat("c",64),Before:a,After:b,
  ContactBandM:.005,ToleranceM:0,ToleranceSpeedMPS:0}
}
func TestNoRegressionIsNotContactPass(t *testing.T){
 p:=pairFixture();c,e:=Compare(p)
 if e!=nil||!strings.Contains(c.Status,"PHYSICAL_CONTACT_UNQUALIFIED"){t.Fatalf("%+v %v",c,e)}
}
func TestRegressionMatrix(t *testing.T){
 scenarios:=[]struct{name string;change func(*Pair);expectError bool}{
  {"hover",func(p *Pair){p.After.Samples[150].EvaluatedSole[2]+=.01},false},
  {"penetration",func(p *Pair){p.After.Samples[150].EvaluatedSole[2]=-.05},false},
  {"slip",func(p *Pair){p.After.Samples[150].EvaluatedSole[0]+=.05},false},
  {"contact coverage",func(p *Pair){
   // Create a control within band in both, then degrade after.
   p.Before.Samples[130].EvaluatedSole[2]=.008
   p.After.Samples[130].EvaluatedSole[2]=.088
  },false},
  {"stance relabel",func(p *Pair){p.After.Samples[150].Stance=false},true},
  {"ground changed",func(p *Pair){p.After.Samples[150].GroundZ=.0},true},
  {"actor swapped",func(p *Pair){p.After.Actor="JUNIPER"},true},
  {"foot swapped",func(p *Pair){p.After.Foot="right"},true},
  {"no source pin",func(p *Pair){p.SourceSHA256=""},true},
  {"identical scene",func(p *Pair){p.After.SceneSHA256=p.Before.SceneSHA256},true},
 }
 for _,tc:=range scenarios{t.Run(tc.name,func(t *testing.T){
  p:=pairFixture();tc.change(&p)
  c,e:=Compare(p)
  if tc.expectError {if e==nil{t.Fatalf("expected invalid pair, got %+v",c)};return}
  if e!=nil{t.Fatalf("unexpected error: %v",e)}
  if c.Status!="RED_NUMERIC_REGRESSION__NO_PHYSICAL_CONTACT_CLAIM" {t.Fatalf("expected RED: %+v",c)}
 })}
}
func TestTolerancesAreDeclaredNotAutoPass(t *testing.T){
 p:=pairFixture();p.ToleranceM=-1
 if _,e:=Compare(p);e==nil{t.Fatal("negative tolerance admitted")}
 p=pairFixture();p.ToleranceSpeedMPS=-1
 if _,e:=Compare(p);e==nil{t.Fatal("negative speed tolerance admitted")}
}
