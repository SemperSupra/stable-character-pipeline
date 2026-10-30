package main
import ("math";"testing")
func expectError(t *testing.T,x Trace){t.Helper();if _,e:=classify(x);e==nil{t.Fatal("hostile mutation accepted")}}
func TestOriginalContract(t *testing.T){
 toy,e:=classify(fixtures("toy"));if e!=nil{t.Fatal(e)}
 if toy.Status!="PASS_SYNTHETIC_CONTACT_EVENTS_ONLY"||len(toy.Events)!=2||toy.Events[0].Sample!=4000||toy.Events[1].Sample!=16000{t.Fatalf("wrong synthetic source clock or contact: %+v",toy)}
 n,e:=classify(fixtures("native"));if e!=nil||n.Status!="ABSTAIN"||n.Reason!="UNVERIFIED_ANATOMICAL_SOLE"||len(n.Events)!=0{t.Fatalf("unlabeled actual mesh invented foot: %+v %v",n,e)}
}
func TestHostileMutations(t *testing.T){
 mutations:=map[string]func(*Trace){
  "rights":func(x *Trace){x.Rights="GUESSED_UNVERIFIED"},
  "clock":func(x *Trace){x.AudioHz=44100},
  "fps":func(x *Trace){x.ClockFPS=24},
  "basis":func(x *Trace){x.Basis="Y_UP"},
  "schema":func(x *Trace){x.Schema="UNKNOWN"},
  "foot":func(x *Trace){x.FootID=""},
  "source":func(x *Trace){x.FootSource="UNKNOWN"},
  "early":func(x *Trace){x.Frames[1].Index=2},
  "nonfinite":func(x *Trace){x.Frames[1].Heel[2]=math.NaN()},
  "penetration":func(x *Trace){x.Frames[1].Heel[2]=-.01},
  "slide":func(x *Trace){x.Frames[2].Heel[0]=.5},
  "missing":func(x *Trace){x.Frames=x.Frames[:2]},
  "negativeclearance":func(x *Trace){x.NativeMinMeshGroundClearance=-1},
  "native_fakefoot":func(x *Trace){x.FootSource="NATIVE_UNLABELED_MESH"},
  "phonyclearance":func(x *Trace){x.NativeMinMeshGroundClearance=.27},
 }
 for name,mutate:=range mutations{t.Run(name,func(t *testing.T){x:=fixtures("toy");mutate(&x);expectError(t,x)})}
}
func TestAbstainNoTouch(t *testing.T){
 x:=fixtures("toy");for i:=range x.Frames{x.Frames[i].Heel[2]=.3;x.Frames[i].Toe[2]=.3}
 r,e:=classify(x);if e!=nil||r.Status!="ABSTAIN"||len(r.Events)!=0{t.Fatalf("hover cannot count as contact %+v %v",r,e)}
}
func TestUnknownNativeContactCannotBeInferred(t *testing.T){
 x:=fixtures("native");x.NativeMinMeshGroundClearance=0
 expectError(t,x)
}
