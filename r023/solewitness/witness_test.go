package solewitness

import (
 "math"
 "strings"
 "testing"
)

func fixture()Witness{
 w:=Witness{Schema:"r023.evaluated_sole_synthetic.v1",
  SceneSHA256:strings.Repeat("a",64),EvaluatedMeshSHA256:strings.Repeat("b",64),
  Ground:Ground{Normal:V3{0,0,1},Offset:0,MetresPerUnit:1}}
 for i:=0;i<285;i++{
  a:=[]Vertex{{Index:1,Position:V3{0,0,.02}},{Index:0,Position:V3{0,0,.005}}}
  b:=[]Vertex{{Index:3,Position:V3{0,0,.01}},{Index:2,Position:V3{0,0,.005}}}
  w.Ticks=append(w.Ticks,Tick{Index:i,Left:a,Right:b,
   ClaimedLeftIndex:0,ClaimedRightIndex:2,ClaimedLeftHeightM:.005,ClaimedRightHeightM:.005})
 }
 return w
}
func TestValidSynthetic(t *testing.T){
 r,e:=Validate(fixture())
 if e!=nil||r.TickCount!=285||!strings.HasPrefix(r.Status,"PASS_SUPPLIED") {t.Fatalf("%+v %v",r,e)}
}
func TestAdversarial(t *testing.T){
 cases:=[]struct{name string;change func(*Witness)}{
 {"forged minimum",func(w *Witness){w.Ticks[99].ClaimedLeftIndex=1}},
 {"swapped feet",func(w *Witness){w.Ticks[9].ClaimedRightIndex=0}},
 {"omitted sample",func(w *Witness){w.Ticks=w.Ticks[:284]}},
 {"missing sole",func(w *Witness){w.Ticks[5].Left=nil}},
 {"duplicate index",func(w *Witness){w.Ticks[4].Right[1].Index=3}},
 {"nonfinite vertex",func(w *Witness){w.Ticks[7].Left[0].Position[2]=math.NaN()}},
 {"incorrect ground",func(w *Witness){w.Ground.Normal=V3{0,0,2}}},
 {"reversed tick",func(w *Witness){w.Ticks[8].Index=7}},
 {"wrong height",func(w *Witness){w.Ticks[40].ClaimedLeftHeightM=.02}},
 {"invalid hash",func(w *Witness){w.SceneSHA256="not_sha"}},
 {"negative vertex index",func(w *Witness){w.Ticks[10].Left[0].Index=-1}},
 }
 for _,tc:=range cases{t.Run(tc.name,func(t *testing.T){
  w:=fixture();tc.change(&w)
  if _,e:=Validate(w);e==nil{t.Fatal("tampered claim was accepted")}
 })}
}
func TestTieSmallestIndex(t *testing.T){
 w:=fixture()
 w.Ticks[0].Left=[]Vertex{{Index:20,Position:V3{0,0,.005}},{Index:0,Position:V3{0,0,.005}}}
 if _,e:=Validate(w);e!=nil{t.Fatal(e)}
 w.Ticks[0].ClaimedLeftIndex=20
 if _,e:=Validate(w);e==nil{t.Fatal("noncanonical tie accepted")}
}
func TestNoRealSourceClaim(t *testing.T){
 r,_:=Validate(fixture())
 if strings.Contains(r.Status,"PHYSICAL_CONTACT_PASS")||strings.Contains(r.Status,"RELEASE_PASS"){t.Fatal("overclaim")}
}
