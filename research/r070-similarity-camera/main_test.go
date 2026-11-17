package main
import (
 "path/filepath"
 "strings"
 "testing"
)
func TestR070StrictSimilarityOriginalFixtures(t *testing.T){
 cases:=[]struct{lane,want string}{
  {"translation-only","STILL"},
  {"zoom-only","STILL"},
  {"rotation-only","STILL"},
  {"right-under-zoom","RIGHT"},
  {"left-under-rotation","LEFT"},
 }
 for _,tc:=range cases{
  t.Run(tc.lane,func(t *testing.T){
   folder:=t.TempDir()
   if err:=generate(tc.lane,folder);err!=nil{t.Fatal(err)}
   a,err:=readFrame(filepath.Join(folder,"frame_001.png"));if err!=nil{t.Fatal(err)}
   b,err:=readFrame(filepath.Join(folder,"frame_002.png"));if err!=nil{t.Fatal(err)}
   decision,worldX,_,scale,theta,residual,err:=classify(a,b)
   if err!=nil||decision!=tc.want{t.Fatalf("want %s got %s dx=%g scale=%g rot=%g residual=%g error=%v",tc.want,decision,worldX,scale,theta,residual,err)}
   if residual>3.5{t.Fatalf("third anchor not independent witness: %f",residual)}
  })
 }
}
func TestR070FailClosedInvalidCameraGeometry(t *testing.T){
 cases:=[]struct{lane,why string}{
  {"corrupted-third-anchor","THIRD_ANCHOR_RESIDUAL"},
  {"mirror-reflection","SIMILARITY_OUT_OF_DOMAIN"},
  {"lost-third-anchor","MISSING_YELLOW"},
  {"lost-subject","MISSING_RED"},
 }
 for _,tc:=range cases{
  t.Run(tc.lane,func(t *testing.T){
   folder:=t.TempDir()
   if err:=generate(tc.lane,folder);err!=nil{t.Fatal(err)}
   a,err:=readFrame(filepath.Join(folder,"frame_001.png"));if err!=nil{t.Fatal(err)}
   b,err:=readFrame(filepath.Join(folder,"frame_002.png"));if err!=nil{t.Fatal(err)}
   d,_,_,_,_,_,err:=classify(a,b)
   if err==nil||!strings.Contains(err.Error(),tc.why)||d!="UNKNOWN"{t.Fatalf("expected fail-closed %s got %s err=%v",tc.why,d,err)}
  })
 }
}
func TestR070DimensionAndPhysicalBaselineRejections(t *testing.T){
 a:=Frame{Width:size,Height:size,Red:Point{X:165,Y:160,Count:500},Green:Point{X:65,Y:75,Count:400},Blue:Point{X:245,Y:75,Count:400},Yellow:Point{X:65,Y:245,Count:400}}
 b:=a;b.Width++
 if _,_,_,_,_,_,err:=classify(a,b);err==nil{t.Fatal("mismatched frame dimensions accepted")}
 b=a;b.Blue.X=a.Green.X+1
 if _,_,_,_,_,_,err:=classify(a,b);err==nil{t.Fatal("unsupported camera warp accepted")}
}
