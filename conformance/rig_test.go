package conformance
import ("math";"strings";"testing")
func fixture()Rig{return Rig{Bones:[]Bone{{"root",-1},{"left_upperleg",0},{"left_lowerleg",1},{"left_upperarm",0},{"right_upperleg",0},{"right_lowerleg",4},{"right_upperarm",0}},Vertices:[]Vertex{{[]Influence{{0,0.6},{1,0.4}}},{[]Influence{{3,1}}}}}}
func TestSyntheticRigPass(t *testing.T){if e:=ValidateRig(fixture());e!=nil{t.Fatal(e)}}
func TestBadWeightsFailClosed(t *testing.T){
 cases:=[]struct{name string;influences []Influence}{
 {"negative",[]Influence{{0,-0.1},{1,1.1}}},
 {"nonfinite",[]Influence{{0,math.NaN()}}},
 {"wrong-sum",[]Influence{{0,0.8}}},
 {"joint-overflow",[]Influence{{22,1}}},
 {"duplicate",[]Influence{{0,0.5},{0,0.5}}},
 {"five-influences",[]Influence{{0,0.2},{1,0.2},{2,0.2},{3,0.2},{4,0.2}}},
 }
 for _,tc:=range cases{t.Run(tc.name,func(t *testing.T){
  r:=fixture();r.Vertices[0].Weights=tc.influences
  if e:=ValidateRig(r);e==nil{t.Fatal("corrupted weights were accepted")}
 })}
}
func TestRejectParentCycleAndDuplicate(t *testing.T){
 r:=fixture();r.Bones[1].Parent=2
 if e:=ValidateRig(r);e==nil||!strings.Contains(e.Error(),"PARENT_ORDER"){t.Fatal(e)}
 r=fixture();r.Bones[2].Name="root"
 if e:=ValidateRig(r);e==nil{t.Fatal("duplicated bone accepted")}
}
func TestMapCommonNamesExcludesTwists(t *testing.T){
 bones:=[]Bone{{"upperleg_l",-1},{"lowerleg_l",-1},{"upperarm_l",-1},{"upperleg_r",-1},{"lowerleg_r",-1},{"upperarm_r",-1},{"upperleg_l_twist",-1},{"upperarm_r_helper",-1}}
 m,e:=MapWalkRoles(bones)
 if e!=nil||len(m)!=6||m["left_thigh"]!="upperleg_l"||m["right_upperarm"]!="upperarm_r"{t.Fatal(m,e)}
}
func TestFailClosedAmbiguousRoles(t *testing.T){
 bones:=[]Bone{{"upperleg_l",-1},{"thigh_l",-1},{"lowerleg_l",-1},{"upperarm_l",-1},{"upperleg_r",-1},{"lowerleg_r",-1},{"upperarm_r",-1}}
 if _,e:=MapWalkRoles(bones);e==nil||!strings.Contains(e.Error(),"AMBIGUOUS_ROLE"){t.Fatal(e)}
 bones=bones[1:];if _,e:=MapWalkRoles(bones);e!=nil{t.Fatal(e)}
 bones=bones[:len(bones)-1];if _,e:=MapWalkRoles(bones);e==nil||!strings.Contains(e.Error(),"ROLE_MISSING"){t.Fatal(e)}
}
func TestIKSegmentLengthsBothBends(t *testing.T){
 root,target:=Vec2{0,1.0},Vec2{0.4,0.2}
 for _,bend:=range []float64{-1,1}{
  knee,e:=SolveTwoLink(root,target,0.6,0.6,bend)
  if e!=nil||math.Abs(math.Hypot(knee.X-root.X,knee.Z-root.Z)-0.6)>1e-9||math.Abs(math.Hypot(knee.X-target.X,knee.Z-target.Z)-0.6)>1e-9{t.Fatal(knee,e)}
 }
}
func TestIKRejectsUnreachableNonfinite(t *testing.T){
 for _,tc:=range []struct{target Vec2;upper,lower float64}{
  {Vec2{3,0},1,1},{Vec2{0,0},1,1},{Vec2{0.1,0},1,0.1},{Vec2{math.NaN(),0},1,1},
 }{
  if _,e:=SolveTwoLink(Vec2{0,0},tc.target,tc.upper,tc.lower,1);e==nil{t.Fatal("unreachable accepted",tc)}
 }
}
func TestContactDetectsFootSlide(t *testing.T){
 locked:=[]Vec2{{0,0},{0.001,0},{0.001,0.001}}
 d,e:=ContactDrift(locked);if e!=nil||d>0.005{t.Fatal(d,e)}
 sliding:=[]Vec2{{0,0},{0.15,0},{0.3,0}}
 d,e=ContactDrift(sliding);if e!=nil||d<=0.005{t.Fatal("sliding fixture passed",d,e)}
}
func TestContactRejectsInvalid(t *testing.T){
 if _,e:=ContactDrift([]Vec2{{0,0}});e==nil{t.Fatal("single sample accepted")}
 if _,e:=ContactDrift([]Vec2{{0,0},{math.Inf(1),0}});e==nil{t.Fatal("nonfinite accepted")}
}
