package main
import(
 "math"
 "path/filepath"
 "testing"
)
func TestR072PinholeParallaxAnalyticWitness(t *testing.T){
 for _,x:=range []struct{lane string;expectedDX float64}{
  {"coplanar-pan",-18},
  {"parallax-near-still",-36},
  {"parallax-far-still",-9},
 }{
  t.Run(x.lane,func(t *testing.T){
   s,err:=sourceScene(x.lane);if err!=nil{t.Fatal(err)}
   x1,_,err:=projected(s.Red,s.First);if err!=nil{t.Fatal(err)}
   x2,_,err:=projected(s.Red,s.Second);if err!=nil{t.Fatal(err)}
   if math.Abs((x2-x1)-x.expectedDX)>1e-8{t.Fatalf("pinhole expected %g got %g",x.expectedDX,x2-x1)}
   if s.RedMotionX!=0{t.Fatal("camera parallax cannot mutate world subject")}
  })
 }
}
func TestR072OwnWorldMotionIndependentOfCamera(t *testing.T){
 for _,x:=range []struct{lane string;delta float64}{
  {"coplanar-world-right",0.6},
  {"coplanar-world-left",-0.6},
 }{
  t.Run(x.lane,func(t *testing.T){
   s,err:=sourceScene(x.lane);if err!=nil{t.Fatal(err)}
   if s.RedMotionX!=x.delta{t.Fatal("world motion lost")}
  })
 }
}
func TestR072IndependentUnsafeAndAbstentionAdjudication(t *testing.T){
 for _,tc:=range []struct{lane,status,direction,outcome string}{
  {"coplanar-pan","PASS_NARROW_SOURCE_ONLY","STILL","SAFE_COPLANAR_CONTROL"},
  {"coplanar-world-right","PASS_NARROW_SOURCE_ONLY","RIGHT","SAFE_COPLANAR_CONTROL"},
  {"coplanar-world-left","PASS_NARROW_SOURCE_ONLY","LEFT","SAFE_COPLANAR_CONTROL"},
  {"parallax-near-still","PASS_NARROW_SOURCE_ONLY","LEFT","CONFIRMED_UNSAFE_2D_PARALLAX_FALSE_MOTION"},
  {"parallax-far-still","PASS_NARROW_SOURCE_ONLY","RIGHT","CONFIRMED_UNSAFE_2D_PARALLAX_FALSE_MOTION"},
  {"mixed-reference-depths","UNKNOWN","UNKNOWN","REJECTED_OUT_OF_DOMAIN"},
  {"lost-red","UNKNOWN","UNKNOWN","REJECTED_OUT_OF_DOMAIN"},
  {"yaw-projective","UNKNOWN","UNKNOWN","REJECTED_OUT_OF_DOMAIN"},
 }{
  t.Run(tc.lane,func(t *testing.T){
   o:=Observed{Status:tc.status,Direction:tc.direction,Reason:"EXPECTED_SYNTHETIC_REFUSAL"}
   r,err:=audit(tc.lane,o)
   if err!=nil||r.Status!=tc.outcome{t.Fatalf("expected %s got %+v err=%v",tc.outcome,r,err)}
  })
 }
}
func TestR072MissingControlsCannotBeDeclaredSafe(t *testing.T){
 for _,lane:=range []string{"parallax-near-still","parallax-far-still","coplanar-pan","mixed-reference-depths"}{
  r,err:=audit(lane,Observed{Status:"PASS_NARROW_SOURCE_ONLY",Direction:"STILL"})
  if lane=="coplanar-pan"{if err!=nil{t.Fatal(err)};continue}
  if err==nil||r.Status!="FAIL_CONTROL"{t.Fatalf("%s erroneously accepted: %+v",lane,r)}
 }
}
func TestR072OriginalFrameProducer(t *testing.T){
 for _,lane:=range []string{"coplanar-pan","parallax-near-still","mixed-reference-depths","yaw-projective","lost-red"}{
  t.Run(lane,func(t *testing.T){
   dir:=t.TempDir()
   if err:=generate(lane,dir);err!=nil{t.Fatal(err)}
   a,b:=sha(filepath.Join(dir,"frame_001.png")),sha(filepath.Join(dir,"frame_002.png"))
   if a==""||b==""||a==b{t.Fatalf("missing/identical actual fixture sha %s %s",a,b)}
  })
 }
}
