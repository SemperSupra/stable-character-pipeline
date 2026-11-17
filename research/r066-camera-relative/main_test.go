package main
import (
 "path/filepath"
 "strings"
 "testing"
)
func TestCameraRelativeControls(t *testing.T){
 for _,tc:=range []struct{lane,want string;delta float64}{
  {"camera-pan-only","STILL",0},
  {"right-with-opposite-pan","RIGHT",55},
  {"left-with-opposite-pan","LEFT",-55},
 }{
  t.Run(tc.lane,func(t *testing.T){
   dir:=t.TempDir();if err:=generate(tc.lane,dir);err!=nil{t.Fatal(err)}
   a,err:=decode(filepath.Join(dir,"frame_001.png"));if err!=nil{t.Fatal(err)}
   b,err:=decode(filepath.Join(dir,"frame_002.png"));if err!=nil{t.Fatal(err)}
   decision,_,_,dx,err:=evaluate(a,b)
   if err!=nil||decision!=tc.want||dx!=tc.delta{t.Fatalf("want %s %g got %s %g, %v",tc.want,tc.delta,decision,dx,err)}
  })
 }
}
func TestFailClosedOnLostEvidence(t *testing.T){
 for _,tc:=range []struct{lane,firstFail string}{
  {"missing-fiducial","NO_GREEN_FIDUCIAL"},
  {"missing-subject","NO_RED_SUBJECT"},
 }{
  t.Run(tc.lane,func(t *testing.T){
   dir:=t.TempDir();if err:=generate(tc.lane,dir);err!=nil{t.Fatal(err)}
   _,err:=decode(filepath.Join(dir,"frame_002.png"))
   if err==nil||!strings.Contains(err.Error(),tc.firstFail){t.Fatalf("bad abstention: %v",err)}
  })
 }
}
func TestRejectAreaAndMismatchedGeometry(t *testing.T){
 good:=Scene{Red:ColorCenter{90,1600},Green:ColorCenter{105,576},Width:224,Height:224}
 other:=good;other.Green.Pixels=100
 if _,_,_,_,err:=evaluate(good,other);err==nil{t.Fatal("small reference accepted")}
 other=good;other.Width++
 if _,_,_,_,err:=evaluate(good,other);err==nil{t.Fatal("mismatched dimensions accepted")}
 other=good;other.Red.Pixels=350
 if _,_,_,_,err:=evaluate(good,other);err==nil{t.Fatal("area drift accepted")}
}
