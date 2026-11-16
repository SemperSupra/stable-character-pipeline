package regionalwarp
import(
 "math"
 "strings"
 "testing"
 "example.org/scp/anatomy-bakeoff/landmarks"
)
const h="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
func testPack()(landmarks.Pack,[]landmarks.Pair){
 locations:=[]struct{id string;x,y,z float64}{
 {"clavicle_left",.2,0,1.5},{"clavicle_right",-.2,0,1.5},
 {"iliac_crest_left",.15,0,1.0},{"iliac_crest_right",-.15,0,1.0},
 {"sternal_notch",0,-.1,1.5},{"spinous_t7",0,.1,1.4},
 {"head_top",0,0,1.85},{"sacrum",0,.02,.8},
 }
 tx:=[4][4]float64{{1,0,0,0},{0,1,0,0},{0,0,1,0},{0,0,0,1}}
 pairs:=[]landmarks.Pair{}
 deform:=func(p P)P{return add(p,P{X:.008+0.002*(p.Z-1.2),Y:.002*(p.X),Z:.001*(p.Z-1)})}
 for _,v:=range locations{
  p:=P{X:v.x,Y:v.y,Z:v.z}
  pairs=append(pairs,landmarks.Pair{ID:v.id,Source:p,Target:deform(p),
   SourceUncertaintyM:.003,TargetUncertaintyM:.004,
   SourceEvidence:h,TargetEvidence:h})
 }
 extra:=[]landmarks.Pair{}
 for i,p:=range []P{{.07,-.03,1.35},{-.09,.04,1.13}}{
  extra=append(extra,landmarks.Pair{ID:"independent-holdout-"+string(rune('0'+i)),
   Source:p,Target:deform(p),SourceUncertaintyM:.003,TargetUncertaintyM:.004,SourceEvidence:h,TargetEvidence:h})
 }
 return landmarks.Pack{Schema:landmarks.Schema,SourceAtlas:"SYNTHETIC_SOURCE_ONLY",
  TargetCharacter:"SYNTHETIC_TARGET_ONLY",SourceSHA256:h,TargetSHA256:h,
  SourceFrame:"synthetic-m",TargetFrame:"synthetic-m",Units:"m",
  Transform:tx,Pairs:pairs},extra
}
func TestSyntheticRegionalWarpHelpsHeldOutAndMaintainsJacobian(t *testing.T){
 source,heldout:=testPack()
 cand,out,err:=Fit(source,heldout,Default())
 if err!=nil{t.Fatal(err)}
 if out.Status!="MEASURED_SYNTHETIC_REGIONAL_FIT_ANATOMY_REVIEW_REQUIRED"{
  t.Fatalf("unexpected status %s: before %v after %v, training %v -> %v, Jacobian %v/%v",
   out.Status,out.BaselineHeldoutMeanM,out.FittedHeldoutMeanM,
   out.BaselineTrainingMeanM,out.FittedTrainingMeanM,out.MinJacobianRatio,out.MaxJacobianRatio)
 }
 if out.MinJacobianRatio<.5||out.MaxJacobianRatio>2||out.NumericalFoldDetected{t.Fatal("unbounded distortion")}
 for _,p:=range heldout{if err:=norm(sub(cand.ApplySource(p.Source),p.Target));err>.01{t.Fatal("heldout regression")}}
}
func TestMirrorSideSwapAndAbsenceFailClosed(t *testing.T){
 p,hld:=testPack()
 p.Transform[0][0]=-1
 if _,_,e:=Fit(p,hld,Default());e==nil{t.Fatal("reflection admitted")}
 p,hld=testPack()
 p.Pairs[0].Target,p.Pairs[1].Target=p.Pairs[1].Target,p.Pairs[0].Target
 if _,_,e:=Fit(p,hld,Default());e==nil{t.Fatal("swapped clavicles admitted")}
 p,hld=testPack()
 if _,_,e:=Fit(p,nil,Default());e==nil{t.Fatal("no independent heldout admitted")}
 p,hld=testPack()
 hld[0].ID=p.Pairs[0].ID
 if _,_,e:=Fit(p,hld,Default());e==nil{t.Fatal("heldout overlaps training accepted")}
}
func TestStrainBoundsAndInvalidInputs(t *testing.T){
 p,hld:=testPack()
 p.Pairs[0].Target.X+=.24
 if _,_,e:=Fit(p,hld,Default());e==nil{t.Fatal("unbounded deformation admitted")}
 p,hld=testPack()
 p.Pairs[0].SourceEvidence=""
 if _,_,e:=Fit(p,hld,Default());e==nil{t.Fatal("missing source proof admitted")}
 p,hld=testPack()
 opts:=Default();opts.RadiusM=math.NaN()
 if _,_,e:=Fit(p,hld,opts);e==nil{t.Fatal("NaN parameters admitted")}
 p,hld=testPack()
 for i:=range hld{hld[i].Target=transform(p.Transform,hld[i].Source)}
 _,out,e:=Fit(p,hld,Default())
 if e!=nil||!strings.HasPrefix(out.Status,"HOLD_"){t.Fatalf("misleading fit claim %+v %v",out,e)}
}
