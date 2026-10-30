package main
import (
 "encoding/json"
 "math"
 "testing"
)
func clone(t Trace)Trace{
 raw,e:=json.Marshal(t);if e!=nil{panic(e)}
 var r Trace
 if e=json.Unmarshal(raw,&r);e!=nil{panic(e)}
 return r
}
func TestPositiveSourceOnlyTrace(t *testing.T){
 for _,p:=range []string{"forward","outward"}{
  if e:=Check(sample(p));e!=nil{t.Fatal(p,e)}
 }
}
func TestHostileGeometryFails(t *testing.T){
 tests:=[]struct{name,code string;mutate func(*Trace)}{
  {"rights","SOURCE_RIGHTS_BASIS_CLOCK_DENIED",func(t *Trace){t.Rights="UNVERIFIED"}},
  {"basis","SOURCE_RIGHTS_BASIS_CLOCK_DENIED",func(t *Trace){t.Basis="BLENDER_Z_UP"}},
  {"clock","SOURCE_RIGHTS_BASIS_CLOCK_DENIED",func(t *Trace){t.FPSNum=30}},
  {"role","UNRECOGNIZED_ORIGINAL_ROLE",func(t *Trace){t.Actors[0].ID="OTHER"}},
  {"time_reversal","CLOCK_OR_NONFINITE_DENIED",func(t *Trace){t.Actors[0].Frames[1].Frame=6}},
  {"nan","CLOCK_OR_NONFINITE_DENIED",func(t *Trace){t.Actors[0].Frames[0].Root[1]=math.NaN()}},
  {"heel_skate","HEEL_OR_TOE_SKATING",func(t *Trace){t.Actors[0].Frames[1].Foot.Heel[0]+=.06}},
  {"toe_skate","HEEL_OR_TOE_SKATING",func(t *Trace){t.Actors[0].Frames[1].Foot.Toe[2]+=.06}},
  {"heel_penetration","PLANTED_HEEL_TOE_PENETRATION_OR_HOVER",func(t *Trace){t.Actors[0].Frames[0].Foot.Heel[1]= -.03}},
  {"toe_hover","PLANTED_HEEL_TOE_PENETRATION_OR_HOVER",func(t *Trace){t.Actors[1].Frames[0].Foot.Toe[1]=.03}},
  {"pole_degenerate","KNEE_REVERSAL_OR_DEGENERATE_POLE",func(t *Trace){t.Actors[0].Frames[1].Pole=t.Actors[0].Frames[1].Hip}},
  {"knee_reversal","KNEE_REVERSAL_OR_DEGENERATE_POLE",func(t *Trace){f:=&t.Actors[0].Frames[1];f.Pole=add(f.Hip,mul(sub(f.Pole,f.Hip),-1))}},
  {"swept_crossing","SWEPT_ACTOR_COLLISION",func(t *Trace){
    for j:=0;j<2;j++{
      t.Actors[0].Frames[j].Root=V{float64(2*j-1),0,1}
      t.Actors[1].Frames[j].Root=V{float64(1-2*j),0,1}
    }
  }},
  {"occluded_actor","CAMERA_FRUSTUM_OR_ACTOR_OCCLUSION",func(t *Trace){
    for j:=0;j<3;j++{
      near:=t.Actors[0].Frames[j].Root
      t.Actors[1].Frames[j].Root=V{near[0],near[1],near[2]+3}
    }
  }},
  {"behind_camera","CAMERA_FRUSTUM_OR_ACTOR_OCCLUSION",func(t *Trace){
    for j:=0;j<3;j++{t.Actors[0].Frames[j].Root[2]= -6}
  }},
 }
 for _,tc:=range tests{t.Run(tc.name,func(t *testing.T){
  x:=clone(sample("forward"));tc.mutate(&x)
  err:=Check(x);if err==nil||err.Error()!=tc.code{t.Fatalf("want=%s got=%v",tc.code,err)}
 })}
}
func TestMidpointSweepAndOffFrustum(t *testing.T){
 d:=sweepMinDistance(V{-1,0,0},V{1,0,0},V{1,0,0},V{-1,0,0})
 if d>1e-12{t.Fatalf("missed midpoint crossing %g",d)}
 if !visible(V{0,0,-5},1,.1,20,V{0,0,0},nil){t.Fatal("front actor not visible")}
 if visible(V{0,0,-5},1,.1,20,V{0,0,-7},nil){t.Fatal("behind camera accepted")}
 if visible(V{0,0,-5},1,.1,20,V{0,0,4},[]V{{0,0,0}}){t.Fatal("foreground occluder accepted")}
}
