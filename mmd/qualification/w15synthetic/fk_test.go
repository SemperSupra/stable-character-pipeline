package synthetic
import (
 "math"
 "testing"
)
func almost(a,b float64)bool{return math.Abs(a-b)<1e-9}
func TestFKExactThreeBone(t *testing.T){
 bones:=[]Bone{{"center",-1,Vec{}},{"arm",0,Vec{X:2}},{"wrist",1,Vec{X:1}}}
 p:=Pose{Root:Vec{X:1},Local:[]Quat{ZRotation(math.Pi/2),ZRotation(math.Pi/2),ZRotation(0)}}
 w,err:=FK(bones,p,0.5);if err!=nil{t.Fatal(err)}
 want:=[]Vec{{X:0.5},{X:0.5,Y:1},{Y:1}}
 for i,v:=range want{
  if !almost(w[i].Position.X,v.X)||!almost(w[i].Position.Y,v.Y)||!almost(w[i].Position.Z,v.Z){t.Fatalf("world[%d]=%+v, want %+v",i,w[i],v)}
 }
 if err:=ValidateNamedMap(bones,map[string]string{"center":"センター","arm":"腕","wrist":"手首"});err!=nil{t.Fatal(err)}
}
func TestFKRedControls(t *testing.T){
 good:=[]Bone{{"root",-1,Vec{}},{"elbow",0,Vec{X:1}},{"hand",1,Vec{X:1}}}
 pose:=Pose{Local:[]Quat{ZRotation(0),ZRotation(0),ZRotation(0)}}
 cases:=[]struct{name string;b []Bone;p Pose;scale float64}{
  {"nonfinite_scale",good,pose,math.NaN()},
  {"zero_scale",good,pose,0},
  {"cycle",[]Bone{{"root",-1,Vec{}},{"elbow",2,Vec{X:1}},{"hand",1,Vec{X:1}}},pose,1},
  {"duplicate_names",[]Bone{{"root",-1,Vec{}},{"root",0,Vec{X:1}},{"hand",1,Vec{X:1}}},pose,1},
  {"two_roots",[]Bone{{"root",-1,Vec{}},{"elbow",-1,Vec{X:1}},{"hand",1,Vec{X:1}}},pose,1},
  {"nonunit_q",good,Pose{Local:[]Quat{{W:2},ZRotation(0),ZRotation(0)}},1},
  {"inf_offset",[]Bone{{"root",-1,Vec{}},{"elbow",0,Vec{X:math.Inf(1)}},{"hand",1,Vec{X:1}}},pose,1},
  {"missing_pose",good,Pose{Local:[]Quat{ZRotation(0)}},1},
 }
 for _,tc:=range cases{t.Run(tc.name,func(t *testing.T){
  if _,err:=FK(tc.b,tc.p,tc.scale);err==nil{t.Fatal("invalid synthetic source accepted")}
 })}
}
func TestFKMappingRedControls(t *testing.T){
 b:=[]Bone{{"root",-1,Vec{}},{"foot",0,Vec{X:1}}}
 for _,m:=range []map[string]string{
  {"root":"center"},
  {"root":"center","foot":"center"},
  {"root":"center","foot":""},
  {"root":"center","unknown":"foot"},
 }{if err:=ValidateNamedMap(b,m);err==nil{t.Fatalf("unearned mapping: %+v",m)}}
}
