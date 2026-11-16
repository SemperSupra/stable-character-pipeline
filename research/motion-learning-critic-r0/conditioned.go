package motion

import (
 "errors"
 "math"
)

// ConditionedModel is a tiny polynomial teacher-student surrogate, NOT a neural
// model, human-motion retargeter, or physically qualified animation solver.
type ConditionedModel struct {
 SourceRig Rig
 MinUpper,MaxUpper,MinLower,MaxLower float64
 HipWeights,KneeWeights []float64
}
func rigFeatures(p Pose, target Rig) []float64 {
 h,k:=p.Hip,p.Knee
 du,dl:=target.Upper-.53,target.Lower-.47
 return []float64{
  1,h,k,du,dl,du*h,dl*h,du*k,dl*k,
  du*du,dl*dl,du*dl,h*k,k*k,h*h,
  du*k*k,dl*k*k,du*h*k,dl*h*k,du*du*k,dl*dl*k,
 }
}

// TrainConditioned trains on multiple explicitly different *target geometries*.
// Labels come from exact analytic IK; no authentic motion or capture is used.
func TrainConditioned(src Rig,targetRigs []Rig, sourcePoses []Pose)(ConditionedModel,error){
 if e:=src.Check();e!=nil{return ConditionedModel{},e}
 if len(targetRigs)<3||len(sourcePoses)<6{return ConditionedModel{},errors.New("insufficient training")}
 n:=21
 xtx:=make([][]float64,n);for i:=range xtx{xtx[i]=make([]float64,n)}
 ya,yb:=make([]float64,n),make([]float64,n)
 m:=ConditionedModel{SourceRig:src,MinUpper:math.Inf(1),MinLower:math.Inf(1),MaxUpper:math.Inf(-1),MaxLower:math.Inf(-1)}
 for _,r:=range targetRigs{
  if e:=r.Check();e!=nil{return ConditionedModel{},e}
  m.MinUpper=math.Min(m.MinUpper,r.Upper);m.MaxUpper=math.Max(m.MaxUpper,r.Upper)
  m.MinLower=math.Min(m.MinLower,r.Lower);m.MaxLower=math.Max(m.MaxLower,r.Lower)
  for _,p:=range sourcePoses {
   v,e:=FK(src,p);if e!=nil{return ConditionedModel{},e}
   target,e:=IK(r,v);if e!=nil{return ConditionedModel{},e}
   x:=rigFeatures(p,r)
   for i:=range x{
    ya[i]+=x[i]*(target.Hip-p.Hip)
    yb[i]+=x[i]*(target.Knee-p.Knee)
    for j:=range x{xtx[i][j]+=x[i]*x[j]}
   }
  }
 }
 for i:=range xtx{xtx[i][i]+=1e-7}
 a,e:=solve(xtx,ya);if e!=nil{return ConditionedModel{},e}
 b,e:=solve(xtx,yb);if e!=nil{return ConditionedModel{},e}
 m.HipWeights,m.KneeWeights=a,b
 return m,nil
}
func (m ConditionedModel) Predict(p Pose,target Rig)(Pose,error){
 if e:=target.Check();e!=nil{return Pose{},e}
 if target.Upper<m.MinUpper-1e-12||target.Upper>m.MaxUpper+1e-12||target.Lower<m.MinLower-1e-12||target.Lower>m.MaxLower+1e-12{return Pose{},errors.New("target geometry outside trained envelope")}
 if math.IsNaN(p.Hip)||math.IsInf(p.Hip,0)||math.IsNaN(p.Knee)||math.IsInf(p.Knee,0){return Pose{},errors.New("invalid source pose")}
 x:=rigFeatures(p,target);if len(x)!=len(m.HipWeights)||len(x)!=len(m.KneeWeights){return Pose{},errors.New("bad checkpoint")}
 out:=p;for i:=range x{out.Hip+=x[i]*m.HipWeights[i];out.Knee+=x[i]*m.KneeWeights[i]}
 if math.IsNaN(out.Hip)||math.IsInf(out.Hip,0)||math.IsNaN(out.Knee)||math.IsInf(out.Knee,0){return Pose{},errors.New("nonfinite prediction")}
 return out,nil
}
