package main
import (
 "encoding/json"
 "math"
 "os"
 "testing"
)
func fixture(t *testing.T)Source{
 t.Helper()
 p:=os.Getenv("W07_TEST_SOURCE")
 if p==""{t.Fatal("W07_TEST_SOURCE_REQUIRED")}
 b,e:=os.ReadFile(p);if e!=nil{t.Fatal(e)}
 var s Source
 if e=json.Unmarshal(b,&s);e!=nil{t.Fatal(e)}
 return s
}
func replay(t *testing.T,s Source,profile string)Transfer{
 t.Helper()
 r,e:=Retarget(s,"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",profile)
 if e!=nil{t.Fatalf("retarget %s: %v",profile,e)}
 return r
}
func TestTwoIndependentProportions(t *testing.T){
 s:=fixture(t)
 a:=replay(t,s,"different-proportions")
 b:=replay(t,s,"compact-and-tall")
 if a.TargetLegs[IDs[0]]==b.TargetLegs[IDs[0]]{t.Fatal("target rig unchanged")}
 if a.Frames[24].Actors[IDs[0]].Joints["knee_left"]==b.Frames[24].Actors[IDs[0]].Joints["knee_left"]{t.Fatal("source knee reused")}
 for _,x:=range []Transfer{a,b}{
  if x.Status!="PASS_ORIGINAL_SYNTHETIC_CONTACT_PRESERVING_RETARGET"||len(x.Frames)!=72||x.MaxSlip>1e-7||x.MaxResidual>1e-8||x.MinGap<1.5{t.Fatalf("invalid pass %+v",x)}
  for i,f:=range x.Frames{
   if f.Index!=s.Frames[i].Index||f.Timestamp!=s.Frames[i].Timestamp{t.Fatal("clock rewritten")}
   for _,id:=range IDs{
    o:=s.Frames[i].Actors[id];p:=f.Actors[id]
    if p.Root!=o.Root||p.Facing!=o.Facing{t.Fatal("root altered")}
    for _,side:=range []string{"left","right"}{
     if p.Joints["ankle_"+side]!=o.Joints["ankle_"+side]||p.Contact[side]!=o.Contact[side]{t.Fatal("contact or planted foot rewritten")}
    }
   }
  }
 }
}
func TestRejectRights(t *testing.T){
 s:=fixture(t);s.Rights="unverified"
 if _,e:=Retarget(s,"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef","different-proportions");e==nil{t.Fatal("accepted rights")}
}
func TestRejectClock(t *testing.T){
 s:=fixture(t);s.Frames[3].Timestamp++
 if _,e:=Retarget(s,"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef","different-proportions");e==nil{t.Fatal("accepted shifted clock")}
}
func TestRejectMissingFrame(t *testing.T){
 s:=fixture(t);s.Frames=s.Frames[:71]
 if _,e:=Retarget(s,"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef","different-proportions");e==nil{t.Fatal("accepted missing frame")}
}
func TestRejectFacing(t *testing.T){
 s:=fixture(t);f:=s.Frames[1].Actors[IDs[0]];f.Facing= -1;s.Frames[1].Actors[IDs[0]]=f
 if _,e:=Retarget(s,"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef","different-proportions");e==nil{t.Fatal("accepted reversed facing")}
}
func TestRejectBadTarget(t *testing.T){
 s:=fixture(t)
 if _,e:=Retarget(s,"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef","unknown-person");e==nil{t.Fatal("accepted unsupported target")}
}
func TestRejectNonfinite(t *testing.T){
 s:=fixture(t);f:=s.Frames[1].Actors[IDs[0]];f.Joints["hip_left"]=V{math.NaN(),1};s.Frames[1].Actors[IDs[0]]=f
 if _,e:=Retarget(s,"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef","different-proportions");e==nil{t.Fatal("accepted NaN")}
}
func TestRejectStanceSkate(t *testing.T){
 s:=fixture(t);id:=IDs[0]
 f:=s.Frames[1].Actors[id]
 if !(f.Contact["left"]&&s.Frames[0].Actors[id].Contact["left"]){t.Fatal("first stance test fixture invalid")}
 p:=f.Joints["ankle_left"];p[0]+=.09;f.Joints["ankle_left"]=p;s.Frames[1].Actors[id]=f
 if _,e:=Retarget(s,"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef","different-proportions");e==nil{t.Fatal("accepted skate")}
}
func TestRejectRootCollision(t *testing.T){
 s:=fixture(t)
 for i:=range s.Frames{
  p:=s.Frames[i].Actors[IDs[1]]
  p.Root=s.Frames[i].Actors[IDs[0]].Root
  s.Frames[i].Actors[IDs[1]]=p
 }
 if _,e:=Retarget(s,"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef","different-proportions");e==nil{t.Fatal("accepted collision")}
}
func TestRejectUnreachableIK(t *testing.T){
 if _,e:=knee(V{0,1.2},V{0,.1},1,Leg{.2,.3});e==nil{t.Fatal("accepted impossible leg")}
}
