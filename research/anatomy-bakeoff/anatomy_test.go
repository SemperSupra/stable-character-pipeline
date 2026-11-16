package anatomy

import (
 "math"
 "testing"
)
func TestSyntheticValid(t *testing.T){if e:=Validate(SyntheticScene());e!=nil{t.Fatal(e)}}
func TestVisibilityIsIdempotentAndPhysicsIndependent(t *testing.T){
 s:=SyntheticScene();h,_:=PhysicsDigest(s)
 a,r,e:=SetSystemVisibility(s,"circulatory",false)
 if e!=nil{t.Fatal(e)};if r.Status!="PASS_NARROW"||a.View.Visible["heart"]{t.Fatal("hide failed")}
 b,_,e:=SetSystemVisibility(a,"circulatory",false);if e!=nil{t.Fatal(e)}
 if len(VisibleIDs(a))!=len(VisibleIDs(b)){t.Fatal("not idempotent")}
 x,_:=PhysicsDigest(b);if h!=x{t.Fatal("physics changed")}
 if !s.View.Visible["heart"]{t.Fatal("mutated source")}
}
func TestNegativeInputs(t *testing.T){
 cases:=map[string]func(*Scene){
  "duplicate":func(s *Scene){s.Structures=append(s.Structures,s.Structures[0])},
  "orphan":func(s *Scene){s.Structures[2].ParentID="missing"},
  "cycle":func(s *Scene){s.Structures[0].ParentID="eye"},
  "bad_units":func(s *Scene){s.Units="mm"},
  "unknown_system":func(s *Scene){s.Structures[0].Systems=[]string{"oops"}},
  "missing_thai":func(s *Scene){delete(s.Structures[1].Labels,"th")},
  "bad_force":func(s *Scene){s.Physics.ForceNewtons["heart"]=math.NaN()},
  "invalid_visibility_ref":func(s *Scene){s.View.Visible["unknown"]=true},
  "invalid_opacity":func(s *Scene){s.View.Opacity["skin"]=1.5},
 }
 for name,mut:=range cases{t.Run(name,func(t *testing.T){s:=SyntheticScene();mut(&s);if Validate(s)==nil{t.Fatal("accepted invalid input")}})}
}
func TestUnknownSystemIsRejected(t *testing.T){_,_,e:=SetSystemVisibility(SyntheticScene(),"unknown",true);if e==nil{t.Fatal("accepted unknown system")}}
func TestMultiSystemMembership(t *testing.T){
 s:=SyntheticScene();s.Structures[4].Systems=[]string{"circulatory","endocrine"}
 if e:=Validate(s);e!=nil{t.Fatal(e)}
 out,_,e:=SetSystemVisibility(s,"endocrine",false);if e!=nil{t.Fatal(e)}
 if out.View.Visible["heart"]{t.Fatal("multisystem not applied")}
}
