package synthetic
import (
 "math"
 "testing"
)
func makeSyntheticKeys(fps int)[]Key{
 keys:=make([]Key,fps+1)
 for i:=range keys{
  a:=float64(i)/float64(fps)
  keys[i]=Key{i,Vec{X:float64(i)},[]Quat{ZRotation(math.Pi*a)}}
 }
 return keys
}
func TestTimeExact60To30And120To30(t *testing.T){
 for _,fps:=range []int{60,120}{
  keys:=makeSyntheticKeys(fps)
  out,err:=ResampleSourceClock(keys,fps,30);if err!=nil{t.Fatal(err)}
  if len(out)!=31||out[0].Frame!=0||out[30].Frame!=30{t.Fatalf("bad target timeline %d %+v",len(out),out[0])}
  if !almost(out[15].Root.X,float64(fps)/2)||!almost(out[30].Root.X,float64(fps)){t.Fatalf("clock drift at %dHz",fps)}
  got:=out[30].Local[0].rotate(Vec{X:1})
  if !almost(got.X,-1)||!almost(got.Y,0){t.Fatalf("wrong final orientation %+v",got)}
 }
}
func TestTimeQuaternionHemisphere(t *testing.T){
 keys:=makeSyntheticKeys(60)
 for i:=range keys{if i%2==1{
  q:=keys[i].Local[0];keys[i].Local[0]=Quat{-q.W,-q.X,-q.Y,-q.Z}
 }}
 out,err:=ResampleSourceClock(keys,60,30);if err!=nil{t.Fatal(err)}
 mid:=out[15].Local[0].rotate(Vec{X:1})
 if math.Abs(mid.X)>1e-9||!almost(mid.Y,1){t.Fatalf("quaternion sign flip caused drift: %+v",mid)}
}
func TestTimeRedControls(t *testing.T){
 base:=makeSyntheticKeys(60)
 cases:=[]struct{name string;mutate func([]Key);source,target int}{
  {"wrong_fps",func([]Key){},0,30},
  {"wrong_origin",func(k []Key){k[0].Frame=1},60,30},
  {"duplicate_frame",func(k []Key){k[7].Frame=6},60,30},
  {"missing_frame",func(k []Key){k[7].Frame=8},60,30},
  {"nonunit_rotation",func(k []Key){k[8].Local[0].W=2},60,30},
  {"missing_rotation",func(k []Key){k[8].Local=nil},60,30},
  {"nan_position",func(k []Key){k[8].Root.X=math.NaN()},60,30},
  {"silent_end_truncation",func(k []Key){k[60].Frame=60},60,29},
 }
 for _,tc:=range cases {t.Run(tc.name,func(t *testing.T){
  k:=make([]Key,len(base))
  for i,x:=range base{k[i]=Key{x.Frame,x.Root,append([]Quat(nil),x.Local...)}}
  tc.mutate(k)
  if _,err:=ResampleSourceClock(k,tc.source,tc.target);err==nil{t.Fatal("invalid clock/motion accepted")}
 })}
}
