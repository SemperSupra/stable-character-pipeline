package main
import (
 "encoding/binary"
 "math"
 "strings"
 "testing"
)
func testFrames() []Frame {
 a:=make([]Frame,30)
 for i:=range a {
   a[i].Index=i
   a[i].SourceTimeMS=11000+i*1000
   if i>=2 && i<=11 || i>=13 && i<=23 {
     a[i].Landmarks=make([]Landmark,33)
     for j:=0;j<33;j++{
       a[i].Landmarks[j]=Landmark{X:float64(j%7)/12+.2+float64(i)*.001,
         Y:float64(j/7)/9+.12+float64(i)*.001, Z:0,Visibility:1}
     }
   }
 }
 return a
}
func TestSourceGate(t *testing.T){
 a:=testFrames()
 if err:=validate(a);err!=nil{t.Fatal(err)}
 s,n,err:=longestRun(a)
 if err!=nil||s!=13||n!=11{t.Fatalf("selected segment %d,%d err %v",s,n,err)}
 a[0].SourceTimeMS+=7
 if err:=validate(a);err==nil{t.Fatal("source clock accepted drift")}
}
func TestPartialAndNonFinite(t *testing.T){
 a:=testFrames();a[4].Landmarks=a[4].Landmarks[:21]
 if err:=validate(a);err==nil{t.Fatal("partial array accepted")}
 a=testFrames();a[4].Landmarks[2].X=math.NaN()
 if err:=validate(a);err==nil{t.Fatal("nonfinite coordinate accepted")}
 a=testFrames();a[4].Landmarks[2].Visibility=2
 if err:=validate(a);err==nil{t.Fatal("out-of-bounds visibility accepted")}
}
func TestMissingnessRefused(t *testing.T){
 a:=testFrames()
 for i:=range a {if i!=5 {a[i].Landmarks=nil}}
 if _,_,err:=longestRun(a);err==nil{t.Fatal("single-only valid pose accepted")}
}
func TestNativeGLBConformance(t *testing.T){
 glb,m,err:=createGLB(testFrames())
 if err!=nil{t.Fatal(err)}
 if binary.LittleEndian.Uint32(glb[:4])!=0x46546c67{t.Fatal("bad glTF magic")}
 if binary.LittleEndian.Uint32(glb[4:8])!=2{t.Fatal("wrong glTF version")}
 if int(binary.LittleEndian.Uint32(glb[8:12]))!=len(glb){t.Fatal("invalid byte length")}
 if m["glb_sample_count"]!=11{t.Fatalf("wrong continuous frame selection %v",m["glb_sample_count"])}
 if m["full_source_detected_frames"]!=21 {t.Fatal("source missingness lost")}
 jsonSize:=int(binary.LittleEndian.Uint32(glb[12:16]))
 if jsonSize<=0||jsonSize+20>len(glb){t.Fatal("invalid JSON chunk")}
 j:=string(glb[20:20+jsonSize])
 for _,token:=range []string{`"skins"`, `"JOINTS_0"`, `"WEIGHTS_0"`, `"animations"`, `"inverseBindMatrices"`}{
   if !strings.Contains(j,token){t.Errorf("missing glTF component %s",token)}
 }
}
func TestRightsAndChecksumGate(t *testing.T){
 if err:=verifyReceipt([]byte(`{"media":{"video":{"bytes":10680037,"sha1":"bogus"}},"model":{"sha256":"bogus"}}`));err==nil{
   t.Fatal("unsupported media accepted")
 }
}


func TestFramingQualityVsLongest(t *testing.T){
  a:=testFrames()
  for i:=13;i<=23;i++{
    for j:=range a[i].Landmarks{
      a[i].Landmarks[j].X=.5+(a[i].Landmarks[j].X-.5)*.12
      a[i].Landmarks[j].Y=.5+(a[i].Landmarks[j].Y-.5)*.12
    }
  }
  start,n,err:=selectRun(a,"coverage")
  if err!=nil||start!=2||n!=10{t.Fatalf("coverage chose %d len=%d err=%v",start,n,err)}
  start,n,err=selectRun(a,"longest")
  if err!=nil||start!=13||n!=11{t.Fatalf("longest baseline changed %d len=%d err=%v",start,n,err)}
  if _,_,err:=selectRun(a,"predicted_truth");err==nil{t.Fatal("unknown selector accepted")}
}
func TestVisibilityAndCroppingCoverage(t *testing.T){
  p:=make([]Landmark,33)
  for i:=range p{p[i]=Landmark{X:float64(i%10)/10,Y:float64(i/10)/10,Visibility:.2}}
  if sampleCoverage(p)!=0{t.Fatal("unobserved inferred joints treated as measured framing")}
  for i:=range p{p[i].Visibility=.95}
  if sampleCoverage(p)<=.1{t.Fatal("valid source image coverage not computed")}
}
