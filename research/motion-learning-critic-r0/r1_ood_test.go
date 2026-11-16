package motion

import (
  "math"
  "testing"
)

// The R0 learner is not conditioned on target rig geometry. These tests prevent
// in-distribution progress from being mistaken for unseen-target compatibility.
func TestR1UnseenTargetRigFailure(t *testing.T) {
  src := Rig{Upper: 0.48, Lower: 0.46}
  trainedTarget := Rig{Upper: 0.53, Lower: 0.47}
  unseenTarget := Rig{Upper: 0.63, Lower: 0.56}
  train, err := Dataset(src, trainedTarget, 16, 40)
  if err != nil { t.Fatal(err) }
  full, err := Dataset(src, unseenTarget, 21, 40)
  if err != nil { t.Fatal(err) }
  holdout := full[16*40:]
  learned, err := Train(train, 2)
  if err != nil { t.Fatal(err) }
  prediction, err := Evaluate(holdout, unseenTarget, learned.Predict)
  if err != nil { t.Fatal(err) }
  oracle, err := Evaluate(holdout, unseenTarget, func(p Pose) (Pose,error) {
    x,e := FK(src,p); if e != nil { return Pose{},e }
    return IK(unseenTarget,x)
  })
  if err != nil { t.Fatal(err) }
  t.Logf("heldout=200 unseen_target mean learned=%0.9fm vs analytic=%0.9fm", prediction.MeanFootErrorM,oracle.MeanFootErrorM)
  if prediction.MeanFootErrorM < 0.01 { t.Fatal("unconditioned model spuriously passed unseen target rig") }
  if oracle.MaxFootErrorM > 1e-9 { t.Fatal("analytical rig-conditioned solver not exact", oracle) }
  finding:=Finding{Status:"OBSERVED",Kind:"looks_correct",ModelID:"simulated-critic-only",Confidence:1,StartFrame:0,EndFrame:39}
  if got:=Adjudicate(prediction,0.005,finding); got!="HARD_GEOMETRY_FAIL" {t.Fatalf("visual claim overrode measurement: %q",got)}
}
func TestR1NoTrainTestFamilyOverlap(t *testing.T){
  src:=Rig{Upper:0.48,Lower:0.46}; dst:=Rig{Upper:0.53,Lower:0.47}
  training,e:=Dataset(src,dst,16,40);if e!=nil {t.Fatal(e)}
  all,e:=Dataset(src,dst,21,40);if e!=nil {t.Fatal(e)}
  holdout:=all[len(training):]
  if len(training)!=640||len(holdout)!=200 {t.Fatal("count",len(training),len(holdout))}
  trainFamilies:=map[int]bool{};testFamilies:=map[int]bool{}
  for _,s:=range training{trainFamilies[s.Family]=true}
  for _,s:=range holdout{testFamilies[s.Family]=true;if trainFamilies[s.Family]{t.Fatal("family leak",s.Family)}}
  if len(trainFamilies)!=16||len(testFamilies)!=5 {t.Fatalf("family split unexpected: %d %d",len(trainFamilies),len(testFamilies))}
  // Same analytic generator with phase shifts is not independent performer or morphology data.
}
func TestR1TargetRigInvalidAndSourcePreserved(t *testing.T){
 src:=Rig{Upper:.48,Lower:.46}
 p:=Pose{Hip:.1,Knee:.8}
 before,e:=FK(src,p);if e!=nil{t.Fatal(e)}
 for _,r:=range []Rig{{Upper:0,Lower:.5},{Upper:math.Inf(1),Lower:.5},{Upper:.5,Lower:math.NaN()}} {
   if _,e:=IK(r,before);e==nil{t.Fatal("invalid destination rig accepted",r)}
 }
 after,e:=FK(src,p);if e!=nil{t.Fatal(e)}
 if before!=after {t.Fatal("source pose mutated")}
}
