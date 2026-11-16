package temporal

import ("math";"testing")
func fixtures()([]Frame,[]Frame) {
 src:=make([]Frame,11);dst:=make([]Frame,11)
 for i:=range src {f:=Frame{Tick:int64(i),X:0.05*float64(i),Y:0.01*math.Sin(float64(i))};src[i]=f;dst[i]=f}
 return src,dst
}
func TestClockAndMotionMutants(t *testing.T){
 s,d:=fixtures()
 if r:=Audit(s,d);r.Status!="MATCHED_PROJECTED_2D_ONLY"||r.MaxPositionError!=0 {t.Fatal(r)}
 frozen:=append([]Frame{},d...);for i:=range frozen {frozen[i].X=0;frozen[i].Y=0}
 if r:=Audit(s,frozen);r.Status!="FROZEN_TARGET"{t.Fatal(r)}
 reversed:=append([]Frame{},d...);for i:=range reversed{reversed[i].X=-reversed[i].X}
 if r:=Audit(s,reversed);r.Status!="MOTION_MISMATCH"{t.Fatal(r)}
 missingClock:=append([]Frame{},d...);missingClock[4].Tick=missingClock[3].Tick
 if r:=Audit(s,missingClock);r.Status!="CLOCK_MISMATCH"{t.Fatal(r)}
 nonfinite:=append([]Frame{},d...);nonfinite[3].X=math.NaN()
 if r:=Audit(s,nonfinite);r.Status!="NONFINITE"{t.Fatal(r)}
 if r:=Audit(s[:2],d[:2]);r.Status!="INSUFFICIENT_OR_UNMATCHED_FRAMES"{t.Fatal(r)}
}
func TestResampleLostInformation(t *testing.T){
 // A high-frequency movement can vanish entirely in 60->30Hz even-tick sampling.
 a:=[]Frame{{0,0,0},{1,1,0},{2,0,0},{3,-1,0},{4,0,0}}
 b,e:=ResampleEven(a);if e!=nil{t.Fatal(e)}
 if len(b)!=3 {t.Fatal("target frame count",len(b))}
 for _,v:=range b {if v.X!=0||v.Y!=0{t.Fatal("alias mutation unexpectedly preserved",v)}}
 if a[1].X!=1||a[3].X!=-1 {t.Fatal("source lost original high-frequency track")}
 if _,e:=ResampleEven([]Frame{{0,0,0},{1,0,0},{1,0,0},{3,0,0},{4,0,0}});e==nil{t.Fatal("invalid monotonic source accepted")}
}
func TestCriticNoOverrideAndSourceBinding(t *testing.T){
 s,d:=fixtures()
 a,e:=DigestFrames(s);if e!=nil{t.Fatal(e)}
 b,e:=DigestFrames(d);if e!=nil{t.Fatal(e)}
 visual:=ClaimedVisualFinding{ModelID:"simulated-vlm-not-real",Status:"OBSERVED",SourceSHA256:a,TargetSHA256:b,CameraID:"synthetic-orthographic",FirstTick:2,LastTick:8,Confidence:1}
 if status,e:=Adjudicate(Audit(s,d),s,d,visual);e!=nil||status!="VISUAL_CLAIM_NOT_3D_QUALIFIED"{t.Fatalf("%s %v",status,e)}
 changed:=append([]Frame{},d...);changed[6].X+=0.5
 if status,e:=Adjudicate(Audit(s,changed),s,changed,visual);e==nil||status!="EVIDENCE_MISMATCH"{t.Fatalf("altered target digest accepted %s %v",status,e)}
 visual.TargetSHA256,_=DigestFrames(changed)
 if status,e:=Adjudicate(Audit(s,changed),s,changed,visual);e!=nil||status!="NUMERIC_FAILURE_NOT_OVERRIDABLE"{t.Fatalf("VLM overrode geometry %s %v",status,e)}
 visual.FirstTick=visual.LastTick
 if status,e:=Adjudicate(Audit(s,changed),s,changed,visual);e==nil||status!="INVALID_OBSERVATION"{t.Fatalf("single instant motion accepted %s %v",status,e)}
}
