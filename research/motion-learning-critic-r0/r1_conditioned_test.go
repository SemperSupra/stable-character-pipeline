package motion

import ("math";"testing")

func conditionedFixture(t *testing.T)(Rig,ConditionedModel,[]Sample,Regression){
 t.Helper()
 src:=Rig{Upper:.48,Lower:.46}
 baseTarget:=Rig{Upper:.53,Lower:.47}
 training,e:=Dataset(src,baseTarget,16,40);if e!=nil{t.Fatal(e)}
 poses:=make([]Pose,len(training));for i,s:=range training{poses[i]=s.Source}
 targets:=[]Rig{}
 for i:=0;i<6;i++ {for j:=0;j<5;j++ {
  targets=append(targets,Rig{Upper:.51+.18*float64(i)/5,Lower:.46+.14*float64(j)/4})
 }}
 model,e:=TrainConditioned(src,targets,poses);if e!=nil{t.Fatal(e)}
 old,e:=Train(training,2);if e!=nil{t.Fatal(e)}
 return src,model,training,old
}

func TestR1ConditionedGeneralizesUnseenTargetGeometry(t *testing.T){
 src,model,training,old:=conditionedFixture(t)
 for _,target:=range []Rig{{Upper:.63,Lower:.56},{Upper:.58,Lower:.53}}{
  all,e:=Dataset(src,target,21,40);if e!=nil{t.Fatal(e)}
  holdout:=all[len(training):]
  learned,e:=Evaluate(holdout,target,func(p Pose)(Pose,error){return model.Predict(p,target)});if e!=nil{t.Fatal(e)}
  unconditioned,e:=Evaluate(holdout,target,old.Predict);if e!=nil{t.Fatal(e)}
  exact,e:=Evaluate(holdout,target,func(p Pose)(Pose,error){v,e:=FK(src,p);if e!=nil{return Pose{},e};return IK(target,v)});if e!=nil{t.Fatal(e)}
  t.Logf("heldout=200 target=(%.3f,%.3f) no-rig=%0.9fm conditioned=%0.9fm analytic=%0.9fm",target.Upper,target.Lower,unconditioned.MeanFootErrorM,learned.MeanFootErrorM,exact.MeanFootErrorM)
  if len(holdout)!=200||learned.MeanFootErrorM>.005||learned.MeanFootErrorM>=.1*unconditioned.MeanFootErrorM{t.Fatal("conditioned learner failed bounded heldout improvement",learned,unconditioned)}
  if exact.MaxFootErrorM>1e-9{t.Fatal("analytic IK is not exact",exact)}
 }
}
func TestR1ConditionedRejectsUnsupportedTargets(t *testing.T){
 _,model,_,_:=conditionedFixture(t)
 pose:=Pose{Hip:.1,Knee:.8}
 for _,r:=range []Rig{{Upper:.75,Lower:.5},{Upper:.6,Lower:.8},{Upper:-1,Lower:.5},{Upper:math.NaN(),Lower:.5}}{
  if _,e:=model.Predict(pose,r);e==nil{t.Fatal("unsupported geometry passed",r)}
 }
 if _,e:=model.Predict(Pose{Hip:math.NaN(),Knee:0},Rig{Upper:.63,Lower:.56});e==nil{t.Fatal("nonfinite pose passed")}
}
