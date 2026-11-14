package observer

import (
 "bytes"
 "encoding/json"
 "math"
 "strings"
 "testing"
)

func digest(s string)string{return strings.Repeat(s,64)}
func valid()Receipt{
 score:=0.65
 return Receipt{Schema:Schema,Status:Status,Canonical:false,
  SourceClass:"public_synthetic",SourceAdmissionID:"synthetic-fixture-only",
  SourceMediaSHA256:digest("a"),MediaKind:"image",FrameCount:1,
  ViewID:"front-synthetic",CameraSHA256:digest("b"),Model:Model{ID:"synthetic-not-a-model",WeightsSHA256:digest("c"),Runtime:"none"},PromptSHA256:digest("d"),
  Observations:[]Observation{{ClaimKind:"pose",Support:"direct",Text:"Synthetic fixture marks a static neutral pose.",FrameIndices:[]int{0},FrameSHA256:[]string{digest("e")},Region:Region{Kind:"full_frame"},ModelReportedScore:&score}},
 }
}

func TestValidStructureNotAcceptance(t *testing.T){
 r:=valid()
 if err:=r.Validate();err!=nil{t.Fatal(err)}
 b,_:=json.Marshal(r)
 got,err:=DecodeAndValidate(bytes.NewReader(b))
 if err!=nil{t.Fatal(err)}
 if got.Status!=Status||got.Canonical||got.Model.ID!="synthetic-not-a-model"{t.Fatalf("false success %+v",got)}
}
func TestAdversarialReceiptFields(t *testing.T){
 cases:=map[string]func(*Receipt){
  "wrong_status":func(r *Receipt){r.Status="PASS"},
  "canonical":func(r *Receipt){r.Canonical=true},
  "unknown_source":func(r *Receipt){r.SourceClass="scraped"},
  "unbound_source":func(r *Receipt){r.SourceMediaSHA256="a"},
  "unbound_model":func(r *Receipt){r.Model.WeightsSHA256=""},
  "wrong_mmproj":func(r *Receipt){r.Model.MMProjSHA256="fake"},
  "bad_camera":func(r *Receipt){r.CameraSHA256="fake"},
  "bad_prompt":func(r *Receipt){r.PromptSHA256="fake"},
  "inverted_timebase":func(r *Receipt){r.Timebase=Timebase{Numerator:24,Denominator:1}},
  "multiple_image_frames":func(r *Receipt){r.FrameCount=2},
  "unbounded_score":func(r *Receipt){v:=math.Inf(1);r.Observations[0].ModelReportedScore=&v},
  "nan_score":func(r *Receipt){v:=math.NaN();r.Observations[0].ModelReportedScore=&v},
  "negative_score":func(r *Receipt){v:=-.1;r.Observations[0].ModelReportedScore=&v},
  "unknown_score":func(r *Receipt){r.Observations[0].Support="unknown"},
  "bad_frame_sha":func(r *Receipt){r.Observations[0].FrameSHA256[0]="fake"},
  "missing_frames":func(r *Receipt){r.Observations[0].FrameIndices=nil},
  "single_frame_motion":func(r *Receipt){r.Observations[0].ClaimKind="temporal_behavior"},
  "blank_text":func(r *Receipt){r.Observations[0].Text=""},
  "missing_region":func(r *Receipt){r.Observations[0].Region=Region{}},
  "unknown_claim":func(r *Receipt){r.Observations[0].ClaimKind="human_identity"},
 }
 for name,f:=range cases{t.Run(name,func(t *testing.T){r:=valid();f(&r);if err:=r.Validate();err==nil{t.Fatal("expected invalid receipt")}})}
}
func TestTemporalBehaviorRequiresGroundedFrames(t *testing.T){
 r:=valid();r.MediaKind="video";r.FrameCount=48;r.Timebase=Timebase{Numerator:24,Denominator:1}
 r.Observations[0].ClaimKind="temporal_behavior"
 r.Observations[0].FrameIndices=[]int{0,12};r.Observations[0].FrameSHA256=[]string{digest("e"),digest("f")}
 if err:=r.Validate();err!=nil{t.Fatal(err)}
 for _,bad:=range []string{"reverse","same","out_of_range","wrong_timebase"}{
  q:=r
  x:=q.Observations[0];x.FrameIndices=append([]int(nil),x.FrameIndices...);x.FrameSHA256=append([]string(nil),x.FrameSHA256...)
  switch bad{case "reverse":x.FrameIndices=[]int{12,0};case "same":x.FrameIndices=[]int{0,0};case "out_of_range":x.FrameIndices=[]int{0,48};case "wrong_timebase":q.Timebase.Denominator=0}
  q.Observations=[]Observation{x}
  if err:=q.Validate();err==nil{t.Fatalf("%s admitted",bad)}
 }
}
func TestBBoxAndUnknownAbstention(t *testing.T){
 r:=valid();r.Observations[0].Region=Region{Kind:"bbox",Box:&Box{X:0.1,Y:0.2,Width:.5,Height:.7}}
 if err:=r.Validate();err!=nil{t.Fatal(err)}
 r.Observations[0].Region.Box.Width=.95
 if err:=r.Validate();err==nil{t.Fatal("bbox outside frame admitted")}
 r=valid();r.Observations[0].Support="unknown";r.Observations[0].ModelReportedScore=nil
 if err:=r.Validate();err!=nil{t.Fatal(err)}
 r.Observations[0].ConceptHypotheses=[]string{"CPE.assumed"}
 if err:=r.Validate();err==nil{t.Fatal("unknown claim emitted concept hypothesis")}
}
func TestDecodeStrictAdversarial(t *testing.T){
 r:=valid();b,_:=json.Marshal(r)
 samples:=map[string]string{
  "duplicate_root":strings.Replace(string(b),`"status":`,`"status":"PASS","status":`,1),
  "duplicate_nested":strings.Replace(string(b),`"support":`,`"support":"inferred","support":`,1),
  "unknown_field":strings.Replace(string(b),`"canonical":false`,`"canonical":false,"accepted":true`,1),
  "nonfinite":strings.Replace(string(b),`"model_reported_score":0.65`,`"model_reported_score":NaN`,1),
  "float_overflow":strings.Replace(string(b),`"model_reported_score":0.65`,`"model_reported_score":1e999`,1),
  "trailing":string(b)+" {}",
  "oversized":string(b)+strings.Repeat(" ",MaxJSONBytes),
 }
 for name,s:=range samples{t.Run(name,func(t *testing.T){if _,err:=DecodeAndValidate(strings.NewReader(s));err==nil{t.Fatal("bad JSON accepted")}})}
}
