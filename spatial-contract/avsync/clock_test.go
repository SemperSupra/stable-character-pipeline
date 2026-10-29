package avsync
import("math";"strings";"testing")
func TestRatesAndRationalPTS(t *testing.T){
 for _,c:=range []struct{r Rate;frames int64;audio int64}{
  {Rate{24,1},240,480000},{Rate{25,1},250,480000},
  {Rate{30,1},300,480000},{Rate{60,1},600,480000},
  {Rate{24000,1001},240,480480},{Rate{30000,1001},300,480480},
 }{
  pts,err:=FramePTS(c.frames,c.r);if err!=nil{t.Fatal(err)}
  got,err:=SampleNearest(c.frames,c.r);if err!=nil||got!=c.audio{t.Fatalf("rate=%+v frame=%d got %d wanted %d",c.r,c.frames,got,c.audio)}
  if pts.Numerator*c.r.Num!=c.frames*c.r.Den*pts.Denominator{t.Fatalf("not rational %+v",pts)}
 }
}
func TestNoAccumulationAndEventMapping(t *testing.T){
 r:=Rate{30000,1001}
 // 30000/1001 FPS corresponds to 1601.6 samples per frame.
 for _,frame:=range []int64{0,1,2,3,4,255,256,1023,1024,1025,299,300,18000}{
  lo,e1:=SampleFloor(frame,r);hi,e2:=SampleCeil(frame,r)
  if e1!=nil||e2!=nil||hi-lo>1{t.Fatalf("frame=%d %d..%d",frame,lo,hi)}
  nearest,e3:=SampleNearest(frame,r)
  if e3!=nil||nearest<lo||nearest>hi{t.Fatalf("frame=%d bad round %d",frame,nearest)}
  containing,e4:=FrameContainingSample(lo,r)
  if e4!=nil||math.Abs(float64(containing-frame))>1{t.Fatalf("frame %d located %d",frame,containing)}
 }
 last:=int64(0)
 for f:=int64(1);f<=18000;f++{
  next,e:=SampleNearest(f,r)
  if e!=nil||next<=last{t.Fatalf("drift f=%d next=%d",f,next)}
  last=next
 }
 if last!=28828800{t.Fatalf("ten minute exact endpoint %d",last)}
}
func TestSampleAccurateMillisecondBridge(t *testing.T){
 for _,ms:=range []int64{0,1,3,255,256,999,1000}{
  s,e:=MillisecondsToSamples(ms)
  if e!=nil||s!=ms*48{t.Fatal(ms,s,e)}
 }
}
func fixture() Manifest {
 return Manifest{Schema:"spatial_audio.avsync.v1",Clock:"PTS_ZERO_COMMON_TIMELINE",
  AudioSampleHz:AudioHz,VideoRate:Rate{30000,1001},AudioSamples:480480,
  VideoFrames:300,Rights:"ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC",
  LatencySamples:255,TailSamples:1024,
  Events:[]Event{{ID:"foot_contact_a",SourceID:"emitter_a",
   Kind:FootContact,AtSample:96000,SourceSHA256:strings.Repeat("a",64)}}}
}
func TestEventAndLatencyInvariants(t *testing.T){
 m:=fixture()
 one,e:=m.Digest();if e!=nil{t.Fatal(e)}
 two,e:=m.Digest();if e!=nil||one!=two{t.Fatal("unstable manifest")}
 trim,e:=m.RequiredTrim();if e!=nil||trim!=255{t.Fatal("missing explicit trim")}
 tests:=[]func(*Manifest){
  func(m *Manifest){m.VideoRate.Den=0},func(m *Manifest){m.AudioSamples-=4},
  func(m *Manifest){m.AudioSampleHz=44100},func(m *Manifest){m.LatencySamples=-1},
  func(m *Manifest){m.Rights="PRIVATE"},func(m *Manifest){m.Events[0].AtSample=-1},
  func(m *Manifest){m.Events[0].SourceSHA256="broken"},
  func(m *Manifest){m.Events[0].Kind="unknown"},
 }
 for i,mutate:=range tests{
  c:=fixture();mutate(&c)
  if c.Validate()==nil{t.Fatalf("negative gate accepted %d",i)}
 }
 m.Events=append(m.Events,m.Events[0])
 if m.Validate()==nil{t.Fatal("duplicate event id")}
}
func TestRateAndTimingNegatives(t *testing.T){
 for _,r:=range []Rate{{0,1},{30,0},{30000,-1001},{999999,1},{1,1001}}{
  if r.Validate()==nil{t.Fatalf("invalid rate accepted %+v",r)}
 }
 if _,e:=FramePTS(-1,Rate{24,1});e==nil{t.Fatal("negative frame")}
 if _,e:=SampleNearest(240*60*60*10+1,Rate{24,1});e==nil{t.Fatal("overflow frame bound")}
 if _,e:=MillisecondsToSamples(-1);e==nil{t.Fatal("negative ms")}
 if _,e:=SamplePTS(MaxDurationSamples+1);e==nil{t.Fatal("too long")}
}
