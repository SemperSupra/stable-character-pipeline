package main
import (
 "math"
 "testing"
)
func TestMapRootAndFourJointCoverage(t *testing.T){
 a,b,p,_:=fixture()
 m,_,_,err:=check(a,b,p)
 if err!=nil{t.Fatal(err)}
 if len(m)!=4||m["hip"]!="pivot"||m["knee"]!="hinge"{t.Fatal("source rig identity or mapping missing")}
 r,err:=execute("map")
 if err!=nil||r.Status!="PASS_SYNTHETIC_NAMED_RIG_CORRESPONDENCE"||r.LearnedModelInference||r.Metric3DRecovered{t.Fatalf("false rig admission %+v %v",r,err)}
}
func TestMapWrongRootAndAncestry(t *testing.T){
 a,b,p,_:=fixture()
 p[0].Target="tip"
 if _,_,_,err:=check(a,b,p);err==nil{t.Fatal("root mapping substitution accepted")}
 a,b,p,_=fixture()
 b.Joints[2].Parent="base" // wrong tree despite every mapped name
 if _,_,_,err:=check(a,b,p);err==nil{t.Fatal("incompatible ancestral chain accepted")}
}
func TestMapDuplicateAndUnmapped(t *testing.T){
 a,b,p,_:=fixture()
 p[2].Source="hip"
 if _,_,_,err:=check(a,b,p);err==nil{t.Fatal("duplicate source accepted")}
 a,b,p,_=fixture()
 p[2].Target="pivot"
 if _,_,_,err:=check(a,b,p);err==nil{t.Fatal("duplicate target accepted")}
 a,b,p,_=fixture()
 if _,_,_,err:=check(a,b,p[:3]);err==nil{t.Fatal("partial mapping accepted")}
}
func TestMapCycleAndZeroLength(t *testing.T){
 a,b,p,_:=fixture()
 a.Joints[1].Parent="ankle"
 if _,_,_,err:=check(a,b,p);err==nil{t.Fatal("cyclic source accepted")}
 a,b,p,_=fixture()
 b.Joints[2].Rest=[3]float64{}
 if _,_,_,err:=check(a,b,p);err==nil{t.Fatal("zero segment accepted")}
}
func TestMapFailClosedRightsAndUnits(t *testing.T){
 a,b,p,_:=fixture()
 a.SourceClass="EXTERNAL_REAL_PERSON"
 if _,_,_,err:=check(a,b,p);err==nil{t.Fatal("external unlicensed person source accepted")}
 a,b,p,_=fixture()
 b.SourceClass="UNKNOWN"
 if _,_,_,err:=check(a,b,p);err==nil{t.Fatal("unknown destination character provenance accepted")}
 a,b,p,_=fixture()
 b.Plane="METERS_METRIC_3D"
 if _,_,_,err:=check(a,b,p);err==nil{t.Fatal("unreviewed coordinate mapping accepted")}
}
func TestMotionScaleAndSourceTimes(t *testing.T){
 a,b,p,fs:=fixture()
 got,delta,err:=retarget(a,b,p,fs)
 if err!=nil{t.Fatal(err)}
 if len(got)!=3||got[1].SourceMS!=1000||got[2].SourceMS!=2000{t.Fatal("source time not retained")}
 if math.Abs(delta-.1)>1e-9||math.Abs(got[2].TargetLocal["hinge"][0]-.1)>1e-9{
  t.Fatalf("source and destination bone scaling invalid %+v %v",got,delta)
 }
 r,err:=execute("motion")
 if err!=nil||r.Status!="PASS_SYNTHETIC_LOCAL_TRANSLATION_SOURCE_CLOCK_ONLY"||r.FrameCount!=3||r.RealHumanOrAnimalContactMeasured||r.LearnedModelInference{
  t.Fatalf("motion accepted wrong claim %+v %v",r,err)
 }
}
func TestMotionMissingFrameCannotInterpolate(t *testing.T){
 a,b,p,fs:=fixture()
 fs[1].SourceMS=1500
 if _,_,err:=retarget(a,b,p,fs);err==nil{t.Fatal("time gap silently interpolated")}
 a,b,p,fs=fixture()
 if _,_,err:=retarget(a,b,p,fs[:2]);err==nil{t.Fatal("missing source time accepted")}
}
func TestMotionOcclusionAndPartialValues(t *testing.T){
 a,b,p,fs:=fixture()
 fs[1].Seen["knee"]=false
 if _,_,err:=retarget(a,b,p,fs);err==nil{t.Fatal("invisible joint silently substituted")}
 a,b,p,fs=fixture()
 delete(fs[1].Local,"knee")
 if _,_,err:=retarget(a,b,p,fs);err==nil{t.Fatal("missing local value accepted")}
 a,b,p,fs=fixture()
 fs[1].Local["knee"]=[3]float64{math.NaN(),1,0}
 if _,_,err:=retarget(a,b,p,fs);err==nil{t.Fatal("NaN pose accepted")}
}
func TestMotionNoInventedDepth(t *testing.T){
 a,b,p,fs:=fixture()
 fs[1].Local["knee"]=[3]float64{0,-.8,.1}
 if _,_,err:=retarget(a,b,p,fs);err==nil{t.Fatal("source depth measured without admission")}
}
func TestUnknownWorkcellDenied(t *testing.T){
 if _,err:=execute("cuda_private_inference");err==nil{t.Fatal("unadmitted private model workcell accepted")}
}
