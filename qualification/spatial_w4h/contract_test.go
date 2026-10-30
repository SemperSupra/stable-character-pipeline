package main
import("encoding/json";"math";"strings";"testing")
func TestAcceptedPresentation(t *testing.T){
 for _,fps:=range [][2]int64{{24,1},{30,1},{30000,1001}}{
  p:=sample();p.Clock.FPSNum=fps[0];p.Clock.FPSDen=fps[1]
  if err:=Validate(p);err!=nil{t.Fatalf("%v %v",fps,err)}
  for _,s:=range []int64{0,1,23999,24000,24001,95999}{
   got,err:=frameAt(p.Clock,s);want:=s*fps[0]/(rate*fps[1])
   if err!=nil||got!=want{t.Fatalf("fps %v sample %d got %d expected %d err %v",fps,s,got,want,err)}
  }
 }
}
func TestPoseSmoothingAndCuts(t *testing.T){
 p:=sample()
 for _,c:=range []struct{s int64;want float64}{{24000,0},{27000,.5},{30000,1},{33000,1},{36000,0},{40000,0}}{
  got,err:=PoseAt(p,"jaw",c.s);if err!=nil||math.Abs(got-c.want)>1e-12{t.Fatalf("sample %d got %g want %g err %v",c.s,got,c.want,err)}
 }
}
func TestHostileMutations(t *testing.T){
 base:=sample()
 negatives:=[]struct{name string;mutate func(*Packet)}{
 {"rights",func(p *Packet){p.Rights="UNCLEAR"}},
 {"sha",func(p *Packet){p.SourceSHA256="PRIVATE"}},
 {"hz",func(p *Packet){p.Clock.AudioHz=44100}},
 {"fps_zero",func(p *Packet){p.Clock.FPSNum=0}},
 {"fps_wrong",func(p *Packet){p.Clock.FPSNum=60}},
 {"duration_zero",func(p *Packet){p.Clock.DurationSamples=0}},
 {"duration_over",func(p *Packet){p.Clock.DurationSamples=rate*601}},
 {"cue_empty",func(p *Packet){p.Cues=nil}},
 {"duplicate_cue",func(p *Packet){p.Cues[1].ID=p.Cues[0].ID}},
 {"cue_untyped",func(p *Packet){p.Cues[0].Kind="mystery"}},
 {"cue_unknown_origin",func(p *Packet){p.Cues[0].Origin="AI_GUESS"}},
 {"inference_as_truth",func(p *Packet){p.Cues[0].Origin="inferred_unverified"}},
 {"negative_start",func(p *Packet){p.Cues[0].StartSample=-1}},
 {"zero_length",func(p *Packet){p.Cues[0].EndSample=p.Cues[0].StartSample}},
 {"over_end",func(p *Packet){p.Cues[0].EndSample=rate*3}},
 {"overlap_phoneme",func(p *Packet){p.Cues[2].StartSample=29999}},
 {"overlap_viseme",func(p *Packet){p.Cues[4].StartSample=29999}},
 {"missing_stream",func(p *Packet){p.Cues[0].Stream=""}},
 {"missing_value",func(p *Packet){p.Cues[0].Value=""}},
 {"nan_pose",func(p *Packet){p.Poses[0].Value=math.NaN()}},
 {"inf_pose",func(p *Packet){p.Poses[0].Value=math.Inf(1)}},
 {"pose_under",func(p *Packet){p.Poses[0].Value=-.01}},
 {"pose_over",func(p *Packet){p.Poses[0].Value=1.01}},
 {"pose_negative_sample",func(p *Packet){p.Poses[0].Sample=-1}},
 {"pose_duplicate_time",func(p *Packet){p.Poses[1].Sample=p.Poses[0].Sample}},
 {"pose_nonmonotonic",func(p *Packet){p.Poses[2].Sample=p.Poses[1].Sample-1}},
 }
 for _,n:=range negatives{t.Run(n.name,func(t *testing.T){
  p:=base;p.Cues=append([]Cue(nil),base.Cues...);p.Poses=append([]Pose(nil),base.Poses...)
  n.mutate(&p);if e:=Validate(p);e==nil{t.Fatal("HOSTILE_ACCEPTED")}
 })}
}
func TestStrictDecode(t *testing.T){
 p:=sample();raw,_:=json.Marshal(p);if _,err:=Decode(raw);err!=nil{t.Fatal(err)}
 for _,input:=range []string{string(raw)+"{}",strings.Replace(string(raw),`"schema":`,`"unknown":1,"schema":`,1),strings.Replace(string(raw),`"schema":`,`"schema":"bad","schema":`,1)}{
  if _,err:=Decode([]byte(input));err==nil{t.Fatal("MALFORMED_ACCEPTED")}
 }
}
func TestReceipt(t *testing.T){p:=sample();r,err:=MakeReceipt(p);if err!=nil{t.Fatal(err)};if r.CueCount!=9||r.MidPose!=.5||r.Frames["foot0"]!=14{t.Fatalf("receipt mismatch %+v",r)}}
