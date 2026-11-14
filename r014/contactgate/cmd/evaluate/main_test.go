package main

import (
 "bytes"
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "testing"

 "github.com/SemperSupra/stable-character-pipeline/r014/contactgate"
)
func mkFixture(t *testing.T)(string,string,string){
 t.Helper()
 hash:=func(c string)string{return strings.Repeat(c,64)}
 p:=contactgate.Policy{MaxPenetrationM:.004,MaxSupportHoverM:.01,
  MaxStanceMarkerSpeedMPS:.05,MinStanceSeconds:.25,
  ContactBandM:.005,MinStanceCoverageFraction:.9}
 r:=contactgate.Record{Schema:contactgate.Schema,
  SourceScope:"PROJECT_ORIGINAL_SYNTHETIC_RDTE_ONLY",Claim:"DIAGNOSTIC_ONLY",
  SceneSHA256:hash("a"),MotionSHA256:hash("b"),SoleMeshSHA256:hash("c"),
  CalibrationSHA256:hash("d"),StanceLabelSHA256:hash("e"),
  PolicySHA256:contactgate.PolicyDigest(p),
  FrameCount:72,FrameRate:12,Substeps:4,Policy:p,
  Ground:contactgate.Ground{Normal:contactgate.Vec3{0,0,1},MetresPerUnit:1},
  Stance:[]contactgate.Segment{{Foot:"left",Support:"heel",Start:0,End:110},
  {Foot:"right",Support:"heel",Start:140,End:284}},
 }
 for i:=0;i<285;i++{
  a:=contactgate.Sole{Heel:contactgate.Vec3{0,0,.001},
   Ball:contactgate.Vec3{.1,0,.001},Toe:contactgate.Vec3{.2,0,.001},
   LowestShoeVertex:contactgate.Vec3{0,0,.001},LowestVertexIndex:2}
  b:=a
  b.Heel[1]=1;b.Ball[1]=1;b.Toe[1]=1;b.LowestShoeVertex[1]=1
  r.Frames=append(r.Frames,contactgate.Frame{Tick:i,Root:contactgate.Vec3{float64(i)*.001,0,1},Left:a,Right:b})
 }
 v:=trustInput{SceneSHA256:r.SceneSHA256,MotionSHA256:r.MotionSHA256,
  SoleMeshSHA256:r.SoleMeshSHA256,
  CalibrationSHA256:r.CalibrationSHA256,StanceLabelSHA256:r.StanceLabelSHA256,
  PolicySHA256:r.PolicySHA256,ReviewerProofSHA256:hash("f"),Reviewed:true}
 dir:=t.TempDir()
 rp:=filepath.Join(dir,"record.json");tp:=filepath.Join(dir,"independent-trust.json")
 out:=filepath.Join(dir,"result.json")
 rb,e:=json.Marshal(r);if e!=nil{t.Fatal(e)}
 tb,e:=json.Marshal(v);if e!=nil{t.Fatal(e)}
 if e=os.WriteFile(rp,rb,0600);e!=nil{t.Fatal(e)}
 if e=os.WriteFile(tp,tb,0600);e!=nil{t.Fatal(e)}
 return rp,tp,out
}
func TestCliRoundTripAndIdempotentWithoutMedia(t *testing.T){
 rp,tp,out:=mkFixture(t)
 args:=[]string{"-record",rp,"-trust",tp,"-output",out}
 if code,e:=execute(args);code!=0||e!=nil{t.Fatalf("first: %d %v",code,e)}
 original,e:=os.ReadFile(out);if e!=nil{t.Fatal(e)}
 if code,e:=execute(args);code!=0||e!=nil{t.Fatalf("repeated: %d %v",code,e)}
 repeated,e:=os.ReadFile(out);if e!=nil||!bytes.Equal(original,repeated){t.Fatal("non-idempotent output")}
 var v receipt
 if e=json.Unmarshal(original,&v);e!=nil{t.Fatal(e)}
 if v.Metrics.Status!="WITHIN_DECLARED_NUMERIC_POLICY_ONLY__NO_PHYSICAL_OR_RELEASE_PASS"||
  v.Rights!="LOCAL_INPUT_ADMISSION_NOT_PROVEN_BY_CLI"||v.CanonicalCharacterPack!="HOLD_OWNER_ONLY"{
  t.Fatalf("accidental product pass %+v",v)
 }
}
func TestCliRedWritesDiagnosticAndExitsThree(t *testing.T){
 rp,tp,out:=mkFixture(t)
 b,e:=os.ReadFile(rp);if e!=nil{t.Fatal(e)}
 var r contactgate.Record;if e=json.Unmarshal(b,&r);e!=nil{t.Fatal(e)}
 r.Frames[42].Left.LowestShoeVertex[2]=.088406
 b,e=json.Marshal(r);if e!=nil{t.Fatal(e)}
 if e=os.WriteFile(rp,b,0600);e!=nil{t.Fatal(e)}
 code,e:=execute([]string{"-record",rp,"-trust",tp,"-output",out})
 if e!=nil||code!=3{t.Fatalf("failed red disposition: %d %v",code,e)}
 body,e:=os.ReadFile(out);if e!=nil{t.Fatal(e)}
 var v receipt;if e=json.Unmarshal(body,&v);e!=nil{t.Fatal(e)}
 if v.Metrics.Status!="RED_DECLARED_CONTACT_POLICY"||v.Metrics.MaxSoleHoverM<.088{
  t.Fatalf("floating shoe was not rejected: %+v",v)
 }
}
func TestCliDoesNotOverwriteConflictingOutput(t *testing.T){
 rp,tp,out:=mkFixture(t)
 if e:=os.WriteFile(out,[]byte("PRIOR_EVIDENCE"),0600);e!=nil{t.Fatal(e)}
 code,e:=execute([]string{"-record",rp,"-trust",tp,"-output",out})
 if code!=2||e==nil{t.Fatal("overwrote existing receipt")}
 b,_:=os.ReadFile(out);if string(b)!="PRIOR_EVIDENCE"{t.Fatal("existing file damaged")}
}
func TestCliRejectsSameRecordAndTrustPath(t *testing.T){
 rp,_,out:=mkFixture(t)
 code,e:=execute([]string{"-record",rp,"-trust",rp,"-output",out})
 if code!=2||e==nil{t.Fatal("self-attesting input admitted")}
}
func TestCliRejectsUnknownReviewerField(t *testing.T){
 rp,tp,out:=mkFixture(t)
 b,_:=os.ReadFile(tp)
 b=bytes.Replace(b,[]byte("\"reviewed\":"),[]byte("\"extra_permission\":true,\"reviewed\":"),1)
 os.WriteFile(tp,b,0600)
 code,e:=execute([]string{"-record",rp,"-trust",tp,"-output",out})
 if code!=2||e==nil{t.Fatal("unexpected reviewer permission accepted")}
}
func TestCliCannotSelfWidenPolicy(t *testing.T){
 rp,tp,out:=mkFixture(t)
 b,_:=os.ReadFile(rp)
 var r contactgate.Record;json.Unmarshal(b,&r)
 r.Policy.MaxSupportHoverM=1
 next,_:=json.Marshal(r);os.WriteFile(rp,next,0600)
 code,e:=execute([]string{"-record",rp,"-trust",tp,"-output",out})
 if code!=2||e==nil{t.Fatal("candidate relaxed policy accepted")}
}
func TestAtomicWriterConflictingBytes(t *testing.T){
 out:=filepath.Join(t.TempDir(),"evidence.json")
 if e:=writeOnce(out,[]byte("first"));e!=nil{t.Fatal(e)}
 if e:=writeOnce(out,[]byte("first"));e!=nil{t.Fatal(e)}
 if e:=writeOnce(out,[]byte("second"));e==nil{t.Fatal("conflicting output overwritten")}
 v,_:=os.ReadFile(out);if string(v)!="first"{t.Fatal("lost immutable evidence")}
}
