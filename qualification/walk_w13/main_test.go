package main
import(
 "encoding/json"
 "math"
 "os"
 "testing"
)
func valid(t *testing.T)(Fixtures,[]byte){
 t.Helper();b,e:=os.ReadFile("fixtures.json");if e!=nil{t.Fatal(e)}
 var f Fixtures
 if e=unmarshalFixture(b,&f);e!=nil{t.Fatal(e)}
 return f,b
}
func unmarshalFixture(b []byte,f *Fixtures)error{return json.Unmarshal(b,f)}
func TestOriginalFiveIndependent3DCases(t *testing.T){
 f,b:=valid(t);r,e:=Run(b);if e!=nil{t.Fatal(e)}
 if len(r.Cases)!=len(f.Cases){t.Fatal("case count")}
 for i,x:=range r.Cases{
  if x.ID!=f.Cases[i].ID{t.Fatal("changed ID")}
  if x.UpperResidual>1e-8||x.LowerResidual>1e-8||x.PoleSide<=0{t.Fatal("invalid geometry")}
  if i==4{
   if x.Reached||x.Status!="SOFTENED_UNREACHABLE"||x.TargetGap<=0{t.Fatal("false unreachable acceptance")}
  }else if !x.Reached||x.TargetGap>1e-8{t.Fatal("unexpected unreachable")}
 }
}
func TestRejectParallelPole(t *testing.T){
 f,_:=valid(t);c:=f.Cases[0];c.Pole=c.Target
 if _,e:=Solve(c);e==nil{t.Fatal("accepted singular pole")}
}
func TestRejectZeroTargetDirection(t *testing.T){
 f,_:=valid(t);c:=f.Cases[0];c.Target=c.Start
 if _,e:=Solve(c);e==nil{t.Fatal("accepted zero target")}
}
func TestRejectInvalidLegs(t *testing.T){
 f,_:=valid(t);c:=f.Cases[0];c.Lower=0
 if _,e:=Solve(c);e==nil{t.Fatal("accepted zero shin")}
}
func TestRejectNaNPole(t *testing.T){
 f,_:=valid(t);c:=f.Cases[0];c.Pole[1]=math.NaN()
 if _,e:=Solve(c);e==nil{t.Fatal("accepted NaN")}
}
func TestRejectInnerReach(t *testing.T){
 f,_:=valid(t);c:=f.Cases[0];c.Upper=1.2;c.Lower=.2;c.Target=Vec{0,1.14,0}
 if _,e:=Solve(c);e==nil{t.Fatal("accepted inner reach")}
}
func TestPoleSideIsNotMirrored(t *testing.T){
 f,_:=valid(t);c:=f.Cases[0];a,e:=Solve(c);if e!=nil{t.Fatal(e)}
 // Reflect original pole component across target vector in the IK plane.
 tvec:=sub(c.Target,c.Start);u:=mul(tvec,1/norm(tvec))
 pole:=sub(c.Pole,c.Start);parallel:=mul(u,dot(pole,u))
 flipped:=sub(mul(parallel,2),pole)
 c.Pole=add(c.Start,flipped)
 b,e:=Solve(c);if e!=nil{t.Fatal(e)}
 mid:=add(a.Knee,b.Knee)
 dir:=sub(c.Target,c.Start)
 projection:=add(mul(c.Start,2),mul(dir,dot(sub(a.Knee,c.Start),dir)/(dot(dir,dir))*2))
 if norm(sub(mid,projection))>1e-8{t.Fatal("pole bend not reflected")}
}
func TestRejectChangedRights(t *testing.T){
 f,_:=valid(t);f.Rights="UNKNOWN_RIGHTS"
 b,e:=json.Marshal(f);if e!=nil{t.Fatal(e)}
 if _,e=Run(b);e==nil{t.Fatal("accepted rights")}
}
