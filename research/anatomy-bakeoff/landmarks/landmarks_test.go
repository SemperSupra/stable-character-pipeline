package landmarks

import (
 "math"
 "strings"
 "testing"
)
const h="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
func fixture()Pack{
 src:=map[string]Point{
  "clavicle_left":{.18,0,1.48},"clavicle_right":{-.18,0,1.48},
  "iliac_crest_left":{.14,0,1.0},"iliac_crest_right":{-.14,0,1.0},
  "sternal_notch":{0,-.08,1.5},"spinous_t7":{0,.10,1.4},
  "head_top":{0,0,1.8},"sacrum":{0,.02,.88},
 }
 theta:=.13
 scale:=1.21
 tx:=[4][4]float64{
  {scale*math.Cos(theta),-scale*math.Sin(theta),0,.18},
  {scale*math.Sin(theta),scale*math.Cos(theta),0,-.24},
  {0,0,scale,.06},{0,0,0,1},
 }
 pairs:=[]Pair{}
 for _,id:=range required{
  p:=src[id]
  pairs=append(pairs,Pair{ID:id,Source:p,Target:apply(tx,p),
   SourceUncertaintyM:.003,TargetUncertaintyM:.004,
   SourceEvidence:h,TargetEvidence:h})
 }
 return Pack{Schema:Schema,SourceAtlas:"HRA_v1_2_male",SourceSHA256:h,
  TargetCharacter:"MPFB_approved_synthetic",TargetSHA256:h,
  SourceFrame:"HRA_samecohort_local",TargetFrame:"MPFB_world",
  Units:"m",Transform:tx,Pairs:pairs}
}
func TestKnownRigidTransformIsOnlyMechanical(t *testing.T){
 pack:=fixture()
 r,e:=Evaluate(pack)
 if e!=nil{t.Fatal(e)}
 if r.Status!="MECHANICAL_CORRESPONDENCE_ONLY_INDEPENDENT_ANATOMY_REVIEW_REQUIRED"||
 r.P95ResidualM>1e-9||!r.LateralityConsistency||!r.AnteriorPosteriorConsistency{t.Fatalf("%+v",r)}
 fp,e:=Fingerprint(pack);if e!=nil||len(fp)!=64{t.Fatal(fp,e)}
}
func TestMirroredAndSwappedLateralityRejected(t *testing.T){
 p:=fixture()
 p.Transform[0][0]*=-1;p.Transform[0][1]*=-1
 if _,e:=Evaluate(p);e==nil||!strings.Contains(e.Error(),"REFLECTION"){t.Fatal("mirror accepted",e)}
 p=fixture()
 i,j:=-1,-1
 for k,v:=range p.Pairs{if v.ID=="clavicle_left"{i=k};if v.ID=="clavicle_right"{j=k}}
 p.Pairs[i].Target,p.Pairs[j].Target=p.Pairs[j].Target,p.Pairs[i].Target
 if _,e:=Evaluate(p);e==nil||!strings.Contains(e.Error(),"LATERALITY"){t.Fatal("swapped left/right accepted",e)}
}
func TestRefuseSemanticOrSourceLaundering(t *testing.T){
 p:=fixture()
 p.SourceSHA256="not a hash"
 if _,e:=Evaluate(p);e==nil{t.Fatal("unknown atlas source admitted")}
 p=fixture();p.Pairs=p.Pairs[1:]
 r,e:=Evaluate(p)
 if e!=nil||r.Status!="HOLD_MISSING_OR_INVALID_FIDUCIALS"||len(r.Missing)!=1{t.Fatal(r,e)}
 p=fixture();p.Pairs[0].SourceEvidence=""
 if _,e:=Evaluate(p);e==nil{t.Fatal("unsubstantiated landmark admitted")}
}
func TestFiniteAndNonUniformTransformGuards(t *testing.T){
 p:=fixture()
 p.Transform[1][1]*=1.2
 if _,e:=Evaluate(p);e==nil{t.Fatal("nonuniform/shear transform allowed")}
 p=fixture();p.Transform[0][0]=math.NaN()
 if _,e:=Evaluate(p);e==nil{t.Fatal("nonfinite transform allowed")}
 p=fixture();p.Transform[3][1]=.2
 if _,e:=Evaluate(p);e==nil{t.Fatal("non-affine matrix allowed")}
}
func TestLargeResidualHoldsEvenWithPositiveTransform(t *testing.T){
 p:=fixture()
 for i:=range p.Pairs{p.Pairs[i].Target.X+=.04}
 r,e:=Evaluate(p)
 if e!=nil||r.Status!="HOLD_LANDMARK_GEOMETRY_RESIDUAL"{t.Fatal(r,e)}
}
func TestDuplicateAndDegenerateGroups(t *testing.T){
 p:=fixture()
 p.Pairs=append(p.Pairs,p.Pairs[0])
 if _,e:=Evaluate(p);e==nil{t.Fatal("duplicate source landmark accepted")}
 p=fixture()
 for i:=range p.Pairs{
  p.Pairs[i].Source.Z=0
  p.Pairs[i].Target.Z=0
 }
 if _,e:=Evaluate(p);e==nil{t.Fatal("coplanar fiducials admitted")}
}
