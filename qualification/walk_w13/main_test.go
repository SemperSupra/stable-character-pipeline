package main
import (
 "math"
 "testing"
)
func run(t *testing.T,profile string)Result{t.Helper();r,e:=solve(canonicalInput(profile));if e!=nil{t.Fatal(e)};return r}
func TestBoth3DPoleEnvelopes(t *testing.T){
 a,b:=run(t,"forward"),run(t,"outward")
 if a.Knee==b.Knee{t.Fatal("pole ignored")}
 for _,r:=range []Result{a,b}{
  if !r.Reachable||r.Status!="PASS_ORIGINAL_3D_POLE_IK_QUATERNION"{t.Fatal("false pass")}
  if r.LengthError>1e-9||r.FKUpperError>1e-9||r.FKLowerError>1e-9{t.Fatal("FK/length error")}
  if r.Knee[2]==0{t.Fatal("3D knee lost all depth")}
 }
}
func TestQuaternionIsUnitAndXYWZRotate(t *testing.T){
 r:=run(t,"forward")
 for _,q:=range []Q{r.UpperLocalQuat,r.LowerLocalQuat}{
  sum:=0.;for _,x:=range q{sum+=x*x}
  if math.Abs(sum-1)>1e-12{t.Fatalf("qnorm %g",sum)}
 }
}
func TestAntipodalQuaternionsEquivalent(t *testing.T){
 q:=run(t,"forward").UpperLocalQuat
 neg:=q;for j:=range neg{neg[j]= -neg[j]}
 a,e:=qangular(q,neg);if e!=nil||math.Abs(a)>1e-7{t.Fatalf("q, -q: %g %v",a,e)}
 v:=V{.32,.2,-.43};if norm(rotate(q,v).Sub(rotate(neg,v)))>1e-12{t.Fatal("antipodal rotation mismatch")}
}
func TestQuaternion180Determinism(t *testing.T){
 q,e:=quatBetween(V{0,-1,0},V{0,1,0});if e!=nil{t.Fatal(e)}
 if norm(rotate(q,V{0,-1,0}).Sub(V{0,1,0}))>1e-9{t.Fatal("180 direction mismatch")}
}
func TestRejectMissingProvenance(t *testing.T){
 x:=canonicalInput("forward");x.Rights="THIRD_PARTY";if _,e:=solve(x);e==nil{t.Fatal("unlicensed accepted")}
}
func TestRejectUnknownProfile(t *testing.T){
 x:=canonicalInput("forward");x.Profile="private-person";if _,e:=solve(x);e==nil{t.Fatal("private admitted")}
}
func TestRejectImpossibleTarget(t *testing.T){
 x:=canonicalInput("forward");x.Ankle=V{50,50,50};if _,e:=solve(x);e==nil{t.Fatal("unreachable accepted")}
}
func TestRejectCoincidentOrDegeneratePole(t *testing.T){
 x:=canonicalInput("forward");x.Pole=x.Ankle.Sub(x.Hip)
 if _,e:=solve(x);e==nil{t.Fatal("parallel pole accepted")}
}
func TestRejectNaNAndZeroLength(t *testing.T){
 x:=canonicalInput("forward");x.Thigh=math.NaN();if _,e:=solve(x);e==nil{t.Fatal("NaN admitted")}
 x=canonicalInput("forward");x.Shin=0;if _,e:=solve(x);e==nil{t.Fatal("zero length admitted")}
}
func TestNormalizedQuaternionRejectNaN(t *testing.T){
 if _,e:=qnormalize(Q{0,0,math.NaN(),1});e==nil{t.Fatal("NaN quaternion accepted")}
 if _,e:=qnormalize(Q{});e==nil{t.Fatal("zero quaternion accepted")}
}
