// Package regionalwarp provides a bounded, landmark-driven RBF nonrigid
// registration challenger. It NEVER qualifies medical/anatomical placement.
package regionalwarp
import(
 "errors"
 "fmt"
 "math"
 "sort"
 "strings"
 "example.org/scp/anatomy-bakeoff/landmarks"
)
const Schema="scp.anatomy.registration.regional_rbf.v1"
type P=landmarks.Point
type Parameters struct {
 RadiusM float64 `json:"radius_m"`
 Regularization float64 `json:"regularization"`
 MaxLandmarkDisplacementM float64 `json:"max_landmark_displacement_m"`
 MinJacobianRatio float64 `json:"min_jacobian_ratio"`
 MaxJacobianRatio float64 `json:"max_jacobian_ratio"`
}
type Outcome struct{
 Schema string `json:"schema"`
 Status string `json:"status"`
 SourceAtlas string `json:"source_atlas"`
 TargetCharacter string `json:"target_character"`
 SourceSHA256 string `json:"source_sha256"`
 TargetSHA256 string `json:"target_sha256"`
 TrainingLandmarks int `json:"training_landmarks"`
 IndependentHeldOut int `json:"independent_held_out"`
 BaselineTrainingMeanM float64 `json:"baseline_training_mean_m"`
 FittedTrainingMeanM float64 `json:"fitted_training_mean_m"`
 BaselineHeldoutMeanM float64 `json:"baseline_heldout_mean_m"`
 FittedHeldoutMeanM float64 `json:"fitted_heldout_mean_m"`
 MinJacobianRatio float64 `json:"min_jacobian_ratio"`
 MaxJacobianRatio float64 `json:"max_jacobian_ratio"`
 NumericalFoldDetected bool `json:"numerical_fold_detected"`
 Phi string `json:"phi"`
 Missing []string `json:"missing"`
 Caveat string `json:"caveat"`
}
type Candidate struct{
 base [4][4]float64
 centers []P
 weights []P
 params Parameters
}
func Default()Parameters{return Parameters{RadiusM:.65,Regularization:1e-4,MaxLandmarkDisplacementM:.15,MinJacobianRatio:.50,MaxJacobianRatio:2.0}}
func add(a,b P)P{return P{X:a.X+b.X,Y:a.Y+b.Y,Z:a.Z+b.Z}}
func sub(a,b P)P{return P{X:a.X-b.X,Y:a.Y-b.Y,Z:a.Z-b.Z}}
func mul(a P,s float64)P{return P{X:a.X*s,Y:a.Y*s,Z:a.Z*s}}
func dot(a,b P)float64{return a.X*b.X+a.Y*b.Y+a.Z*b.Z}
func norm(a P)float64{return math.Sqrt(dot(a,a))}
func good(x float64)bool{return !math.IsNaN(x)&&!math.IsInf(x,0)}
func hash(s string)bool{
 if len(s)!=64{return false}
 for _,r:=range s{if !strings.ContainsRune("0123456789abcdef",r){return false}}
 return true
}
func transform(m [4][4]float64,p P)P{
 return P{X:m[0][0]*p.X+m[0][1]*p.Y+m[0][2]*p.Z+m[0][3],
 Y:m[1][0]*p.X+m[1][1]*p.Y+m[1][2]*p.Z+m[1][3],
 Z:m[2][0]*p.X+m[2][1]*p.Y+m[2][2]*p.Z+m[2][3]}
}
func kernel(d P,r float64)float64{return math.Exp(-dot(d,d)/(2*r*r))}
func system(a [][]float64,b []float64)([]float64,error){
 n:=len(b)
 if len(a)!=n||n==0{return nil,errors.New("INVALID_LINEAR_SYSTEM")}
 c:=make([][]float64,n)
 for i:=0;i<n;i++{
  if len(a[i])!=n{return nil,errors.New("NON_SQUARE_MATRIX")}
  c[i]=append(append([]float64(nil),a[i]...),b[i])
 }
 for col:=0;col<n;col++{
  pivot:=col
  for row:=col+1;row<n;row++{if math.Abs(c[row][col])>math.Abs(c[pivot][col]){pivot=row}}
  if math.Abs(c[pivot][col])<1e-10{return nil,errors.New("SINGULAR_RBF_SYSTEM")}
  c[col],c[pivot]=c[pivot],c[col]
  for row:=col+1;row<n;row++{
   ratio:=c[row][col]/c[col][col]
   for k:=col;k<=n;k++{c[row][k]-=ratio*c[col][k]}
  }
 }
 res:=make([]float64,n)
 for i:=n-1;i>=0;i--{
  val:=c[i][n]
  for j:=i+1;j<n;j++{val-=c[i][j]*res[j]}
  res[i]=val/c[i][i]
  if !good(res[i]){return nil,errors.New("NONFINITE_COEFFICIENT")}
 }
 return res,nil
}
func validateParams(p Parameters)error{
 if !good(p.RadiusM)||p.RadiusM<.05||p.RadiusM>3||
 !good(p.Regularization)||p.Regularization<1e-8||p.Regularization>.1||
 !good(p.MaxLandmarkDisplacementM)||p.MaxLandmarkDisplacementM<.01||p.MaxLandmarkDisplacementM>.3||
 !good(p.MinJacobianRatio)||p.MinJacobianRatio<=0||p.MinJacobianRatio>=1||
 !good(p.MaxJacobianRatio)||p.MaxJacobianRatio<=1||p.MaxJacobianRatio>5{
  return errors.New("INVALID_FIT_PARAMETERS")
 }
 return nil
}
func checkHeldout(fit landmarks.Pack,heldout []landmarks.Pair)error{
 if len(heldout)<2||len(heldout)>64{return errors.New("INSUFFICIENT_INDEPENDENT_HELDOUT")}
 ids:=map[string]bool{}
 for _,p:=range fit.Pairs{ids[p.ID]=true}
 for _,p:=range heldout{
  if p.ID==""||ids[p.ID]||!hash(p.SourceEvidence)||!hash(p.TargetEvidence)||
    !good(p.SourceUncertaintyM)||!good(p.TargetUncertaintyM)||
    p.SourceUncertaintyM<=0||p.TargetUncertaintyM<=0||
    p.SourceUncertaintyM>.20||p.TargetUncertaintyM>.20{
   return errors.New("INVALID_OR_NONINDEPENDENT_HELDOUT")
  }
  for _,v:=range []float64{p.Source.X,p.Source.Y,p.Source.Z,p.Target.X,p.Target.Y,p.Target.Z}{
   if !good(v){return errors.New("NONFINITE_HELDOUT_COORDINATES")}
  }
  ids[p.ID]=true
 }
 return nil
}
func det3(a [3][3]float64)float64{
 return a[0][0]*(a[1][1]*a[2][2]-a[1][2]*a[2][1])-
 a[0][1]*(a[1][0]*a[2][2]-a[1][2]*a[2][0])+
 a[0][2]*(a[1][0]*a[2][1]-a[1][1]*a[2][0])
}
func (c Candidate)field(x P)P{
 d:=P{}
 for i,ctr:=range c.centers{
  d=add(d,mul(c.weights[i],kernel(sub(x,ctr),c.params.RadiusM)))
 }
 return d
}
func (c Candidate)ApplySource(source P)P{
 x:=transform(c.base,source)
 return add(x,c.field(x))
}
func (c Candidate)jacobianRatio(x P)float64{
 j:=[3][3]float64{{1,0,0},{0,1,0},{0,0,1}}
 for i,ctr:=range c.centers{
  d:=sub(x,ctr);k:=kernel(d,c.params.RadiusM)
  coeff:=-k/(c.params.RadiusM*c.params.RadiusM)
  w:=[]float64{c.weights[i].X,c.weights[i].Y,c.weights[i].Z}
  grad:=[]float64{d.X,d.Y,d.Z}
  for row:=0;row<3;row++{for col:=0;col<3;col++{j[row][col]+=w[row]*grad[col]*coeff}}
 }
 return det3(j)
}
func averages(pairs []landmarks.Pair,apply func(P)P)float64{
 total:=0.0
 for _,v:=range pairs{total+=norm(sub(apply(v.Source),v.Target))}
 return total/float64(len(pairs))
}
func Fit(fit landmarks.Pack,heldout []landmarks.Pair,params Parameters)(Candidate,Outcome,error){
 out:=Outcome{Schema:Schema,Status:"HOLD_INVALID_OR_MISSING_PROVENANCE",
  SourceAtlas:fit.SourceAtlas,TargetCharacter:fit.TargetCharacter,SourceSHA256:fit.SourceSHA256,
  TargetSHA256:fit.TargetSHA256,Phi:"exp(-r²/(2σ²)) regularized, no inferred physical tissue",
  Missing:[]string{},Caveat:"Synthetic validation is not real anatomical registration, patient shape, collision/rig, visual fidelity or physics acceptance."}
 if err:=validateParams(params);err!=nil{return Candidate{},out,err}
 original,err:=landmarks.Evaluate(fit)
 if err!=nil||len(original.Missing)>0||!original.LateralityConsistency||!original.AnteriorPosteriorConsistency{
  return Candidate{},out,errors.New("SOURCE_LANDMARK_GATE_FAILED")
 }
 if err=checkHeldout(fit,heldout);err!=nil{return Candidate{},out,err}
 n:=len(fit.Pairs)
 if n>128{return Candidate{},out,errors.New("EXCESSIVE_LANDMARKS")}
 centers:=make([]P,n);delta:=make([]P,n)
 for i,p:=range fit.Pairs{
  centers[i]=transform(fit.Transform,p.Source)
  delta[i]=sub(p.Target,centers[i])
  if norm(delta[i])>params.MaxLandmarkDisplacementM{
   return Candidate{},out,errors.New("OUTSIDE_SUPPORTED_REGIONAL_DEFORMATION")
  }
 }
 gram:=make([][]float64,n)
 for i:=0;i<n;i++{
  gram[i]=make([]float64,n)
  for j:=0;j<n;j++{gram[i][j]=kernel(sub(centers[i],centers[j]),params.RadiusM)}
  gram[i][i]+=params.Regularization
 }
 weights:=make([]P,n)
 for axis:=0;axis<3;axis++{
  rhs:=make([]float64,n)
  for i,v:=range delta{
   switch axis{case 0:rhs[i]=v.X;case 1:rhs[i]=v.Y;case 2:rhs[i]=v.Z}
  }
  solved,err:=system(gram,rhs);if err!=nil{return Candidate{},out,fmt.Errorf("RBF solver: %w",err)}
  for i,v:=range solved{
   switch axis{case 0:weights[i].X=v;case 1:weights[i].Y=v;case 2:weights[i].Z=v}
  }
 }
 cand:=Candidate{base:fit.Transform,centers:centers,weights:weights,params:params}
 out.TrainingLandmarks=n;out.IndependentHeldOut=len(heldout)
 out.BaselineTrainingMeanM=averages(fit.Pairs,func(p P)P{return transform(fit.Transform,p)})
 out.FittedTrainingMeanM=averages(fit.Pairs,cand.ApplySource)
 out.BaselineHeldoutMeanM=averages(heldout,func(p P)P{return transform(fit.Transform,p)})
 out.FittedHeldoutMeanM=averages(heldout,cand.ApplySource)
 samples:=[]P{}
 samples=append(samples,centers...)
 for _,p:=range heldout{samples=append(samples,transform(fit.Transform,p.Source))}
 for i:=0;i<n;i++{for j:=i+1;j<n&&j<i+5;j++{samples=append(samples,mul(add(centers[i],centers[j]),.5))}}
 if len(samples)==0{return Candidate{},out,errors.New("NO_JACOBIAN_SAMPLES")}
 out.MinJacobianRatio=math.Inf(1)
 out.MaxJacobianRatio=math.Inf(-1)
 for _,p:=range samples{
  ratio:=cand.jacobianRatio(p)
  if !good(ratio){return Candidate{},out,errors.New("NONFINITE_NONRIGID_JACOBIAN")}
  if ratio<out.MinJacobianRatio{out.MinJacobianRatio=ratio}
  if ratio>out.MaxJacobianRatio{out.MaxJacobianRatio=ratio}
 }
 if out.MinJacobianRatio<=0{out.NumericalFoldDetected=true}
 if out.MinJacobianRatio<params.MinJacobianRatio||
    out.MaxJacobianRatio>params.MaxJacobianRatio{
  out.Status="HOLD_NONRIGID_LOCAL_INVERSION_OR_STRAIN"
 }else if out.FittedHeldoutMeanM>=out.BaselineHeldoutMeanM-1e-5{
  out.Status="HOLD_INDEPENDENT_HELDOUT_NO_IMPROVEMENT"
 }else if out.FittedTrainingMeanM>=out.BaselineTrainingMeanM-1e-5{
  out.Status="HOLD_TRAINING_NO_IMPROVEMENT"
 }else{
  out.Status="MEASURED_SYNTHETIC_REGIONAL_FIT_ANATOMY_REVIEW_REQUIRED"
 }
 sort.Strings(out.Missing)
 return cand,out,nil
}
