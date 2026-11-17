package main
import(
 "os"
 "path/filepath"
 "strings"
 "testing"
)
func witness(lane string)(string,string,string,R070,R072){
 sha:=strings.Repeat("a",40);first:=strings.Repeat("b",64);second:=strings.Repeat("c",64)
 exp,err:=catalog(lane);if err!=nil{panic(err)}
 a:=R070{Schema:"scp.r070.similarity-camera.v1",SourceSHA:sha,Frame1SHA:first,Frame2SHA:second,Direction:exp.Truth,Status:"PASS_NARROW_SOURCE_ONLY"}
 b:=R072{Schema:"scp.r072.pinhole-parallax-counterexample.v1",SourceSHA:sha,FirstSHA:first,SecondSHA:second,Lane:lane,
  SourceTruth:exp.Truth,ObservedDirection:exp.Truth,ObservedStatus:"PASS_NARROW_SOURCE_ONLY",
  Status:"SAFE_COPLANAR_CONTROL",WorldDeltaX:exp.WorldDelta,SubjectDepth:exp.ZRed,ReferenceDepth:exp.ZGreen}
 switch exp.Class{
 case "PARALLAX":
  a.Direction="LEFT";if lane=="parallax-far-still"{a.Direction="RIGHT"}
  b.ObservedDirection=a.Direction;b.Status="CONFIRMED_UNSAFE_2D_PARALLAX_FALSE_MOTION"
 case "NONCOPLANAR_REFERENCE","PROJECTIVE_CAMERA","MISSING_SUBJECT":
  a.Direction="UNKNOWN";a.Status="UNKNOWN"
  b.ObservedDirection="UNKNOWN";b.ObservedStatus="UNKNOWN";b.Status="REJECTED_OUT_OF_DOMAIN"
 }
 return sha,first,second,a,b
}
func TestR073ExpectedFixtureAdmissionAndRejection(t *testing.T){
 cases:=[]struct{lane,want string}{
  {"coplanar-pan","ADMIT_SYNTHETIC_COPLANAR_ONLY"},
  {"coplanar-world-right","ADMIT_SYNTHETIC_COPLANAR_ONLY"},
  {"coplanar-world-left","ADMIT_SYNTHETIC_COPLANAR_ONLY"},
  {"parallax-near-still","HOLD_PARALLAX"},
  {"parallax-far-still","HOLD_PARALLAX"},
  {"mixed-reference-depths","HOLD_REFERENCE_DEPTH"},
  {"lost-red","HOLD_MISSING_SUBJECT"},
  {"yaw-projective","HOLD_PROJECTIVE_CAMERA"},
 }
 for _,tc:=range cases{
  t.Run(tc.lane,func(t *testing.T){
   sha,a,b,ob,world:=witness(tc.lane)
   r:=decide(tc.lane,sha,a,b,ob,world)
   if r.Decision!=tc.want{t.Fatalf("want %s got %+v",tc.want,r)}
  })
 }
}
func TestR073MaliciousProvenanceAndRightsSpoofRejection(t *testing.T){
 sha,a,b,ob,world:=witness("coplanar-pan")
 attacks:=[]struct{name string;change func(*R070,*R072)}{
  {"wrong-source",func(x *R070,_ *R072){x.SourceSHA=strings.Repeat("0",40)}},
  {"wrong-world-source",func(_ *R070,y *R072){y.SourceSHA=strings.Repeat("0",40)}},
  {"wrong-frame-070",func(x *R070,_ *R072){x.Frame1SHA=strings.Repeat("0",64)}},
  {"wrong-frame-072",func(_ *R070,y *R072){y.SecondSHA=strings.Repeat("0",64)}},
  {"fabricated-world-motion",func(_ *R070,y *R072){y.WorldDeltaX=999}},
  {"fabricated-depth",func(_ *R070,y *R072){y.SubjectDepth=2}},
  {"fabricated-source-truth",func(_ *R070,y *R072){y.SourceTruth="LEFT"}},
  {"fabricated-r070-label",func(x *R070,_ *R072){x.Direction="RIGHT"}},
  {"fabricated-r072-observed-label",func(_ *R070,y *R072){y.ObservedDirection="RIGHT"}},
  {"r072-failure-disguised-pass",func(_ *R070,y *R072){y.Status="CONFIRMED_UNSAFE_2D_PARALLAX_FALSE_MOTION"}},
 }
 for _,tc:=range attacks{
  t.Run(tc.name,func(t *testing.T){
   x,y:=ob,world;tc.change(&x,&y)
   r:=decide("coplanar-pan",sha,a,b,x,y)
   if r.Decision!="HOLD_UNVERIFIED_EVIDENCE"{t.Fatalf("tamper admitted: %+v",r)}
  })
 }
 if decide("fake-lane",sha,a,b,ob,world).Decision!="HOLD_UNVERIFIED_EVIDENCE"{t.Fatal("unlisted lane admitted")}
}
func TestR073StrictNestedReceiptGrammar(t *testing.T){
 cases:=[]string{
  "{\"Schema\":\"scp.r070.similarity-camera.v1\",\"Schema\":\"attacker\"}",
  "{\"Schema\":\"scp.r070.similarity-camera.v1\",\"unknown\":\"x\"}",
  "{\"Schema\":\"scp.r070.similarity-camera.v1\"} {}",
  "",
  strings.Repeat("X",8193),
 }
 for i,raw:=range cases{
  p:=filepath.Join(t.TempDir(),"receipt.json")
  if err:=os.WriteFile(p,[]byte(raw),0600);err!=nil{t.Fatal(err)}
  var obj R070
  if err:=readBounded(p,&obj);err==nil{t.Fatalf("invalid receipt %d accepted",i)}
 }
}
