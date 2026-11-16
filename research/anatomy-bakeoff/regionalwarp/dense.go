// Dense region-specific Jacobian qualification for original R036 RBF.
// This is a bounded sampling test, not a continuous diffeomorphism proof.
package regionalwarp

import (
 "errors"
 "math"
 "example.org/scp/anatomy-bakeoff/landmarks"
)
type GridDomain struct{
 Low P `json:"low_m"`
 High P `json:"high_m"`
 Steps int `json:"steps_per_axis"`
}
type DenseReceipt struct{
 Schema string `json:"schema"`
 Status string `json:"status"`
 Domain GridDomain `json:"domain"`
 SampledCells int `json:"sampled_points"`
 MinimumJacobian float64 `json:"minimum_jacobian_ratio"`
 MaximumJacobian float64 `json:"maximum_jacobian_ratio"`
 Violations int `json:"jacobian_limit_violations"`
 NonpositiveCount int `json:"nonpositive_jacobian_count"`
 WorstPoint P `json:"worst_point_m"`
 MaximumAnalyticNumericDelta float64 `json:"max_analytic_numeric_abs_delta"`
 NumericalChecks int `json:"numeric_checks"`
 Caveat string `json:"caveat"`
}
func vec(p P)[3]float64{return [3]float64{p.X,p.Y,p.Z}}
func finiteP(p P)bool{return good(p.X)&&good(p.Y)&&good(p.Z)}
func rangeCheck(d GridDomain)error{
 if !finiteP(d.Low)||!finiteP(d.High){return errors.New("NONFINITE_AUDIT_DOMAIN")}
 if d.Steps<5||d.Steps>17{return errors.New("UNBOUNDED_GRID_SIZE")}
 low,high:=vec(d.Low),vec(d.High)
 for i:=0;i<3;i++{
  if high[i]-low[i]<.01||high[i]-low[i]>4{return errors.New("INVALID_REGION_EXTENT")}
 }
 return nil
}
func numericJacobian(c Candidate,x P)float64{
 // Independent finite-difference derivative of actual x+field(x), not
 // an expression copied from the analytic Gaussian gradient routine.
 eps:=1e-5
 base:=func(p P)P{return add(p,c.field(p))}
 a:=[3][3]float64{}
 for col:=0;col<3;col++{
  positive,negative:=x,x
  switch col{
  case 0:positive.X+=eps;negative.X-=eps
  case 1:positive.Y+=eps;negative.Y-=eps
  case 2:positive.Z+=eps;negative.Z-=eps
  }
  difference:=mul(sub(base(positive),base(negative)),1/(2*eps))
  a[0][col],a[1][col],a[2][col]=difference.X,difference.Y,difference.Z
 }
 return det3(a)
}
func AuditDenseGrid(c Candidate,d GridDomain)(DenseReceipt,error){
 out:=DenseReceipt{Schema:"scp.anatomy.registration.regional_dense_jacobian.v1",
  Status:"HOLD_NO_DENSE_QUALIFICATION",Domain:d,
  MinimumJacobian:math.Inf(1),MaximumJacobian:math.Inf(-1),
  Caveat:"Finite deterministic 3D grid is NOT a mathematical proof of global injectivity, anatomical biomechanical properties or correct person-specific geometry."}
 if e:=rangeCheck(d);e!=nil{return out,e}
 if e:=validateParams(c.params);e!=nil{return out,e}
 if len(c.centers)==0||len(c.centers)!=len(c.weights)||len(c.centers)>128{return out,errors.New("INVALID_OR_EXCESSIVE_RBF_CENTERS")}
 low,high:=vec(d.Low),vec(d.High)
 for ix:=0;ix<d.Steps;ix++{
  for iy:=0;iy<d.Steps;iy++{
   for iz:=0;iz<d.Steps;iz++{
    x:=P{
     X:low[0]+(high[0]-low[0])*float64(ix)/float64(d.Steps-1),
     Y:low[1]+(high[1]-low[1])*float64(iy)/float64(d.Steps-1),
     Z:low[2]+(high[2]-low[2])*float64(iz)/float64(d.Steps-1)}
    v:=c.jacobianRatio(x)
    if !good(v){return out,errors.New("NONFINITE_ANALYTIC_JACOBIAN")}
    out.SampledCells++
    if v<out.MinimumJacobian{out.MinimumJacobian=v;out.WorstPoint=x}
    if v>out.MaximumJacobian{out.MaximumJacobian=v}
    if v<=0{out.NonpositiveCount++}
    if v<c.params.MinJacobianRatio||v>c.params.MaxJacobianRatio{out.Violations++}
    // Four corners and the center cross-check distinct numerical method.
    if (ix==0&&iy==0&&iz==0)||(ix==d.Steps-1&&iy==d.Steps-1&&iz==d.Steps-1)||
      (ix==d.Steps/2&&iy==d.Steps/2&&iz==d.Steps/2)||
      (ix==d.Steps/2&&iy==0&&iz==d.Steps/2){
     nv:=numericJacobian(c,x)
     if !good(nv){return out,errors.New("NONFINITE_NUMERICAL_JACOBIAN")}
     delta:=math.Abs(nv-v)
     if delta>out.MaximumAnalyticNumericDelta{out.MaximumAnalyticNumericDelta=delta}
     out.NumericalChecks++
    }
   }
  }
 }
 if out.NumericalChecks<3{return out,errors.New("INSUFFICIENT_INDEPENDENT_DIFFERENTIAL_CHECKS")}
 if out.MaximumAnalyticNumericDelta>1e-4{
  out.Status="HOLD_ANALYTIC_NUMERICAL_JACOBIAN_DISAGREE"
 }else if out.Violations>0{
  out.Status="HOLD_DENSE_JACOBIAN_OR_STRAIN"
 }else{
  out.Status="MEASURED_DENSE_SAMPLE_ONLY_INDEPENDENT_REVIEW_REQUIRED"
 }
 return out,nil
}
func DomainFromLandmarks(p landmarks.Pack,heldout []landmarks.Pair,margin float64,steps int)(GridDomain,error){
 d:=GridDomain{Steps:steps,Low:P{X:math.Inf(1),Y:math.Inf(1),Z:math.Inf(1)},High:P{X:math.Inf(-1),Y:math.Inf(-1),Z:math.Inf(-1)}}
 if !good(margin)||margin<.02||margin>.3{return d,errors.New("INVALID_MARGIN")}
 positions:=[]P{}
 for _,p0:=range p.Pairs{positions=append(positions,transform(p.Transform,p0.Source))}
 for _,p0:=range heldout{positions=append(positions,transform(p.Transform,p0.Source))}
 if len(positions)<10{return d,errors.New("INSUFFICIENT_SOURCE_LANDMARK_DOMAIN")}
 for _,x:=range positions{
  if !finiteP(x){return d,errors.New("NONFINITE_LANDMARK_DOMAIN")}
  if x.X<d.Low.X{d.Low.X=x.X};if x.X>d.High.X{d.High.X=x.X}
  if x.Y<d.Low.Y{d.Low.Y=x.Y};if x.Y>d.High.Y{d.High.Y=x.Y}
  if x.Z<d.Low.Z{d.Low.Z=x.Z};if x.Z>d.High.Z{d.High.Z=x.Z}
 }
 d.Low=sub(d.Low,P{X:margin,Y:margin,Z:margin});d.High=add(d.High,P{X:margin,Y:margin,Z:margin})
 return d,rangeCheck(d)
}
func FitDenseGuard(fit landmarks.Pack,heldout []landmarks.Pair,params Parameters)(Candidate,Outcome,DenseReceipt,error){
 c,receipt,err:=Fit(fit,heldout,params)
 if err!=nil{return c,receipt,DenseReceipt{},err}
 d,e:=DomainFromLandmarks(fit,heldout,.08,9)
 if e!=nil{return c,receipt,DenseReceipt{},e}
 dense,e:=AuditDenseGrid(c,d)
 if e!=nil{return c,receipt,dense,e}
 if dense.Status!="MEASURED_DENSE_SAMPLE_ONLY_INDEPENDENT_REVIEW_REQUIRED"{
  receipt.Status="HOLD_DENSE_JACOBIAN_OR_DISAGREEMENT"
 }
 return c,receipt,dense,nil
}
