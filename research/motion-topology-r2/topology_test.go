package topology

import (
 "math"
 "testing"
)
func fixture()Skeleton{return Skeleton{[]Joint{
 {"root","",0},{"left.hip","root",0.53},{"left.knee","left.hip",.23},{"left.ankle","left.knee",.24},
 {"right.hip","root",.53},{"right.knee","right.hip",.23},{"right.ankle","right.knee",.24},
}}}
func TestTopologyValidAndInvalid(t *testing.T){
 if e:=fixture().Validate();e!=nil{t.Fatal(e)}
 cases:=map[string]func(*Skeleton){
  "duplicate_id":func(s *Skeleton){s.Joints[6].ID="left.ankle"},
  "missing_parent":func(s *Skeleton){s.Joints[6].Parent="absent"},
  "multiple_roots":func(s *Skeleton){s.Joints[6].Parent=""},
  "left_right_swapped_parent":func(s *Skeleton){s.Joints[3].Parent="right.knee"},
  "cycle":func(s *Skeleton){s.Joints[1].Parent="left.ankle"},
  "nonfinite_segment":func(s *Skeleton){s.Joints[3].Length=math.NaN()},
 }
 for name,mutate:=range cases{t.Run(name,func(t *testing.T){s:=fixture();mutate(&s);if e:=s.Validate();e==nil{t.Fatal("invalid topology accepted")}})}
}
func TestEndpointAliasingAcrossDifferentJointConfigurations(t *testing.T){
 r:=ThreeLink{A:.53,B:.23,C:.24}
 // In a 3-link target, prescribing the foot endpoint leaves one joint angle
 // fundamentally undetermined; it cannot be inferred from two-keypoint motion alone.
 target:=Point{.22,-.82}
 p0,e:=SolveAtAnkle(r,target,0);if e!=nil{t.Fatal(e)}
 p1,e:=SolveAtAnkle(r,target,.7);if e!=nil{t.Fatal(e)}
 k0,a0,f0,e:=FK(r,p0);if e!=nil{t.Fatal(e)}
 k1,a1,f1,e:=FK(r,p1);if e!=nil{t.Fatal(e)}
 if Distance(f0,target)>1e-10||Distance(f1,target)>1e-10 {t.Fatalf("solver failed endpoint: %v %v",f0,f1)}
 gap:=math.Max(Distance(k0,k1),Distance(a0,a1))
 t.Logf("same_foot_target delta_ankle=%.3f rad internal_joint_gap=%.9f m endpoint_error=%.10f m",p1.Ankle-p0.Ankle,gap,math.Max(Distance(f0,target),Distance(f1,target)))
 if gap < .01 {t.Fatal("expected internal joint ambiguity not witnessed")}
 if math.Abs(p1.Ankle-p0.Ankle)<.5{t.Fatal("pose differentiation lost")}
 // A preference/reward learned solely from target-foot error sees both as exact.
 if math.Abs(Distance(f0,target)-Distance(f1,target))>1e-10{t.Fatal("endpoint loss unexpectedly discriminated")}
}
func TestPoseBendPolicyAndUnsupportedTarget(t *testing.T){
 r:=ThreeLink{.53,.23,.24}
 target:=Point{.22,-.82}
 if _,e:=SolveAtAnkle(r,target,math.NaN());e==nil{t.Fatal("nonfinite hinge accepted")}
 if _,e:=SolveAtAnkle(r,Point{5,0},0);e==nil{t.Fatal("unreachable target accepted")}
 if _,e:=SolveAtAnkle(ThreeLink{.53,-1,.24},target,0);e==nil{t.Fatal("invalid rig passed")}
 p0,e:=SolveAtAnkle(r,target,0);if e!=nil{t.Fatal(e)}
 p1,e:=SolveAtAnkle(r,target,.7);if e!=nil{t.Fatal(e)}
 // An explicit approved target ankle-range constraint can distinguish poses
 // without inventing a hidden source-performance label.
 min,max:=-.1,.1
 allowed:=func(p Pose3)bool{return p.Ankle>=min&&p.Ankle<=max}
 if !allowed(p0)||allowed(p1){t.Fatal("independent ankle constraint failed to distinguish ambiguous solutions")}
}
