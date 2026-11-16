package regionalwarp

import (
 "math"
 "testing"
)
func TestActualRBFAnalyticAndFiniteDifferenceAgreement(t *testing.T){
 fit,hold:=testPack()
 c,result,grid,e:=FitDenseGuard(fit,hold,Default())
 if e!=nil{t.Fatal(e)}
 if result.Status!="MEASURED_SYNTHETIC_REGIONAL_FIT_ANATOMY_REVIEW_REQUIRED"{
  t.Fatalf("synthetic known field not accepted by geometric guard: %s",result.Status)
 }
 if grid.Status!="MEASURED_DENSE_SAMPLE_ONLY_INDEPENDENT_REVIEW_REQUIRED"||
  grid.SampledCells!=729||grid.NumericalChecks<3||grid.MaximumAnalyticNumericDelta>1e-4{
  t.Fatalf("dense independent field error %+v",grid)
 }
 p:=P{X:0,Y:0,Z:1.4}
 if math.Abs(c.jacobianRatio(p)-numericJacobian(c,p))>1e-5{t.Fatal("gradient is inconsistent with actual field")}
}
func TestDetectLocalizedFoldAwayFromControlPoint(t *testing.T){
 // A Gaussian radial field can have Jacobian ratio 1 AT ITS CENTER
 // yet fold at a nearby offset. Sparse landmark-only checks miss it.
 c:=Candidate{
  centers:[]P{{X:0,Y:0,Z:0}},
  weights:[]P{{X:.3,Y:0,Z:0}},
  params:Parameters{RadiusM:.05,Regularization:1e-4,MaxLandmarkDisplacementM:.3,
   MinJacobianRatio:.5,MaxJacobianRatio:2},
 }
 center:=c.jacobianRatio(P{})
 if math.Abs(center-1)>1e-10{t.Fatalf("precondition: center Jacobian %.8f",center)}
 r,e:=AuditDenseGrid(c,GridDomain{Low:P{X:-.10,Y:-.02,Z:-.02},High:P{X:.10,Y:.02,Z:.02},Steps:11})
 if e!=nil{t.Fatal(e)}
 if r.Status!="HOLD_DENSE_JACOBIAN_OR_STRAIN"||r.NonpositiveCount==0||r.MinimumJacobian>=0{
  t.Fatalf("interior fold missed: %+v",r)
 }
}
func TestBadDomainAndResourceBounds(t *testing.T){
 c:=Candidate{centers:[]P{{X:0}},weights:[]P{{X:0}},
  params:Default()}
 cases:=[]GridDomain{
  {Low:P{},High:P{X:.2,Y:.2,Z:.2},Steps:18},
  {Low:P{},High:P{X:.001,Y:.2,Z:.2},Steps:9},
  {Low:P{},High:P{X:math.NaN(),Y:.2,Z:.2},Steps:9},
  {Low:P{},High:P{X:5,Y:.2,Z:.2},Steps:9},
 }
 for _,d:=range cases{if _,e:=AuditDenseGrid(c,d);e==nil{t.Fatal("unbounded grid/domain accepted",d)}}
}
func TestHeldoutGuardCannotBeBypassedByDenseGrid(t *testing.T){
 fit,hold:=testPack()
 for i:=range hold{hold[i].Target=transform(fit.Transform,hold[i].Source)}
 _,out,dense,e:=FitDenseGuard(fit,hold,Default())
 if e!=nil{t.Fatal(e)}
 if out.Status!="HOLD_INDEPENDENT_HELDOUT_NO_IMPROVEMENT"{
  t.Fatalf("dense grid overrode independent bad holdout: %s %+v",out.Status,dense)
 }
}
